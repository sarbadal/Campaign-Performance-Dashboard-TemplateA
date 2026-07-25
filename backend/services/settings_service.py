from __future__ import annotations

import json
from pathlib import Path

DEFAULT_SELECTED_KPIS = [
    "total_spend",
    "total_impressions",
    "total_reach",
    "total_clicks",
    "total_conversions",
    "total_campaigns",
    "avg_ctr_percent",
    "avg_cpc",
    "cpm",
    "cvv",
]

DEFAULT_SELECTED_FILTER_FIELDS = [
    "objective",
    "campaign_group",
    "platform",
]

DEFAULT_SELECTED_TOP_ENTITY_CHARTS = [
    "platform",
    "campaign_name",
]

DEFAULT_SELECTED_DEEP_DIVE_TABLE_COLUMNS = [
    "DATE",
    "CAMPAIGN_NAME",
    "CAMPAIGN_GROUP",
    "PLATFORM",
    "ADSET_NAME",
    "AD_NAME",
    "AMOUNT_SPENT",
    "IMPRESSIONS",
    "CLICKS",
    "CONVERSIONS",
    "LEADS",
    "REACH",
]

DEFAULT_SELECTED_DEEP_DIVE_HIERARCHY_FIELDS = [
    "PLATFORM",
    "CAMPAIGN_GROUP",
    "ADSET_NAME",
]


def load_platform_chart_colors(settings_file: Path) -> dict[str, str]:
    """Load optional platform color mapping for Top Platforms chart.

    Expected JSON shape:
      {
        "platform_chart_colors": {
          "Facebook": "#1877F2",
          "Instagram": "#E4405F"
        }
      }
    """
    if not settings_file.exists():
        return {}

    try:
        payload = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    raw = payload.get("platform_chart_colors")
    if not isinstance(raw, dict):
        return {}

    colors: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        platform = key.strip()
        color = value.strip()
        if not platform or not color:
            continue
        colors[platform] = color

    return colors


def load_top_entity_chart_colors(settings_file: Path) -> dict[str, dict[str, str]]:
    """Load optional per-entity color mappings for top-entity charts.

    Expected JSON shape:
      {
        "top_entity_chart_colors": {
          "platform": {
            "Meta": "#1877F2"
          },
          "campaign_group": {
            "Brand": "#EF6C00"
          }
        }
      }

    Backward compatibility:
      - If "platform_chart_colors" is present, it is used as the
        "platform" entry when top_entity_chart_colors.platform is missing.
    """
    if not settings_file.exists():
        return {}

    try:
        payload = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    result: dict[str, dict[str, str]] = {}

    raw = payload.get("top_entity_chart_colors")
    if isinstance(raw, dict):
        for entity_key, entity_colors in raw.items():
            if not isinstance(entity_key, str) or not isinstance(entity_colors, dict):
                continue
            cleaned_entity_key = entity_key.strip()
            if not cleaned_entity_key:
                continue

            cleaned_colors: dict[str, str] = {}
            for item_key, item_color in entity_colors.items():
                if not isinstance(item_key, str) or not isinstance(item_color, str):
                    continue
                key = item_key.strip()
                color = item_color.strip()
                if not key or not color:
                    continue
                cleaned_colors[key] = color

            if cleaned_colors:
                result[cleaned_entity_key] = cleaned_colors

    legacy_platform = payload.get("platform_chart_colors")
    if "platform" not in result and isinstance(legacy_platform, dict):
        cleaned_legacy: dict[str, str] = {}
        for item_key, item_color in legacy_platform.items():
            if not isinstance(item_key, str) or not isinstance(item_color, str):
                continue
            key = item_key.strip()
            color = item_color.strip()
            if not key or not color:
                continue
            cleaned_legacy[key] = color
        if cleaned_legacy:
            result["platform"] = cleaned_legacy

    return result


def load_top_entity_chart_default_color(settings_file: Path) -> str:
    """Load optional default bar color for top-entity charts.

    Expected JSON shape:
      {
        "top_entity_chart_default_color": "#0b6e4f"
      }
    """
    if not settings_file.exists():
        return ""

    try:
        payload = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""

    raw = payload.get("top_entity_chart_default_color")
    if not isinstance(raw, str):
        return ""

    return raw.strip()


