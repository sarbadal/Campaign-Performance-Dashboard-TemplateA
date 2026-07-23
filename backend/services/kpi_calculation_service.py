from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class KpiSummary:
    total_spend: float
    total_impressions: int
    total_clicks: int
    total_conversions: int
    total_leads: int
    total_video_views: int
    total_likes: int
    total_video_completion: int
    total_reach: int
    total_campaigns: int
    avg_ctr_percent: float
    avg_cpc: float
    cpm: float
    cvv: float
    date_min: str | None
    date_max: str | None


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(dtype="float64")

    series = df[column].fillna("").astype(str).str.replace(",", "", regex=False).str.strip()
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0)
    return numeric


def _date_bounds(df: pd.DataFrame) -> tuple[str | None, str | None]:
    if "DATE" not in df.columns:
        return None, None

    dates = pd.to_datetime(df["DATE"], errors="coerce")
    valid_dates = dates.dropna()
    if valid_dates.empty:
        return None, None

    return valid_dates.min().strftime("%Y-%m-%d"), valid_dates.max().strftime("%Y-%m-%d")


def build_kpi_summary_from_dataframe(df: pd.DataFrame) -> KpiSummary:
    spend = _numeric_series(df, "AMOUNT_SPENT")
    impressions = _numeric_series(df, "IMPRESSIONS")
    clicks = _numeric_series(df, "CLICKS")
    conversions = _numeric_series(df, "CONVERSIONS")
    leads = _numeric_series(df, "LEADS")
    video_views = _numeric_series(df, "VIDEO_VIEWS")
    likes = _numeric_series(df, "LIKES")
    video_completion = _numeric_series(df, "VIDEO_COMPLETION")
    reach = _numeric_series(df, "REACH")

    total_spend = float(spend.sum())
    total_impressions = int(round(float(impressions.sum())))
    total_clicks = int(round(float(clicks.sum())))
    total_conversions = int(round(float(conversions.sum())))
    total_leads = int(round(float(leads.sum())))
    total_video_views = int(round(float(video_views.sum())))
    total_likes = int(round(float(likes.sum())))
    total_video_completion = int(round(float(video_completion.sum())))
    total_reach = int(round(float(reach.sum())))

    if "CAMPAIGN_NAME" in df.columns:
        campaign_series = df["CAMPAIGN_NAME"].fillna("").astype(str).str.strip()
        total_campaigns = int(campaign_series[campaign_series != ""].nunique())
    else:
        total_campaigns = 0

    date_min, date_max = _date_bounds(df)

    avg_ctr_percent = (total_clicks / total_impressions * 100.0) if total_impressions else 0.0
    avg_cpc = (total_spend / total_clicks) if total_clicks else 0.0
    cpm = (total_spend / total_impressions * 1000.0) if total_impressions else 0.0
    cvv = (total_spend / total_video_views) if total_video_views else 0.0

    return KpiSummary(
        total_spend=total_spend,
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        total_conversions=total_conversions,
        total_leads=total_leads,
        total_video_views=total_video_views,
        total_likes=total_likes,
        total_video_completion=total_video_completion,
        total_reach=total_reach,
        total_campaigns=total_campaigns,
        avg_ctr_percent=avg_ctr_percent,
        avg_cpc=avg_cpc,
        cpm=cpm,
        cvv=cvv,
        date_min=date_min,
        date_max=date_max,
    )
