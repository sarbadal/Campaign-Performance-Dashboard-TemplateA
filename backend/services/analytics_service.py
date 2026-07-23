from __future__ import annotations

import os

import pandas as pd


TOP_N_CAMPAIGNS = 3
TOP_N_PLATFORMS = 10
CURRENCY_SYMBOL = os.getenv("KPI_CURRENCY_SYMBOL", "RM").strip()


def _amount_series(df: pd.DataFrame) -> pd.Series:
    if "AMOUNT_SPENT" not in df.columns:
        return pd.Series(dtype="float64")

    raw = df["AMOUNT_SPENT"].fillna("").astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(raw, errors="coerce").fillna(0.0)


def top_campaigns_by_spend(df: pd.DataFrame, top_n: int = TOP_N_CAMPAIGNS, currency_symbol: str = CURRENCY_SYMBOL) -> list[dict[str, str]]:
    """Return top campaigns by spend from a shared DataFrame."""
    if "CAMPAIGN_NAME" not in df.columns or top_n <= 0:
        return []

    working = pd.DataFrame(
        {
            "campaign_name": df["CAMPAIGN_NAME"].fillna("").astype(str).str.strip(),
            "amount_spent": _amount_series(df),
        }
    )

    working = working[working["campaign_name"] != ""]
    if working.empty:
        return []

    grouped = (
        working.groupby("campaign_name", as_index=False)["amount_spent"]
        .sum()
        .sort_values("amount_spent", ascending=False)
        .head(top_n)
    )

    money_prefix = f"{currency_symbol} " if currency_symbol else ""
    rows: list[dict[str, str]] = []
    for idx, row in grouped.reset_index(drop=True).iterrows():
        rows.append(
            {
                "rank": str(idx + 1),
                "campaign_name": str(row["campaign_name"]),
                "amount_spent": f"{money_prefix}{float(row['amount_spent']):,.2f}",
            }
        )
    return rows


def top_platforms_by_spend(df: pd.DataFrame, top_n: int = TOP_N_PLATFORMS, currency_symbol: str = CURRENCY_SYMBOL) -> list[dict[str, str]]:
    """Return top platforms by spend from a shared DataFrame."""
    if "PLATFORM" not in df.columns or top_n <= 0:
        return []

    working = pd.DataFrame(
        {
            "platform": df["PLATFORM"].fillna("").astype(str).str.strip(),
            "amount_spent": _amount_series(df),
        }
    )

    working = working[working["platform"] != ""]
    if working.empty:
        return []

    grouped = (
        working.groupby("platform", as_index=False)["amount_spent"]
        .sum()
        .sort_values("amount_spent", ascending=False)
        .head(top_n)
    )

    money_prefix = f"{currency_symbol} " if currency_symbol else ""
    rows: list[dict[str, str]] = []
    for idx, row in grouped.reset_index(drop=True).iterrows():
        rows.append(
            {
                "rank": str(idx + 1),
                "platform": str(row["platform"]),
                "amount_spent": f"{money_prefix}{float(row['amount_spent']):,.2f}",
                "amount_spent_value": float(row["amount_spent"]),
            }
        )
    return rows