def load_selected_kpis(settings_file: Path) -> list[str]:
    """Load selected KPI keys from JSON settings file."""
    if not settings_file.exists():
        return DEFAULT_SELECTED_KPIS.copy()

    try:
        payload = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return DEFAULT_SELECTED_KPIS.copy()

    raw = payload.get("selected_kpis")
    if not isinstance(raw, list):
        return DEFAULT_SELECTED_KPIS.copy()

    available_raw = payload.get("available_kpis")
    available = None
    if isinstance(available_raw, list):
        cleaned_available: list[str] = []
        for item in available_raw:
            if isinstance(item, str) and item.strip() and item.strip() not in cleaned_available:
                cleaned_available.append(item.strip())
        if cleaned_available:
            available = set(cleaned_available)

    selected: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        key = item.strip()
        if not key or key in selected:
            continue
        if available is not None and key not in available:
            continue
        selected.append(key)

    return selected or DEFAULT_SELECTED_KPIS.copy()


def load_selected_filter_fields(settings_file: Path, allowed_fields: list[str], max_filters: int = 3) -> list[str]:
    """Load selected non-date filter fields from JSON settings file."""
    if not allowed_fields:
        return []

    allowed: list[str] = []
    for item in allowed_fields:
        key = str(item).strip()
        if key and key not in allowed:
            allowed.append(key)

    fallback = [key for key in DEFAULT_SELECTED_FILTER_FIELDS if key in allowed]
    if not fallback:
        fallback = allowed[:max(max_filters, 1)]

    if not settings_file.exists():
        return fallback[:max(max_filters, 1)]

    try:
        payload = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback[:max(max_filters, 1)]

    available_raw = payload.get("available_filter_fields")
    available = set(allowed)
    if isinstance(available_raw, list):
        configured_available: set[str] = set()
        for item in available_raw:
            if not isinstance(item, str):
                continue
            key = item.strip()
            if key in available:
                configured_available.add(key)
        if configured_available:
            available = configured_available

    selected_raw = payload.get("selected_filter_fields")
    if not isinstance(selected_raw, list):
        return [key for key in fallback if key in available][:max(max_filters, 1)]

    selected: list[str] = []
    for item in selected_raw:
        if not isinstance(item, str):
            continue
        key = item.strip()
        if not key or key in selected:
            continue
        if key not in available:
            continue
        selected.append(key)
        if len(selected) >= max(max_filters, 1):
            break

    if selected:
        return selected

    return [key for key in fallback if key in available][:max(max_filters, 1)]


def load_selected_top_entity_charts(
    settings_file: Path,
    allowed_chart_keys: list[str],
    max_charts: int = 2,
) -> list[str]:
    """Load selected top-entity chart keys from JSON settings file."""
    if not allowed_chart_keys:
        return []

    allowed: list[str] = []
    for item in allowed_chart_keys:
        key = str(item).strip()
        if key and key not in allowed:
            allowed.append(key)

    fallback = [key for key in DEFAULT_SELECTED_TOP_ENTITY_CHARTS if key in allowed]
    if not fallback:
        fallback = allowed[:max(max_charts, 1)]

    if not settings_file.exists():
        return fallback[:max(max_charts, 1)]

    try:
        payload = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback[:max(max_charts, 1)]

    available_raw = payload.get("available_top_entity_charts")
    available = set(allowed)
    if isinstance(available_raw, list):
        configured_available: set[str] = set()
        for item in available_raw:
            if not isinstance(item, str):
                continue
            key = item.strip()
            if key in available:
                configured_available.add(key)
        if configured_available:
            available = configured_available

    selected_raw = payload.get("selected_top_entity_charts")
    if not isinstance(selected_raw, list):
        return [key for key in fallback if key in available][:max(max_charts, 1)]

    selected: list[str] = []
    for item in selected_raw:
        if not isinstance(item, str):
            continue
        key = item.strip()
        if not key or key in selected:
            continue
        if key not in available:
            continue
        selected.append(key)
        if len(selected) >= max(max_charts, 1):
            break

    if selected:
        return selected

    return [key for key in fallback if key in available][:max(max_charts, 1)]


