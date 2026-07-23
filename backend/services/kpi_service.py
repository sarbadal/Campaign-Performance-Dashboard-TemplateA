from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.services.dataframe_service import DataframeRequest, get_campaign_dataframe
from backend.services.kpi_calculation_service import KpiSummary, build_kpi_summary_from_dataframe


KPI_DEFINITIONS: dict[str, str] = {
    "total_spend": "Spend",
    "total_impressions": "Impressions",
    "total_reach": "Reach",
    "total_clicks": "Clicks",
    "total_conversions": "Conversions",
    "total_leads": "Leads",
    "total_video_views": "Video Views",
    "total_likes": "Likes",
    "total_video_completion": "Video Completion",
    "total_campaigns": "Unique Campaigns",
    "avg_ctr_percent": "CTR",
    "avg_cpc": "CPC",
    "cpm": "CPM",
    "cvv": "CVV",
}


@dataclass(frozen=True)
class KpiSummaryRequest:
    data_file: Path
    db_backend: str
    sqlite_db_file: Path
    mysql_config: dict[str, object]
    field_mapping_file: Path
    cache_ttl_seconds: int = 300


@dataclass(frozen=True)
class KpiCardsRequest:
    summary: KpiSummary
    selected_keys: list[str]
    currency_symbol: str = "RM"

def build_kpi_summary(request: KpiSummaryRequest) -> KpiSummary:
    df = get_campaign_dataframe(
        DataframeRequest(
            data_file=request.data_file,
            db_backend=request.db_backend,
            sqlite_db_file=request.sqlite_db_file,
            mysql_config=request.mysql_config,
            field_mapping_file=request.field_mapping_file,
            cache_ttl_seconds=request.cache_ttl_seconds,
        )
    )
    return build_kpi_summary_from_dataframe(df)


def build_kpi_cards(request: KpiCardsRequest) -> list[dict[str, str]]:
    """Build display-ready KPI cards using selected KPI keys."""
    summary = request.summary
    selected_keys = request.selected_keys
    currency_symbol = request.currency_symbol

    if not selected_keys:
        selected_keys = list(KPI_DEFINITIONS.keys())

    value_map: dict[str, float | int] = {
        "total_spend": summary.total_spend,
        "total_impressions": summary.total_impressions,
        "total_reach": summary.total_reach,
        "total_clicks": summary.total_clicks,
        "total_conversions": summary.total_conversions,
        "total_leads": summary.total_leads,
        "total_video_views": summary.total_video_views,
        "total_likes": summary.total_likes,
        "total_video_completion": summary.total_video_completion,
        "total_campaigns": summary.total_campaigns,
        "avg_ctr_percent": summary.avg_ctr_percent,
        "avg_cpc": summary.avg_cpc,
        "cpm": summary.cpm,
        "cvv": summary.cvv,
    }

    cards: list[dict[str, str]] = []
    money_prefix = f"{currency_symbol} " if currency_symbol else ""
    def _format_default(value: float | int) -> str:
        return str(value)

    formatters = {
        "total_spend": lambda value: f"{money_prefix}{value:,.0f}",
        "total_impressions": lambda value: f"{int(value):,}",
        "total_reach": lambda value: f"{int(value):,}",
        "total_clicks": lambda value: f"{int(value):,}",
        "total_conversions": lambda value: f"{int(value):,}",
        "total_leads": lambda value: f"{int(value):,}",
        "total_video_views": lambda value: f"{int(value):,}",
        "total_likes": lambda value: f"{int(value):,}",
        "total_video_completion": lambda value: f"{int(value):,}",
        "total_campaigns": lambda value: f"{int(value):,}",
        "avg_ctr_percent": lambda value: f"{value:.2f}%",
        "avg_cpc": lambda value: f"{money_prefix}{value:.2f}",
        "cpm": lambda value: f"{money_prefix}{value:.2f}",
        "cvv": lambda value: f"{money_prefix}{value:.2f}",
    }

    for key in selected_keys:
        if key not in KPI_DEFINITIONS:
            continue

        raw = value_map[key]
        formatter = formatters.get(key, _format_default)
        value = formatter(raw)

        cards.append({
            "key": key,
            "label": KPI_DEFINITIONS[key],
            "value": value,
        })

    return cards
