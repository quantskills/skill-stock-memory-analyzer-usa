"""Ticker-specific history boundaries for listed instruments."""

from __future__ import annotations

import pandas as pd


TICKER_POLICIES = {
    "SKHY": {
        "listing_date": "2026-07-10",
        "history_policy": "post_listing_only",
        "underlying_ticker": "000660.KS",
        "underlying_market": "KRX",
    }
}


def get_ticker_policy(ticker: str) -> dict:
    """Return a copy of the configured policy for a US ticker."""
    return dict(TICKER_POLICIES.get(ticker.upper(), {}))


def filter_price_history(ticker: str, price_df: pd.DataFrame) -> pd.DataFrame:
    """Keep only price observations permitted for the specified ticker."""
    policy = get_ticker_policy(ticker)
    result = price_df.copy()
    if policy.get("history_policy") != "post_listing_only":
        return result

    result.index = pd.to_datetime(result.index)
    return result.loc[result.index >= pd.Timestamp(policy["listing_date"])]


def build_history_context(ticker: str, price_df: pd.DataFrame) -> dict:
    """Describe the usable listing history and long-window availability."""
    policy = get_ticker_policy(ticker)
    trading_days = len(price_df)
    is_post_listing_only = policy.get("history_policy") == "post_listing_only"
    unavailable_reasons = {}

    if is_post_listing_only and trading_days < 252:
        unavailable_reasons["52_week"] = (
            f"{ticker.upper()} 自 {policy['listing_date']} 在 Nasdaq 上市，"
            "上市后交易日不足 252 个"
        )

    return {
        "ticker": ticker.upper(),
        "listing_date": policy.get("listing_date"),
        "trading_days": trading_days,
        "has_52_week_history": not is_post_listing_only or trading_days >= 252,
        "unavailable_reasons": unavailable_reasons,
    }
