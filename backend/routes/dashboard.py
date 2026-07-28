from __future__ import annotations

from dataclasses import dataclass

from flask import current_app, render_template, request

from backend.services.analytics_service import (
    DEFAULT_TOP_KPI_KEY,
    TOP_N_PLATFORMS,
    TOP_KPI_KEYS,
    top_entities_by_kpi,
    DualAxisKpiSeriesRequest,
    TopEntityKpiRequest,
    dual_axis_kpi_series,
)
from backend.services.kpi_calculation_service import build_kpi_summary_from_dataframe
from backend.services.kpi_service import KPI_DEFINITIONS, KpiCardsRequest, build_kpi_cards
from backend.services.settings_service import (
    load_platform_chart_colors,
    load_selected_kpis,
    load_selected_top_entity_charts,
    load_top_entity_chart_colors,
    load_top_entity_chart_default_color,
)

from .utils.auth import (
    _is_auth_enabled,
    _require_authenticated,
)
from .utils.common import (
    TOP_ENTITY_CHART_DEFINITIONS,
    TREND_GRANULARITY_OPTIONS,
    _as_clean_str,
    _build_branding,
    _build_route_context,
    _build_url,
    dashboard_bp,
)


@dataclass(slots=True)
class DashboardRenderContextParams:
    summary: object
    kpi_cards: list[dict[str, object]]
    top_entity_charts: list[dict[str, object]]
    top_kpi_options: dict[str, str]
    selected_top_kpi_adset: str
    selected_top_kpi_platform: str
    shared_top_kpi: str
    selected_line_kpi_left: str
    selected_line_kpi_right: str
    selected_line_granularity: str
    dual_axis_series: list[dict[str, object]]
    currency_symbol: str
    platform_chart_colors: dict[str, str]
    filters: dict[str, object]
    active_filter_fields: list[dict[str, str]]
    filter_options: dict[str, list[str]]
    filtered_rows: int
    total_rows: int
    selected_kpis: list[str]
    settings_file: object
    branding: dict[str, object]


@dataclass(slots=True)
class TopEntityChartsParams:
    filtered_df: object
    selected_top_entity_chart_keys: list[str]
    shared_top_kpi: str
    selected_top_kpi_adset: str
    selected_top_kpi_platform: str
    top_entity_chart_colors: dict[str, dict[str, str]]
    platform_chart_colors: dict[str, str]
    top_entity_chart_default_color: str
    currency_symbol: str


def _resolve_top_kpi_state() -> tuple[str, str, str]:
    requested_shared_top_kpi = _as_clean_str(request.args.get("top_kpi", ""))
    shared_top_kpi = requested_shared_top_kpi if requested_shared_top_kpi in TOP_KPI_KEYS else DEFAULT_TOP_KPI_KEY

    requested_top_kpi_adset = _as_clean_str(request.args.get("top_kpi_adset", ""))
    requested_top_kpi_platform = _as_clean_str(request.args.get("top_kpi_platform", ""))

    selected_top_kpi_adset = requested_top_kpi_adset if requested_top_kpi_adset in TOP_KPI_KEYS else shared_top_kpi
    selected_top_kpi_platform = (
        requested_top_kpi_platform if requested_top_kpi_platform in TOP_KPI_KEYS else shared_top_kpi
    )
    return shared_top_kpi, selected_top_kpi_adset, selected_top_kpi_platform


def _resolve_line_trend_state() -> tuple[str, str, str]:
    requested_line_kpi_left = _as_clean_str(request.args.get("line_kpi_left", ""))
    requested_line_kpi_right = _as_clean_str(request.args.get("line_kpi_right", ""))
    requested_line_granularity = _as_clean_str(request.args.get("line_granularity", ""))

    selected_line_kpi_left = requested_line_kpi_left if requested_line_kpi_left in TOP_KPI_KEYS else "total_spend"
    selected_line_kpi_right = (
        requested_line_kpi_right if requested_line_kpi_right in TOP_KPI_KEYS else "total_impressions"
    )
    selected_line_granularity = (
        requested_line_granularity if requested_line_granularity in TREND_GRANULARITY_OPTIONS else "daily"
    )
    return selected_line_kpi_left, selected_line_kpi_right, selected_line_granularity


def _build_top_entity_charts(params: TopEntityChartsParams) -> list[dict[str, object]]:
    top_entity_charts: list[dict[str, object]] = []
    for chart_key in params.selected_top_entity_chart_keys:
        definition = TOP_ENTITY_CHART_DEFINITIONS.get(chart_key)
        if definition is None:
            continue

        chart_kpi_key = (
            params.selected_top_kpi_platform
            if chart_key == "platform"
            else params.selected_top_kpi_adset if chart_key == "adset_name" else params.shared_top_kpi
        )

        rows = top_entities_by_kpi(
            TopEntityKpiRequest(
                df=params.filtered_df,
                entity_column=definition["column"],
                entity_key="entity",
                top_n=TOP_N_PLATFORMS,
                kpi_key=chart_kpi_key,
                currency_symbol=params.currency_symbol,
            )
        )

        top_entity_charts.append(
            {
                "key": chart_key,
                "label_plural": definition["label_plural"],
                "rows": rows,
                "kpi_key": chart_kpi_key,
                "kpi_label": KPI_DEFINITIONS.get(chart_kpi_key, KPI_DEFINITIONS.get(DEFAULT_TOP_KPI_KEY, "Spend")),
                "colors": params.top_entity_chart_colors.get(
                    chart_key,
                    params.platform_chart_colors if chart_key == "platform" else {},
                ),
                "default_color": params.top_entity_chart_default_color,
            }
        )

    return top_entity_charts


