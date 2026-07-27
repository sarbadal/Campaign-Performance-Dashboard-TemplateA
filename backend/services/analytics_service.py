from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd


TOP_N_PLATFORMS = 10
CURRENCY_SYMBOL = os.getenv("KPI_CURRENCY_SYMBOL", "RM").strip()
DEFAULT_TOP_KPI_KEY = "total_spend"
TOP_KPI_KEYS = [
    "total_spend",
    "total_impressions",
    "total_clicks",
    "total_reach",
    "total_conversions",
    "total_leads",
    "total_video_views",
    "total_likes",
    "total_video_completion",
    # "avg_ctr_percent",
    # "avg_cpc",
    # "cpm",
    # "cvv",
]

_SUM_KPI_COLUMN_MAP: dict[str, str] = {
    "total_spend": "AMOUNT_SPENT",
    "total_impressions": "IMPRESSIONS",
    "total_reach": "REACH",
    "total_clicks": "CLICKS",
    "total_conversions": "CONVERSIONS",
    "total_leads": "LEADS",
    "total_video_views": "VIDEO_VIEWS",
    "total_likes": "LIKES",
    "total_video_completion": "VIDEO_COMPLETION",
}
TopEntityRow = dict[str, str | float]


@dataclass(frozen=True)
class TopEntityKpiRequest:
    df: pd.DataFrame
    entity_column: str
    entity_key: str
    top_n: int
    kpi_key: str = DEFAULT_TOP_KPI_KEY
    currency_symbol: str = CURRENCY_SYMBOL


@dataclass(frozen=True)
class DualAxisKpiSeriesRequest:
    df: pd.DataFrame
    left_kpi_key: str
    right_kpi_key: str
    granularity: str = "daily"


_TREND_GRANULARITIES = {"daily", "weekly", "monthly", "quarterly", "yearly"}


def _resolve_trend_granularity(granularity: str) -> str:
    cleaned = str(granularity or "").strip().lower()
    if cleaned in _TREND_GRANULARITIES:
        return cleaned
    return "daily"


def _bucket_dates(series: pd.Series, granularity: str) -> pd.Series:
    normalized = pd.to_datetime(series, errors="coerce")
    if granularity == "daily":
        return normalized.dt.floor("D")
    if granularity == "weekly":
        # Monday-start week bucket.
        return (normalized - pd.to_timedelta(normalized.dt.weekday, unit="D")).dt.floor("D")
    if granularity == "monthly":
        return normalized.dt.to_period("M").dt.start_time
    if granularity == "quarterly":
        return normalized.dt.to_period("Q").dt.start_time
    if granularity == "yearly":
        return normalized.dt.to_period("Y").dt.start_time
    return normalized.dt.floor("D")


def _format_trend_bucket_labels(bucket_dates: pd.Series, granularity: str) -> list[str]:
    stamps = pd.to_datetime(bucket_dates, errors="coerce")
    if granularity == "monthly":
        return [value.strftime("%Y-%m") for value in stamps]
    if granularity == "quarterly":
        return [f"{value.year}-Q{((value.month - 1) // 3) + 1}" for value in stamps]
    if granularity == "yearly":
        return [value.strftime("%Y") for value in stamps]
    return [value.strftime("%Y-%m-%d") for value in stamps]


def _numeric_column_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(dtype="float64")

    raw = df[column].fillna("").astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(raw, errors="coerce").fillna(0.0)


def _resolve_top_kpi_key(kpi_key: str) -> str:
    cleaned = str(kpi_key or "").strip()
    if cleaned in TOP_KPI_KEYS:
        return cleaned
    return DEFAULT_TOP_KPI_KEY


def _format_kpi_value(kpi_key: str, value: float, currency_symbol: str) -> str:
    money_prefix = f"{currency_symbol} " if currency_symbol else ""
    if kpi_key == "avg_ctr_percent":
        return f"{value:.2f}%"
    if kpi_key in {"total_spend", "avg_cpc", "cpm", "cvv"}:
        return f"{money_prefix}{value:,.2f}"
    return f"{int(round(value)):,}"


def _kpi_value_for_grouped(grouped: pd.DataFrame, kpi_key: str) -> pd.Series:
    if kpi_key in _SUM_KPI_COLUMN_MAP:
        return grouped[_SUM_KPI_COLUMN_MAP[kpi_key]].astype("float64")

    spend = grouped["AMOUNT_SPENT"].astype("float64")
    impressions = grouped["IMPRESSIONS"].astype("float64")
    clicks = grouped["CLICKS"].astype("float64")
    video_views = grouped["VIDEO_VIEWS"].astype("float64")

    derived_kpi_map: dict[str, pd.Series] = {
        "avg_ctr_percent": clicks.div(impressions.where(impressions != 0), fill_value=0.0).fillna(0.0) * 100.0,
        "avg_cpc": spend.div(clicks.where(clicks != 0), fill_value=0.0).fillna(0.0),
        "cpm": (spend.div(impressions.where(impressions != 0), fill_value=0.0).fillna(0.0)) * 1000.0,
        "cvv": spend.div(video_views.where(video_views != 0), fill_value=0.0).fillna(0.0),
    }
    return derived_kpi_map.get(kpi_key, grouped["AMOUNT_SPENT"].astype("float64"))


