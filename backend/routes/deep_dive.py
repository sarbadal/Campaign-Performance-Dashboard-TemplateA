from __future__ import annotations

from datetime import datetime
from io import StringIO

import pandas as pd
from flask import Response, current_app, render_template, request

from backend.services.kpi_calculation_service import build_kpi_summary_from_dataframe
from backend.services.settings_service import (
    load_deep_dive_default_page_size,
    load_selected_deep_dive_hierarchy_fields,
    load_selected_deep_dive_table_columns,
)

from .utils.auth import (
    _is_auth_enabled,
    _require_authenticated,
)
from .utils.common import (
    DEEP_DIVE_TABLE_COLUMN_DEFINITIONS,
    _as_positive_int,
    _as_truthy,
    _build_branding,
    _build_drill_nodes,
    _build_route_context,
    _build_url,
    _normalize_deep_dive_view,
    _row_to_record,
    dashboard_bp,
)


@dashboard_bp.get("/deep-dive")
@_require_authenticated
def deep_dive():
    route_context = _build_route_context(include_filters=True)
    db_backend = route_context.db_backend
    sqlite_db_file = route_context.sqlite_db_file
    mysql_config = route_context.mysql_config
    settings_file = route_context.settings_file

    df = route_context.df
    active_filter_fields = route_context.active_filter_fields
    filtered_df = route_context.filtered_df
    filters = route_context.filters
    filter_options = route_context.filter_options
    summary = build_kpi_summary_from_dataframe(filtered_df)

    selected_deep_dive_column_keys = load_selected_deep_dive_table_columns(
        settings_file=settings_file,
        allowed_column_keys=list(DEEP_DIVE_TABLE_COLUMN_DEFINITIONS.keys()),
        max_columns=12,
    )
    deep_dive_columns = [
        {"key": column_key, "label": DEEP_DIVE_TABLE_COLUMN_DEFINITIONS[column_key]}
        for column_key in selected_deep_dive_column_keys
        if column_key in filtered_df.columns
    ]

    view_mode = _normalize_deep_dive_view(request.args.get("view", "hierarchy"))
    all_rows_enabled = _as_truthy(request.args.get("all_rows", ""))

    base_page_size_options = [50, 100, 200]
    default_page_size = load_deep_dive_default_page_size(
        settings_file=settings_file,
        default_page_size=100,
    )
    page_size_options = sorted(set(base_page_size_options + [default_page_size]))
    page_size_requested = _as_positive_int(request.args.get("page_size", str(default_page_size)), default_page_size)
    page_size = page_size_requested if page_size_requested in page_size_options else default_page_size
    page = _as_positive_int(request.args.get("page", "1"), 1)

    deep_dive_total_rows = int(filtered_df.shape[0])
    if deep_dive_total_rows > 0:
        page_size_options = sorted(set(page_size_options + [deep_dive_total_rows]))
        if all_rows_enabled or page_size_requested == deep_dive_total_rows:
            page_size = deep_dive_total_rows

    deep_dive_table_df = filtered_df.copy()
    if "DATE" in deep_dive_table_df.columns:
        deep_dive_table_df["__parsed_date"] = pd.to_datetime(deep_dive_table_df["DATE"], errors="coerce")
        deep_dive_table_df = deep_dive_table_df.sort_values("__parsed_date", ascending=False, na_position="last")

    selected_table_columns = [column["key"] for column in deep_dive_columns]
    if selected_table_columns:
        deep_dive_table_df = deep_dive_table_df.loc[:, selected_table_columns]
    else:
        deep_dive_table_df = deep_dive_table_df.head(0)

    deep_dive_full_df = deep_dive_table_df.copy()

    total_pages = max((deep_dive_total_rows + page_size - 1) // page_size, 1)
    page = min(page, total_pages)
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    deep_dive_table_df = deep_dive_table_df.iloc[start_index:end_index]

    metric_column_keys = [
        key for key in ["AMOUNT_SPENT", "IMPRESSIONS", "CLICKS", "CONVERSIONS", "LEADS", "REACH"]
        if key in selected_table_columns
    ]
    available_hierarchy_fields = [
        key for key in ["PLATFORM", "CAMPAIGN_GROUP", "CAMPAIGN_NAME", "ADSET_NAME", "AD_NAME", "DATE"]
        if key in selected_table_columns and key not in metric_column_keys
    ]
    hierarchy_columns = load_selected_deep_dive_hierarchy_fields(
        settings_file=settings_file,
        allowed_field_keys=available_hierarchy_fields,
        max_levels=3,
    )

    if not hierarchy_columns:
        hierarchy_columns = [key for key in available_hierarchy_fields if key not in metric_column_keys][:2]

    deep_dive_rows: list[dict[str, str]] = [
        _row_to_record(row, selected_table_columns)
        for _, row in deep_dive_table_df.iterrows()
    ]
    deep_dive_drill_nodes = (
        _build_drill_nodes(
            dataframe=deep_dive_full_df,
            dimensions=hierarchy_columns,
            selected_table_columns=selected_table_columns,
            metric_column_keys=metric_column_keys,
        )
        if view_mode == "hierarchy"
        else []
    )
    deep_dive_hierarchy_fields = [
        {"key": key, "label": DEEP_DIVE_TABLE_COLUMN_DEFINITIONS.get(key, key)}
        for key in hierarchy_columns
    ]

    args_multi = request.args.to_dict(flat=False)
    args_multi.pop("clear_filters", None)

    page_start = max(1, page - 2)
    page_end = min(total_pages, page + 2)
    page_links = [
        {
            "page": page_number,
            "url": _build_url(
                "dashboard.deep_dive",
                args_multi,
                {
                    "page": str(max(page_number, 1)),
                    "page_size": str(page_size),
                    "view": view_mode,
                    "all_rows": "1" if all_rows_enabled else "0",
                },
            ),
            "is_current": page_number == page,
        }
        for page_number in range(page_start, page_end + 1)
    ]

    page_size_links = [
        {
            "size": size,
            "url": _build_url(
                "dashboard.deep_dive",
                args_multi,
                {
                    "page": "1",
                    "page_size": str(size),
                    "view": view_mode,
                    "all_rows": "0",
                },
            ),
            "is_current": size == page_size,
        }
        for size in page_size_options
    ]

    pagination = {
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "start_row": start_index + 1 if deep_dive_total_rows > 0 else 0,
        "end_row": start_index + len(deep_dive_rows),
        "prev_url": (
            _build_url(
                "dashboard.deep_dive",
                args_multi,
                {
                    "page": str(page - 1),
                    "page_size": str(page_size),
                    "view": view_mode,
                    "all_rows": "1" if all_rows_enabled else "0",
                },
            )
            if page > 1
            else ""
        ),
        "next_url": (
            _build_url(
                "dashboard.deep_dive",
                args_multi,
                {
                    "page": str(page + 1),
                    "page_size": str(page_size),
                    "view": view_mode,
                    "all_rows": "1" if all_rows_enabled else "0",
                },
            )
            if page < total_pages
            else ""
        ),
        "page_links": page_links,
        "page_size_links": page_size_links,
        "all_rows_enabled": bool(all_rows_enabled and deep_dive_total_rows > 0),
        "all_rows_on_url": (
            _build_url(
                "dashboard.deep_dive",
                args_multi,
                {
                    "page": "1",
                    "view": view_mode,
                    "all_rows": "1",
                    "page_size": str(deep_dive_total_rows),
                },
            )
            if deep_dive_total_rows > 0
            else ""
        ),
        "all_rows_off_url": _build_url(
            "dashboard.deep_dive",
            args_multi,
            {
                "page": "1",
                "view": view_mode,
                "all_rows": "0",
                "page_size": str(default_page_size),
            },
        ),
    }

    view_links = {
        "hierarchy_url": _build_url(
            "dashboard.deep_dive",
            args_multi,
            {
                "page": "1",
                "view": "hierarchy",
                "page_size": str(page_size),
                "all_rows": "1" if all_rows_enabled else "0",
            },
        ),
        "flat_url": _build_url(
            "dashboard.deep_dive",
            args_multi,
            {
                "page": "1",
                "view": "flat",
                "page_size": str(page_size),
                "all_rows": "1" if all_rows_enabled else "0",
            },
        ),
    }

    deep_dive_download_current_csv_url = _build_url(
        "dashboard.deep_dive_download_csv",
        args_multi,
        {
            "view": view_mode,
            "page": str(page),
            "page_size": str(page_size),
            "all_rows": "1" if all_rows_enabled else "0",
        },
    )

    deep_dive_download_all_csv_url = _build_url(
        "dashboard.deep_dive_download_csv",
        args_multi,
        {
            "view": view_mode,
            "page": "1",
            "page_size": str(deep_dive_total_rows if deep_dive_total_rows > 0 else page_size),
            "all_rows": "1",
        },
    )

    branding = _build_branding(
        db_backend=db_backend,
        sqlite_db_file=sqlite_db_file,
        mysql_config=mysql_config,
        df=df,
    )

    return render_template(
        "deep_dive.html",
        kpi=summary,
        filters=filters,
        active_filter_fields=active_filter_fields,
        filter_options=filter_options,
        deep_dive_columns=deep_dive_columns,
        deep_dive_rows=deep_dive_rows,
        deep_dive_drill_nodes=deep_dive_drill_nodes,
        deep_dive_hierarchy_fields=deep_dive_hierarchy_fields,
        deep_dive_view_mode=view_mode,
        deep_dive_view_links=view_links,
        deep_dive_download_current_csv_url=deep_dive_download_current_csv_url,
        deep_dive_download_all_csv_url=deep_dive_download_all_csv_url,
        deep_dive_total_rows=deep_dive_total_rows,
        deep_dive_page_size=page_size,
        deep_dive_all_rows_enabled=bool(all_rows_enabled and deep_dive_total_rows > 0),
        pagination=pagination,
        filtered_rows=int(filtered_df.shape[0]),
        total_rows=int(df.shape[0]),
        branding=branding,
        app_auth_enabled=_is_auth_enabled(),
        current_page="deep_dive",
        clear_url=_build_url("dashboard.deep_dive", {}, {"clear_filters": "1"}),
    )


@dashboard_bp.get("/deep-dive/download-csv")
@_require_authenticated
def deep_dive_download_csv() -> Response:
    route_context = _build_route_context(include_filters=True)
    settings_file = route_context.settings_file
    filtered_df = route_context.filtered_df

    selected_deep_dive_column_keys = load_selected_deep_dive_table_columns(
        settings_file=settings_file,
        allowed_column_keys=list(DEEP_DIVE_TABLE_COLUMN_DEFINITIONS.keys()),
        max_columns=12,
    )
    selected_table_columns = [
        column_key
        for column_key in selected_deep_dive_column_keys
        if column_key in filtered_df.columns
    ]

    table_df = filtered_df.copy()
    if "DATE" in table_df.columns:
        table_df["__parsed_date"] = pd.to_datetime(table_df["DATE"], errors="coerce")
        table_df = table_df.sort_values("__parsed_date", ascending=False, na_position="last")

    if selected_table_columns:
        table_df = table_df.loc[:, selected_table_columns]
    else:
        table_df = table_df.head(0)

    deep_dive_total_rows = int(table_df.shape[0])
    all_rows_enabled = _as_truthy(request.args.get("all_rows", ""))

    default_page_size = load_deep_dive_default_page_size(
        settings_file=settings_file,
        default_page_size=100,
    )
    base_page_size_options = [50, 100, 200]
    page_size_options = sorted(set(base_page_size_options + [default_page_size]))
    if deep_dive_total_rows > 0:
        page_size_options = sorted(set(page_size_options + [deep_dive_total_rows]))

    page_size_requested = _as_positive_int(request.args.get("page_size", str(default_page_size)), default_page_size)
    page_size = page_size_requested if page_size_requested in page_size_options else default_page_size
    if all_rows_enabled and deep_dive_total_rows > 0:
        page_size = deep_dive_total_rows

    if not all_rows_enabled:
        page = _as_positive_int(request.args.get("page", "1"), 1)
        total_pages = max((deep_dive_total_rows + page_size - 1) // page_size, 1)
        page = min(page, total_pages)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        table_df = table_df.iloc[start_index:end_index]

    export_df = table_df.rename(columns=DEEP_DIVE_TABLE_COLUMN_DEFINITIONS)
    csv_buffer = StringIO()
    export_df.to_csv(csv_buffer, index=False)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"deep_dive_table_{timestamp}.csv"
    return Response(
        csv_buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
