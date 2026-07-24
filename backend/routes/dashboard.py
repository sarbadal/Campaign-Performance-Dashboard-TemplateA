from __future__ import annotations

from datetime import datetime

import pandas as pd
from flask import Blueprint, current_app, render_template, request, session, url_for

from backend.services.analytics_service import (
    DualAxisKpiSeriesRequest,
    DEFAULT_TOP_KPI_KEY,
    TOP_N_PLATFORMS,
    TOP_KPI_KEYS,
    TopEntityKpiRequest,
    dual_axis_kpi_series,
    top_entities_by_kpi,
)
from backend.services.dataframe_service import DataframeRequest, get_campaign_dataframe
from backend.services.db_service import fetch_sqlite_last_ingested_at
from backend.services.kpi_calculation_service import build_kpi_summary_from_dataframe
from backend.services.kpi_service import KPI_DEFINITIONS, KpiCardsRequest, build_kpi_cards
from backend.services.mysql_service import fetch_mysql_last_ingested_at
from backend.services.settings_service import (
    load_platform_chart_colors,
    load_selected_filter_fields,
    load_selected_kpis,
    load_selected_top_entity_charts,
    load_top_entity_chart_default_color,
    load_top_entity_chart_colors,
)


dashboard_bp = Blueprint("dashboard", __name__)

FILTER_FIELD_DEFINITIONS: dict[str, dict[str, str]] = {
    "objective": {"label": "Objective", "column": "OBJECTIVE"},
    "campaign_group": {"label": "Campaign Group", "column": "CAMPAIGN_GROUP"},
    "platform": {"label": "Platform", "column": "PLATFORM"},
    "campaign_name": {"label": "Campaign", "column": "CAMPAIGN_NAME"},
    "adname": {"label": "Ad Name", "column": "AD_NAME"},
    "adset_name": {"label": "Adset Name", "column": "ADSET_NAME"},
}

TOP_ENTITY_CHART_DEFINITIONS: dict[str, dict[str, str]] = {
    "platform": {"label_plural": "Platforms", "column": "PLATFORM"},
    "campaign_name": {"label_plural": "Campaign Names", "column": "CAMPAIGN_NAME"},
    "campaign_group": {"label_plural": "Campaign Groups", "column": "CAMPAIGN_GROUP"},
    "adname": {"label_plural": "Ad Names", "column": "AD_NAME"},
    "adset_name": {"label_plural": "Adset Names", "column": "ADSET_NAME"},
}

TREND_GRANULARITY_OPTIONS: dict[str, str] = {
    "daily": "Daily",
    "weekly": "Weekly (Mon Start)",
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "yearly": "Yearly",
}

TOP_LEVEL_FILTERS_SESSION_KEY = "top_level_filters"


