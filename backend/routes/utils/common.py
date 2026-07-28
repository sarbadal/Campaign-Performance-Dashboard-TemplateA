from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Blueprint, current_app, request, session, url_for

from backend.services.dataframe_service import DataframeRequest, get_campaign_dataframe
from backend.services.db_service import fetch_sqlite_last_ingested_at
from backend.services.mysql_service import fetch_mysql_last_ingested_at
from backend.services.settings_service import (
    load_selected_filter_fields,
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

DEEP_DIVE_TABLE_COLUMN_DEFINITIONS: dict[str, str] = {
    "DATE": "Date",
    "CAMPAIGN_NAME": "Campaign",
    "CAMPAIGN_GROUP": "Campaign Group",
    "PLATFORM": "Platform",
    "ADSET_NAME": "Adset",
    "AD_NAME": "Ad Name",
    "AMOUNT_SPENT": "Spend",
    "IMPRESSIONS": "Impressions",
    "CLICKS": "Clicks",
    "CONVERSIONS": "Conversions",
    "LEADS": "Leads",
    "REACH": "Reach",
}

TOP_LEVEL_FILTERS_SESSION_KEY = "top_level_filters"

FilterOptionsByField = dict[str, list[str]]
FilterState = dict[str, object]
FilterDataframeResult = tuple[pd.DataFrame, FilterState, FilterOptionsByField]


@dataclass(slots=True)
class RouteContext:
    db_backend: str
    sqlite_db_file: Path
    mysql_config: dict[str, object]
    gcs_bucket: str
    gcs_prefix: str
    gcs_credentials_json: str
    settings_file: Path
    field_mapping_file: Path
    cache_ttl_seconds: int
    df: pd.DataFrame
    active_filter_fields: list[dict[str, str]] = field(default_factory=list)
    filtered_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    filters: FilterState = field(default_factory=dict)
    filter_options: FilterOptionsByField = field(default_factory=dict)


def _as_clean_str(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_truthy(value: object) -> bool:
    return _as_clean_str(value).lower() in {"1", "true", "yes", "on"}


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


def _resolve_last_updated_display(db_backend: str, sqlite_db_file: Path, mysql_config: dict[str, object]) -> str:
    normalized_backend = db_backend.strip().lower()
    if normalized_backend == "mysql":
        raw = fetch_mysql_last_ingested_at(mysql_config)
    elif normalized_backend == "sqlite":
        raw = fetch_sqlite_last_ingested_at(sqlite_db_file)
    else:
        raw = None
    return _format_last_updated(raw)


def _resolve_latest_report_date_display(df: pd.DataFrame) -> str:
    if "DATE" not in df.columns:
        return "N/A"

    dates = pd.to_datetime(df["DATE"], errors="coerce").dropna()
    if dates.empty:
        return "N/A"

    return dates.max().strftime("%d %b %Y")


def _resolve_footer_recency(
    db_backend: str,
    sqlite_db_file: Path,
    mysql_config: dict[str, object],
    df: pd.DataFrame,
) -> tuple[str, str]:
    normalized_backend = db_backend.strip().lower()
    if normalized_backend == "gcs":
        return "Latest Report Date", _resolve_latest_report_date_display(df)

    return "Last Updated", _resolve_last_updated_display(db_backend, sqlite_db_file, mysql_config)


def _as_positive_int(value: object, default: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _normalize_deep_dive_view(value: object) -> str:
    raw = _as_clean_str(value).lower()
    if raw in {"flat", "table", "rows"}:
        return "flat"
    return "hierarchy"


def _format_metric_value(metric_key: str, value: float) -> str:
    if metric_key == "AMOUNT_SPENT":
        return f"{value:,.2f}"
    return f"{int(round(value)):,}"


def _build_mysql_config() -> dict[str, object]:
    return {
        "host": current_app.config.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(current_app.config.get("MYSQL_PORT", 3306)),
        "user": current_app.config.get("MYSQL_USER", "root"),
        "password": current_app.config.get("MYSQL_PASSWORD", ""),
        "database": current_app.config.get("MYSQL_DATABASE", "campaign_performance"),
        "table": current_app.config.get("MYSQL_TABLE", "campaign_data"),
        "state_table": current_app.config.get("MYSQL_STATE_TABLE", "ingestion_state"),
    }


def _load_campaign_dataframe(
    db_backend: str,
    sqlite_db_file: Path,
    mysql_config: dict[str, object],
    field_mapping_file: Path,
    cache_ttl_seconds: int,
    gcs_bucket: str,
    gcs_prefix: str,
    gcs_credentials_json: str,
) -> pd.DataFrame:
    return get_campaign_dataframe(
        DataframeRequest(
            db_backend=db_backend,
            sqlite_db_file=sqlite_db_file,
            mysql_config=mysql_config,
            field_mapping_file=field_mapping_file,
            cache_ttl_seconds=cache_ttl_seconds,
            gcs_bucket=gcs_bucket,
            gcs_prefix=gcs_prefix,
            gcs_credentials_json=gcs_credentials_json,
        )
    )


def _build_active_filter_fields(settings_file: Path) -> list[dict[str, str]]:
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
    return active_filter_fields


def _build_route_context(*, include_filters: bool = True) -> RouteContext:
    db_backend = str(current_app.config.get("DB_BACKEND", "sqlite"))
    sqlite_db_file = current_app.config["SQLITE_DB_FILE"]
    mysql_config = _build_mysql_config()
    gcs_bucket = str(current_app.config.get("GCS_DATA_BUCKET", ""))
    gcs_prefix = str(current_app.config.get("GCS_DATA_PREFIX", ""))
    gcs_credentials_json = str(current_app.config.get("GCS_CREDENTIALS_JSON", ""))
    settings_file = current_app.config["DASHBOARD_SETTINGS_FILE"]
    field_mapping_file = current_app.config["FIELD_MAPPING_FILE"]
    cache_ttl_seconds = int(current_app.config.get("KPI_CACHE_TTL_SECONDS", 300))

    df = _load_campaign_dataframe(
        db_backend=db_backend,
        sqlite_db_file=sqlite_db_file,
        mysql_config=mysql_config,
        field_mapping_file=field_mapping_file,
        cache_ttl_seconds=cache_ttl_seconds,
        gcs_bucket=gcs_bucket,
        gcs_prefix=gcs_prefix,
        gcs_credentials_json=gcs_credentials_json,
    )

    context = RouteContext(
        db_backend=db_backend,
        sqlite_db_file=sqlite_db_file,
        mysql_config=mysql_config,
        gcs_bucket=gcs_bucket,
        gcs_prefix=gcs_prefix,
        gcs_credentials_json=gcs_credentials_json,
        settings_file=settings_file,
        field_mapping_file=field_mapping_file,
        cache_ttl_seconds=cache_ttl_seconds,
        df=df,
        filtered_df=df,
    )

    if include_filters:
        active_filter_fields = _build_active_filter_fields(settings_file)
        filtered_df, filters, filter_options = _filter_dataframe(df, active_filter_fields)
        context.active_filter_fields = active_filter_fields
        context.filtered_df = filtered_df
        context.filters = filters
        context.filter_options = filter_options

    return context


def _filter_dataframe(df: pd.DataFrame, active_filter_fields: list[dict[str, str]]) -> FilterDataframeResult:
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


def _build_branding(db_backend: str, sqlite_db_file: Path, mysql_config: dict[str, object], df: pd.DataFrame) -> dict[str, object]:
    recency_label, recency_value = _resolve_footer_recency(
        db_backend=db_backend,
        sqlite_db_file=sqlite_db_file,
        mysql_config=mysql_config,
        df=df,
    )
    return {
        "client_name": current_app.config.get("CLIENT_NAME", "Brand Placeholder"),
        "dashboard_kicker": current_app.config.get("DASHBOARD_KICKER", "Client Dashboard"),
        "banner_title": current_app.config.get(
            "DASHBOARD_BANNER_TITLE",
            "Campaign Performance Executive Snapshot",
        ),
        "logo_image_path": current_app.config.get("LOGO_IMAGE_PATH", "img/client-logo.svg"),
        "footer_team_name": current_app.config.get("FOOTER_TEAM_NAME", "Performance Analytics Team"),
        "last_updated_label": recency_label,
        "last_updated_at": recency_value,
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


def _row_to_record(row: pd.Series, selected_table_columns: list[str]) -> dict[str, str]:
    record: dict[str, str] = {}
    for column_key in selected_table_columns:
        value = row[column_key]
        if pd.isna(value):
            record[column_key] = ""
        else:
            record[column_key] = str(value)
    return record


def _build_drill_nodes(
    dataframe: pd.DataFrame,
    dimensions: list[str],
    selected_table_columns: list[str],
    metric_column_keys: list[str],
    level: int = 1,
) -> list[dict[str, object]]:
    if dataframe.empty or not dimensions:
        return []

    current_dimension = dimensions[0]
    grouped = dataframe.copy()
    grouped["__group_label"] = grouped[current_dimension].fillna("").astype(str).str.strip().replace("", "(blank)")

    nodes: list[dict[str, object]] = []
    for group_label, group_df in grouped.groupby("__group_label", sort=True):
        subgroup = group_df.drop(columns=["__group_label"])
        metrics = [
            {
                "key": metric_key,
                "label": DEEP_DIVE_TABLE_COLUMN_DEFINITIONS.get(metric_key, metric_key),
                "value": _format_metric_value(
                    metric_key,
                    float(pd.to_numeric(subgroup[metric_key], errors="coerce").fillna(0).sum()),
                ),
            }
            for metric_key in metric_column_keys
            if metric_key in subgroup.columns
        ]

        node: dict[str, object] = {
            "level": level,
            "field_label": DEEP_DIVE_TABLE_COLUMN_DEFINITIONS.get(current_dimension, current_dimension),
            "label": str(group_label),
            "row_count": int(subgroup.shape[0]),
            "metrics": metrics,
            "children": [],
            "rows": [],
        }

        if len(dimensions) > 1:
            node["children"] = _build_drill_nodes(
                subgroup,
                dimensions[1:],
                selected_table_columns,
                metric_column_keys,
                level + 1,
            )
        else:
            node["rows"] = [_row_to_record(row, selected_table_columns) for _, row in subgroup.iterrows()]

        nodes.append(node)

    return nodes


def _build_url(endpoint: str, args_multi: dict[str, list[str]], updates: dict[str, str]) -> str:
    page_params = {key: list(values) for key, values in args_multi.items()}
    for key, value in updates.items():
        page_params[key] = [value]
    return url_for(endpoint, **page_params)