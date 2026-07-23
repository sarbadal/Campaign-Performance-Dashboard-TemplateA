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