def _as_clean_str(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _column_options(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []

    values = df[column].fillna("").astype(str).str.strip()
    values = values[values != ""]
    if values.empty:
        return []
    return sorted(values.unique().tolist())


def _date_input_defaults(df: pd.DataFrame) -> tuple[str, str]:
    if "DATE" not in df.columns:
        return "", ""

    dates = pd.to_datetime(df["DATE"], errors="coerce").dropna()
    if dates.empty:
        return "", ""

    return dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d")


def _clean_multi_values(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in values:
        value = _as_clean_str(item)
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


def _format_last_updated(raw: str | None) -> str:
    if not raw:
        return "N/A"

    try:
        dt = datetime.fromisoformat(raw)
        return dt.astimezone().strftime("%d %b %Y, %I:%M %p")
    except ValueError:
        return raw


def _resolve_last_updated_display(
    db_backend: str,
    sqlite_db_file,
    mysql_config: dict[str, object],
) -> str:
    if db_backend == "mysql":
        raw = fetch_mysql_last_ingested_at(mysql_config)
    else:
        raw = fetch_sqlite_last_ingested_at(sqlite_db_file)
    return _format_last_updated(raw)


def _filter_dataframe(
    df: pd.DataFrame,
    active_filter_fields: list[dict[str, str]],
) -> tuple[pd.DataFrame, dict[str, object], dict[str, list[str]]]:
    clear_requested = _as_clean_str(request.args.get("clear_filters", "")).lower() in {"1", "true", "yes"}
    if clear_requested:
        session.pop(TOP_LEVEL_FILTERS_SESSION_KEY, None)

    stored_filters_raw = session.get(TOP_LEVEL_FILTERS_SESSION_KEY, {})
    stored_filters = stored_filters_raw if isinstance(stored_filters_raw, dict) else {}

    def _stored_scalar(name: str) -> str:
        return _as_clean_str(stored_filters.get(name, ""))

    default_date_from, default_date_to = _date_input_defaults(df)

    filters = {
        "date_from": (
            _as_clean_str(request.args.get("date_from", ""))
            if "date_from" in request.args
            else (_stored_scalar("date_from") or default_date_from)
        ),
        "date_to": (
            _as_clean_str(request.args.get("date_to", ""))
            if "date_to" in request.args
            else (_stored_scalar("date_to") or default_date_to)
        ),
    }

    options: dict[str, list[str]] = {}
    for field in active_filter_fields:
        key = field["key"]
        column = field["column"]

        if key in request.args:
            selected_values = _clean_multi_values(request.args.getlist(key))
        else:
            stored_values = stored_filters.get(key, [])
            if isinstance(stored_values, list):
                selected_values = _clean_multi_values([str(item) for item in stored_values])
            else:
                selected_values = _clean_multi_values([str(stored_values)]) if stored_values else []

        filters[key] = selected_values
        options[key] = _column_options(df, column)

    filtered = df.copy()

    active_date_from = _as_clean_str(filters.get("date_from", ""))
    active_date_to = _as_clean_str(filters.get("date_to", ""))
    if "DATE" in filtered.columns and (active_date_from or active_date_to):
        parsed_dates = pd.to_datetime(filtered["DATE"], errors="coerce")

        if active_date_from:
            start = pd.to_datetime(active_date_from, errors="coerce")
            if pd.notna(start):
                filtered = filtered[parsed_dates >= start]
                parsed_dates = parsed_dates[parsed_dates >= start]

        if active_date_to:
            end = pd.to_datetime(active_date_to, errors="coerce")
            if pd.notna(end):
                filtered = filtered[parsed_dates <= end]

    for field in active_filter_fields:
        key = field["key"]
        column = field["column"]
        selected_values = filters.get(key) or []
        if not selected_values or column not in filtered.columns:
            continue
        chosen = set(selected_values)
        series = filtered[column].fillna("").astype(str).str.strip()
        filtered = filtered[series.isin(chosen)]

    stored_payload: dict[str, object] = {
        "date_from": filters["date_from"],
        "date_to": filters["date_to"],
    }
    for field in active_filter_fields:
        key = field["key"]
        value = filters.get(key) or []
        stored_payload[key] = value if isinstance(value, list) else []

    session[TOP_LEVEL_FILTERS_SESSION_KEY] = stored_payload
    session.modified = True

    return filtered, filters, options


@dashboard_bp.get("/")
def dashboard():
    data_file = current_app.config["DATA_FILE"]
    db_backend = str(current_app.config.get("DB_BACKEND", "sqlite"))
    sqlite_db_file = current_app.config["SQLITE_DB_FILE"]
    mysql_config = {
        "host": current_app.config.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(current_app.config.get("MYSQL_PORT", 3306)),
        "user": current_app.config.get("MYSQL_USER", "root"),
        "password": current_app.config.get("MYSQL_PASSWORD", ""),
        "database": current_app.config.get("MYSQL_DATABASE", "campaign_performance"),
        "table": current_app.config.get("MYSQL_TABLE", "campaign_data"),
        "state_table": current_app.config.get("MYSQL_STATE_TABLE", "ingestion_state"),
    }
    settings_file = current_app.config["DASHBOARD_SETTINGS_FILE"]
    field_mapping_file = current_app.config["FIELD_MAPPING_FILE"]
    currency_symbol = str(current_app.config.get("KPI_CURRENCY_SYMBOL", "RM"))
    cache_ttl_seconds = int(current_app.config.get("KPI_CACHE_TTL_SECONDS", 300))

    df = get_campaign_dataframe(
        DataframeRequest(
            data_file=data_file,
            db_backend=db_backend,
            sqlite_db_file=sqlite_db_file,
            mysql_config=mysql_config,
            field_mapping_file=field_mapping_file,
            cache_ttl_seconds=cache_ttl_seconds,
        )
    )
    selected_filter_keys = load_selected_filter_fields(
        settings_file=settings_file,
        allowed_fields=list(FILTER_FIELD_DEFINITIONS.keys()),
        max_filters=3,
    )
    active_filter_fields: list[dict[str, str]] = []
    for key in selected_filter_keys:
        definition = FILTER_FIELD_DEFINITIONS.get(key)
        if definition is None:
            continue
        active_filter_fields.append(
            {
                "key": key,
                "label": definition["label"],
                "column": definition["column"],
            }
        )

    filtered_df, filters, filter_options = _filter_dataframe(df, active_filter_fields)
    requested_shared_top_kpi = _as_clean_str(request.args.get("top_kpi", ""))
    shared_top_kpi = requested_shared_top_kpi if requested_shared_top_kpi in TOP_KPI_KEYS else DEFAULT_TOP_KPI_KEY

    requested_top_kpi_adset = _as_clean_str(request.args.get("top_kpi_adset", ""))
    requested_top_kpi_platform = _as_clean_str(request.args.get("top_kpi_platform", ""))

    selected_top_kpi_adset = (
        requested_top_kpi_adset if requested_top_kpi_adset in TOP_KPI_KEYS else shared_top_kpi
    )
    selected_top_kpi_platform = (
        requested_top_kpi_platform if requested_top_kpi_platform in TOP_KPI_KEYS else shared_top_kpi
    )

    filters["top_kpi_adset"] = selected_top_kpi_adset
    filters["top_kpi_platform"] = selected_top_kpi_platform
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
    if selected_line_kpi_right == selected_line_kpi_left:
        selected_line_kpi_right = "total_clicks" if selected_line_kpi_left != "total_clicks" else "total_reach"

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

    top_entity_charts: list[dict[str, object]] = []
    for chart_key in selected_top_entity_chart_keys:
        definition = TOP_ENTITY_CHART_DEFINITIONS.get(chart_key)
        if definition is None:
            continue

        chart_kpi_key = (
            selected_top_kpi_platform
            if chart_key == "platform"
            else selected_top_kpi_adset if chart_key == "adset_name" else shared_top_kpi
        )

        rows = top_entities_by_kpi(
            TopEntityKpiRequest(
                df=filtered_df,
                entity_column=definition["column"],
                entity_key="entity",
                top_n=TOP_N_PLATFORMS,
                kpi_key=chart_kpi_key,
                currency_symbol=currency_symbol,
            )
        )

        top_entity_charts.append(
            {
                "key": chart_key,
                "label_plural": definition["label_plural"],
                "rows": rows,
                "kpi_key": chart_kpi_key,
                "kpi_label": KPI_DEFINITIONS.get(chart_kpi_key, KPI_DEFINITIONS.get(DEFAULT_TOP_KPI_KEY, "Spend")),
                "colors": top_entity_chart_colors.get(
                    chart_key,
                    platform_chart_colors if chart_key == "platform" else {},
                ),
                "default_color": top_entity_chart_default_color,
            }
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
    last_updated_display = _resolve_last_updated_display(
        db_backend=db_backend,
        sqlite_db_file=sqlite_db_file,
        mysql_config=mysql_config,
    )
    branding = {
        "client_name": current_app.config.get("CLIENT_NAME", "Brand Placeholder"),
        "dashboard_kicker": current_app.config.get("DASHBOARD_KICKER", "Client Dashboard"),
        "banner_title": current_app.config.get(
            "DASHBOARD_BANNER_TITLE",
            "Campaign Performance Executive Snapshot",
        ),
        "logo_image_path": current_app.config.get("LOGO_IMAGE_PATH", "img/client-logo.svg"),
        "footer_team_name": current_app.config.get("FOOTER_TEAM_NAME", "Performance Analytics Team"),
        "last_updated_at": last_updated_display,
        "footer_logo_image_path": current_app.config.get("FOOTER_LOGO_IMAGE_PATH", "img/ogs-logo.gif"),
        "show_footer_logo": bool(current_app.config.get("SHOW_FOOTER_LOGO", True)),
        "banner_gradient_start": current_app.config.get("BANNER_GRADIENT_START", "#0b6e4f"),
        "banner_gradient_mid": current_app.config.get("BANNER_GRADIENT_MID", "#13795c"),
        "banner_gradient_end": current_app.config.get("BANNER_GRADIENT_END", "#2e8f74"),
        "dashboard_font_family": current_app.config.get(
            "DASHBOARD_FONT_FAMILY",
            '"Georgia", "Times New Roman", serif',
        ),
        "kpi_label_color": current_app.config.get("KPI_LABEL_COLOR", "#56605b"),
        "kpi_value_color": current_app.config.get("KPI_VALUE_COLOR", "#0b6e4f"),
        "kpi_label_font_size": current_app.config.get("KPI_LABEL_FONT_SIZE", "0.9rem"),
        "kpi_value_font_size": current_app.config.get(
            "KPI_VALUE_FONT_SIZE",
            "1.8rem",
        ),
    }
    return render_template(
        "dashboard.html",
        kpi=summary,
        kpi_cards=kpi_cards,
        top_entity_charts=top_entity_charts,
        top_n_entities=TOP_N_PLATFORMS,
        top_kpi_options=top_kpi_options,
        selected_top_kpi_adset=selected_top_kpi_adset,
        selected_top_kpi_platform=selected_top_kpi_platform,
        selected_top_kpi=shared_top_kpi,
        selected_line_kpi_left=selected_line_kpi_left,
        selected_line_kpi_right=selected_line_kpi_right,
        selected_line_granularity=selected_line_granularity,
        trend_granularity_options=TREND_GRANULARITY_OPTIONS,
        dual_axis_series=dual_axis_series,
        top_kpi_currency_symbol=currency_symbol,
        platform_chart_colors=platform_chart_colors,
        filters=filters,
        active_filter_fields=active_filter_fields,
        filter_options=filter_options,
        filtered_rows=int(filtered_df.shape[0]),
        total_rows=int(df.shape[0]),
        selected_kpis=selected_kpis,
        kpi_options=KPI_DEFINITIONS,
        settings_file=str(settings_file),
        branding=branding,
        current_page="dashboard",
        clear_url=url_for("dashboard.dashboard", clear_filters=1),
    )


@dashboard_bp.get("/deep-dive")
def deep_dive():
    data_file = current_app.config["DATA_FILE"]
    db_backend = str(current_app.config.get("DB_BACKEND", "sqlite"))
    sqlite_db_file = current_app.config["SQLITE_DB_FILE"]
    mysql_config = {
        "host": current_app.config.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(current_app.config.get("MYSQL_PORT", 3306)),
        "user": current_app.config.get("MYSQL_USER", "root"),
        "password": current_app.config.get("MYSQL_PASSWORD", ""),
        "database": current_app.config.get("MYSQL_DATABASE", "campaign_performance"),
        "table": current_app.config.get("MYSQL_TABLE", "campaign_data"),
        "state_table": current_app.config.get("MYSQL_STATE_TABLE", "ingestion_state"),
    }
    settings_file = current_app.config["DASHBOARD_SETTINGS_FILE"]
    field_mapping_file = current_app.config["FIELD_MAPPING_FILE"]
    cache_ttl_seconds = int(current_app.config.get("KPI_CACHE_TTL_SECONDS", 300))

    df = get_campaign_dataframe(
        DataframeRequest(
            data_file=data_file,
            db_backend=db_backend,
            sqlite_db_file=sqlite_db_file,
            mysql_config=mysql_config,
            field_mapping_file=field_mapping_file,
            cache_ttl_seconds=cache_ttl_seconds,
        )
    )
    selected_filter_keys = load_selected_filter_fields(
        settings_file=settings_file,
        allowed_fields=list(FILTER_FIELD_DEFINITIONS.keys()),
        max_filters=3,
    )

    active_filter_fields: list[dict[str, str]] = []
    for key in selected_filter_keys:
        definition = FILTER_FIELD_DEFINITIONS.get(key)
        if definition is None:
            continue
        active_filter_fields.append(
            {
                "key": key,
                "label": definition["label"],
                "column": definition["column"],
            }
        )

    filtered_df, filters, filter_options = _filter_dataframe(df, active_filter_fields)
    summary = build_kpi_summary_from_dataframe(filtered_df)
    last_updated_display = _resolve_last_updated_display(
        db_backend=db_backend,
        sqlite_db_file=sqlite_db_file,
        mysql_config=mysql_config,
    )

    branding = {
        "client_name": current_app.config.get("CLIENT_NAME", "Brand Placeholder"),
        "dashboard_kicker": current_app.config.get("DASHBOARD_KICKER", "Client Dashboard"),
        "banner_title": current_app.config.get(
            "DASHBOARD_BANNER_TITLE",
            "Campaign Performance Executive Snapshot",
        ),
        "logo_image_path": current_app.config.get("LOGO_IMAGE_PATH", "img/client-logo.svg"),
        "footer_team_name": current_app.config.get("FOOTER_TEAM_NAME", "Performance Analytics Team"),
        "last_updated_at": last_updated_display,
        "footer_logo_image_path": current_app.config.get("FOOTER_LOGO_IMAGE_PATH", "img/ogs-logo.gif"),
        "show_footer_logo": bool(current_app.config.get("SHOW_FOOTER_LOGO", True)),
        "banner_gradient_start": current_app.config.get("BANNER_GRADIENT_START", "#0b6e4f"),
        "banner_gradient_mid": current_app.config.get("BANNER_GRADIENT_MID", "#13795c"),
        "banner_gradient_end": current_app.config.get("BANNER_GRADIENT_END", "#2e8f74"),
        "dashboard_font_family": current_app.config.get(
            "DASHBOARD_FONT_FAMILY",
            '"Georgia", "Times New Roman", serif',
        ),
        "kpi_label_color": current_app.config.get("KPI_LABEL_COLOR", "#56605b"),
        "kpi_value_color": current_app.config.get("KPI_VALUE_COLOR", "#0b6e4f"),
        "kpi_label_font_size": current_app.config.get("KPI_LABEL_FONT_SIZE", "0.9rem"),
        "kpi_value_font_size": current_app.config.get(
            "KPI_VALUE_FONT_SIZE",
            "1.8rem",
        ),
    }

    return render_template(
        "deep_dive.html",
        kpi=summary,
        filters=filters,
        active_filter_fields=active_filter_fields,
        filter_options=filter_options,
        filtered_rows=int(filtered_df.shape[0]),
        total_rows=int(df.shape[0]),
        branding=branding,
        current_page="deep_dive",
        clear_url=url_for("dashboard.deep_dive", clear_filters=1),
    )
