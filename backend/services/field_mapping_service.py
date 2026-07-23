from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DEFAULT_FIELD_MAPPING: dict[str, str] = {
    "DATE": "DATE",
    "CAMPAIGN_NAME": "CAMPAIGN_NAME",
    "AMOUNT_SPENT": "AMOUNT_SPENT",
    "IMPRESSIONS": "IMPRESSIONS",
    "CLICKS": "CLICKS",
    "CONVERSIONS": "CONVERSIONS",
    "LEADS": "LEADS",
    "VIDEO_VIEWS": "VIDEO_VIEWS",
    "LIKES": "LIKES",
    "VIDEO_COMPLETION": "VIDEO_PLAYS_AT_100",
    "REACH": "REACH",
}


def load_field_mapping(mapping_file: Path) -> dict[str, str]:
    """Load canonical->source field name mapping from JSON file."""
    if not mapping_file.exists():
        return DEFAULT_FIELD_MAPPING.copy()

    try:
        payload = json.loads(mapping_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return DEFAULT_FIELD_MAPPING.copy()

    if not isinstance(payload, dict):
        return DEFAULT_FIELD_MAPPING.copy()

    mapping: dict[str, str] = DEFAULT_FIELD_MAPPING.copy()
    for canonical, source in payload.items():
        if not isinstance(canonical, str) or not isinstance(source, str):
            continue
        c = canonical.strip()
        s = source.strip()
        if c and s:
            mapping[c] = s

    return mapping


def apply_field_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Return a copy with source columns renamed to canonical names where needed."""
    if df.empty:
        return df

    rename_map: dict[str, str] = {}
    for canonical, source in mapping.items():
        if canonical in df.columns:
            continue
        if source in df.columns:
            rename_map[source] = canonical

    if not rename_map:
        return df

    return df.rename(columns=rename_map)
