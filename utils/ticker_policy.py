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

    def _has_sessions(required_sessions: int) -> bool:
        return not is_post_listing_only or trading_days >= required_sessions

    if is_post_listing_only and trading_days < 252:
        unavailable_reasons["52_week"] = (
            f"{ticker.upper()} 自 {policy['listing_date']} 在 Nasdaq 上市，"
            "上市后交易日不足 252 个"
        )

    technical_windows = {
        "ma_5": 5,
        "ma_20": 20,
        "ma_50": 50,
        "ma_200": 200,
        "bollinger_20": 20,
        "rsi_14": 15,
        "macd": 35,
    }
    for indicator, required_sessions in technical_windows.items():
        if not _has_sessions(required_sessions):
            unavailable_reasons[indicator] = (
                f"\u4e0a\u5e02\u540e\u4ec5 {trading_days} \u4e2a\u4ea4\u6613\u65e5\uff0c"
                f"\u4e0d\u8db3 {required_sessions} \u4e2a\u4ea4\u6613\u65e5"
            )

    return {
        "ticker": ticker.upper(),
        "listing_date": policy.get("listing_date"),
        "trading_days": trading_days,
        "has_52_week_history": not is_post_listing_only or trading_days >= 252,
        **{
            f"has_{indicator}": _has_sessions(required_sessions)
            for indicator, required_sessions in technical_windows.items()
        },
        "unavailable_reasons": unavailable_reasons,
    }