def _top_entities_by_kpi(request: TopEntityKpiRequest) -> list[TopEntityRow]:
    if request.entity_column not in request.df.columns or request.top_n <= 0:
        return []

    normalized_kpi_key = _resolve_top_kpi_key(request.kpi_key)
    working = pd.DataFrame({
        request.entity_key: request.df[request.entity_column].fillna("").astype(str).str.strip(),
        "AMOUNT_SPENT": _numeric_column_series(request.df, "AMOUNT_SPENT"),
        "IMPRESSIONS": _numeric_column_series(request.df, "IMPRESSIONS"),
        "CLICKS": _numeric_column_series(request.df, "CLICKS"),
        "VIDEO_VIEWS": _numeric_column_series(request.df, "VIDEO_VIEWS"),
        "REACH": _numeric_column_series(request.df, "REACH"),
        "CONVERSIONS": _numeric_column_series(request.df, "CONVERSIONS"),
        "LEADS": _numeric_column_series(request.df, "LEADS"),
        "LIKES": _numeric_column_series(request.df, "LIKES"),
        "VIDEO_COMPLETION": _numeric_column_series(request.df, "VIDEO_COMPLETION"),
    })

    working = working[working[request.entity_key] != ""]
    if working.empty:
        return []

    grouped = working.groupby(request.entity_key, as_index=False).sum(numeric_only=True)
    grouped["kpi_value"] = _kpi_value_for_grouped(grouped, normalized_kpi_key)
    grouped = grouped.sort_values("kpi_value", ascending=False).head(request.top_n)

    rows: list[TopEntityRow] = []
    for idx, row in grouped.reset_index(drop=True).iterrows():
        numeric_value = float(row["kpi_value"])
        rows.append(
            {
                "rank": str(idx + 1),
                request.entity_key: str(row[request.entity_key]),
                "kpi_display": _format_kpi_value(normalized_kpi_key, numeric_value, request.currency_symbol),
                "kpi_value": numeric_value,
            }
        )
    return rows


def top_entities_by_kpi(request: TopEntityKpiRequest) -> list[TopEntityRow]:
    """Return top entities by selected KPI from a shared DataFrame."""
    return _top_entities_by_kpi(request)


def dual_axis_kpi_series(request: DualAxisKpiSeriesRequest) -> dict[str, list[float | str]]:
    """Return date-aligned KPI series for a dual-axis line chart."""
    if "DATE" not in request.df.columns:
        return {
            "labels": [],
            "left_values": [],
            "right_values": [],
        }

    left_kpi_key = _resolve_top_kpi_key(request.left_kpi_key)
    right_kpi_key = _resolve_top_kpi_key(request.right_kpi_key)
    granularity = _resolve_trend_granularity(request.granularity)

    working = pd.DataFrame({
        "DATE": pd.to_datetime(request.df["DATE"], errors="coerce"),
        "AMOUNT_SPENT": _numeric_column_series(request.df, "AMOUNT_SPENT"),
        "IMPRESSIONS": _numeric_column_series(request.df, "IMPRESSIONS"),
        "CLICKS": _numeric_column_series(request.df, "CLICKS"),
        "VIDEO_VIEWS": _numeric_column_series(request.df, "VIDEO_VIEWS"),
        "REACH": _numeric_column_series(request.df, "REACH"),
        "CONVERSIONS": _numeric_column_series(request.df, "CONVERSIONS"),
        "LEADS": _numeric_column_series(request.df, "LEADS"),
        "LIKES": _numeric_column_series(request.df, "LIKES"),
        "VIDEO_COMPLETION": _numeric_column_series(request.df, "VIDEO_COMPLETION"),
    }).dropna(subset=["DATE"])

    if working.empty:
        return {
            "labels": [],
            "left_values": [],
            "right_values": [],
        }

    working["DATE_BUCKET"] = _bucket_dates(working["DATE"], granularity)
    working = working.dropna(subset=["DATE_BUCKET"])

    grouped = (
        working
        .groupby("DATE_BUCKET", as_index=False)
        .sum(numeric_only=True)
        .sort_values("DATE_BUCKET")
    )

    left_series = _kpi_value_for_grouped(grouped, left_kpi_key).astype("float64").fillna(0.0)
    right_series = _kpi_value_for_grouped(grouped, right_kpi_key).astype("float64").fillna(0.0)

    labels = _format_trend_bucket_labels(grouped["DATE_BUCKET"], granularity)
    left_values = [float(value) for value in left_series.tolist()]
    right_values = [float(value) for value in right_series.tolist()]

    return {
        "labels": labels,
        "left_values": left_values,
        "right_values": right_values,
    }