def load_selected_deep_dive_table_columns(
    settings_file: Path,
    allowed_column_keys: list[str],
    max_columns: int = 12,
) -> list[str]:
    """Load selected deep-dive table column keys from JSON settings file."""
    if not allowed_column_keys:
        return []

    allowed: list[str] = []
    for item in allowed_column_keys:
        key = str(item).strip()
        if key and key not in allowed:
            allowed.append(key)

    fallback = [key for key in DEFAULT_SELECTED_DEEP_DIVE_TABLE_COLUMNS if key in allowed]
    if not fallback:
        fallback = allowed[:max(max_columns, 1)]

    if not settings_file.exists():
        return fallback[:max(max_columns, 1)]

    try:
        payload = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback[:max(max_columns, 1)]

    available_raw = payload.get("available_deep_dive_table_columns")
    available = set(allowed)
    if isinstance(available_raw, list):
        configured_available: set[str] = set()
        for item in available_raw:
            if not isinstance(item, str):
                continue
            key = item.strip()
            if key in available:
                configured_available.add(key)
        if configured_available:
            available = configured_available

    selected_raw = payload.get("selected_deep_dive_table_columns")
    if not isinstance(selected_raw, list):
        return [key for key in fallback if key in available][:max(max_columns, 1)]

    selected: list[str] = []
    for item in selected_raw:
        if not isinstance(item, str):
            continue
        key = item.strip()
        if not key or key in selected:
            continue
        if key not in available:
            continue
        selected.append(key)
        if len(selected) >= max(max_columns, 1):
            break

    if selected:
        return selected

    return [key for key in fallback if key in available][:max(max_columns, 1)]


def load_deep_dive_default_page_size(
    settings_file: Path,
    default_page_size: int = 100,
    min_page_size: int = 1,
    max_page_size: int = 1000,
) -> int:
    """Load default deep-dive page size from JSON settings file."""
    fallback = default_page_size if default_page_size > 0 else 100

    if not settings_file.exists():
        return fallback

    try:
        payload = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback

    raw = payload.get("deep_dive_default_page_size")
    try:
        parsed = int(str(raw).strip())
    except (TypeError, ValueError):
        return fallback

    if parsed < max(min_page_size, 1):
        return fallback
    if parsed > max(max_page_size, max(min_page_size, 1)):
        return fallback

    return parsed


def load_selected_deep_dive_hierarchy_fields(
    settings_file: Path,
    allowed_field_keys: list[str],
    max_levels: int = 3,
) -> list[str]:
    """Load selected deep-dive hierarchy field keys from JSON settings file."""
    if not allowed_field_keys:
        return []

    allowed: list[str] = []
    for item in allowed_field_keys:
        key = str(item).strip()
        if key and key not in allowed:
            allowed.append(key)

    fallback = [key for key in DEFAULT_SELECTED_DEEP_DIVE_HIERARCHY_FIELDS if key in allowed]
    if not fallback:
        fallback = allowed[:max(max_levels, 1)]

    if not settings_file.exists():
        return fallback[:max(max_levels, 1)]

    try:
        payload = json.loads(settings_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback[:max(max_levels, 1)]

    available_raw = payload.get("available_deep_dive_hierarchy_fields")
    available = set(allowed)
    if isinstance(available_raw, list):
        configured_available: set[str] = set()
        for item in available_raw:
            if not isinstance(item, str):
                continue
            key = item.strip()
            if key in available:
                configured_available.add(key)
        if configured_available:
            available = configured_available

    selected_raw = payload.get("selected_deep_dive_hierarchy_fields")
    if not isinstance(selected_raw, list):
        return [key for key in fallback if key in available][:max(max_levels, 1)]

    selected: list[str] = []
    for item in selected_raw:
        if not isinstance(item, str):
            continue
        key = item.strip()
        if not key or key in selected:
            continue
        if key not in available:
            continue
        selected.append(key)
        if len(selected) >= max(max_levels, 1):
            break

    if selected:
        return selected

    return [key for key in fallback if key in available][:max(max_levels, 1)]