def _build_dashboard_render_context(params: DashboardRenderContextParams) -> dict[str, object]:
    return {
        "kpi": params.summary,
        "kpi_cards": params.kpi_cards,
        "top_entity_charts": params.top_entity_charts,
        "top_n_entities": TOP_N_PLATFORMS,
        "top_kpi_options": params.top_kpi_options,
        "selected_top_kpi_adset": params.selected_top_kpi_adset,
        "selected_top_kpi_platform": params.selected_top_kpi_platform,
        "selected_top_kpi": params.shared_top_kpi,
        "selected_line_kpi_left": params.selected_line_kpi_left,
        "selected_line_kpi_right": params.selected_line_kpi_right,
        "selected_line_granularity": params.selected_line_granularity,
        "trend_granularity_options": TREND_GRANULARITY_OPTIONS,
        "dual_axis_series": params.dual_axis_series,
        "top_kpi_currency_symbol": params.currency_symbol,
        "platform_chart_colors": params.platform_chart_colors,
        "filters": params.filters,
        "active_filter_fields": params.active_filter_fields,
        "filter_options": params.filter_options,
        "filtered_rows": params.filtered_rows,
        "total_rows": params.total_rows,
        "selected_kpis": params.selected_kpis,
        "kpi_options": KPI_DEFINITIONS,
        "settings_file": str(params.settings_file),
        "branding": params.branding,
        "app_auth_enabled": _is_auth_enabled(),
        "current_page": "dashboard",
        "clear_url": _build_url("dashboard.dashboard", {}, {"clear_filters": "1"}),
    }


@dashboard_bp.get("/")
@_require_authenticated
def dashboard():
    route_context = _build_route_context(include_filters=True)
    db_backend = route_context.db_backend
    sqlite_db_file = route_context.sqlite_db_file
    mysql_config = route_context.mysql_config
    settings_file = route_context.settings_file
    currency_symbol = str(current_app.config.get("KPI_CURRENCY_SYMBOL", "RM"))

    df = route_context.df
    active_filter_fields = route_context.active_filter_fields
    filtered_df = route_context.filtered_df
    filters = route_context.filters
    filter_options = route_context.filter_options

    shared_top_kpi, selected_top_kpi_adset, selected_top_kpi_platform = _resolve_top_kpi_state()

    filters["top_kpi_adset"] = selected_top_kpi_adset
    filters["top_kpi_platform"] = selected_top_kpi_platform

    selected_line_kpi_left, selected_line_kpi_right, selected_line_granularity = _resolve_line_trend_state()

    filters["line_kpi_left"] = selected_line_kpi_left
    filters["line_kpi_right"] = selected_line_kpi_right
    filters["line_granularity"] = selected_line_granularity

    summary = build_kpi_summary_from_dataframe(filtered_df)
    selected_kpis = load_selected_kpis(settings_file)
    platform_chart_colors = load_platform_chart_colors(settings_file)
    top_entity_chart_colors = load_top_entity_chart_colors(settings_file)
    top_entity_chart_default_color = load_top_entity_chart_default_color(settings_file)
    selected_top_entity_chart_keys = load_selected_top_entity_charts(
        settings_file=settings_file,
        allowed_chart_keys=list(TOP_ENTITY_CHART_DEFINITIONS.keys()),
        max_charts=2,
    )

    kpi_cards = build_kpi_cards(
        KpiCardsRequest(
            summary=summary,
            selected_keys=selected_kpis,
            currency_symbol=currency_symbol,
        )
    )

    top_entity_charts = _build_top_entity_charts(
        TopEntityChartsParams(
            filtered_df=filtered_df,
            selected_top_entity_chart_keys=selected_top_entity_chart_keys,
            shared_top_kpi=shared_top_kpi,
            selected_top_kpi_adset=selected_top_kpi_adset,
            selected_top_kpi_platform=selected_top_kpi_platform,
            top_entity_chart_colors=top_entity_chart_colors,
            platform_chart_colors=platform_chart_colors,
            top_entity_chart_default_color=top_entity_chart_default_color,
            currency_symbol=currency_symbol,
        )
    )

    top_kpi_options = {key: KPI_DEFINITIONS[key] for key in TOP_KPI_KEYS if key in KPI_DEFINITIONS}
    dual_axis_series = dual_axis_kpi_series(
        DualAxisKpiSeriesRequest(
            df=filtered_df,
            left_kpi_key=selected_line_kpi_left,
            right_kpi_key=selected_line_kpi_right,
            granularity=selected_line_granularity,
        )
    )

    branding = _build_branding(
        db_backend=db_backend,
        sqlite_db_file=sqlite_db_file,
        mysql_config=mysql_config,
        df=df,
    )

    render_context = _build_dashboard_render_context(
        DashboardRenderContextParams(
            summary=summary,
            kpi_cards=kpi_cards,
            top_entity_charts=top_entity_charts,
            top_kpi_options=top_kpi_options,
            selected_top_kpi_adset=selected_top_kpi_adset,
            selected_top_kpi_platform=selected_top_kpi_platform,
            shared_top_kpi=shared_top_kpi,
            selected_line_kpi_left=selected_line_kpi_left,
            selected_line_kpi_right=selected_line_kpi_right,
            selected_line_granularity=selected_line_granularity,
            dual_axis_series=dual_axis_series,
            currency_symbol=currency_symbol,
            platform_chart_colors=platform_chart_colors,
            filters=filters,
            active_filter_fields=active_filter_fields,
            filter_options=filter_options,
            filtered_rows=int(filtered_df.shape[0]),
            total_rows=int(df.shape[0]),
            selected_kpis=selected_kpis,
            settings_file=settings_file,
            branding=branding,
        )
    )
    return render_template("dashboard.html", **render_context)
