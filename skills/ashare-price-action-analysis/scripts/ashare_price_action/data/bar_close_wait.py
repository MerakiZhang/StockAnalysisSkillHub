"""Closed-bar checks for A-share snapshots."""
from __future__ import annotations

import re
import time

from ashare_price_action.data.base import KlineBar

_TIMEFRAME_SECONDS_RE = re.compile(r"^(\d+)([mhdw])$", re.IGNORECASE)
_TIMEFRAME_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


def timeframe_to_seconds(timeframe: str) -> int | None:
    text = str(timeframe or "").strip().lower()
    if text in _TIMEFRAME_SECONDS:
        return _TIMEFRAME_SECONDS[text]
    match = _TIMEFRAME_SECONDS_RE.fullmatch(text)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2).lower()
    seconds = {"m": 60, "h": 3600, "d": 86400, "w": 604800}[unit]
    return amount * seconds


def _looks_like_ashare_symbol(symbol: str | None) -> bool:
    from ashare_price_action.data.ashare_common import normalize_ashare_symbol

    return bool(normalize_ashare_symbol(symbol or ""))


def is_bar_still_forming(
    bar: KlineBar,
    timeframe: str,
    *,
    now_ms: int | None = None,
    symbol: str | None = None,
) -> bool:
    if bar.closed:
        return False
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    text = str(timeframe or "").strip().lower()
    if text == "1d" and _looks_like_ashare_symbol(symbol):
        from ashare_price_action.data.ashare_common import ashare_session_open

        if not ashare_session_open():
            return False
    duration = timeframe_to_seconds(text)
    if duration is None:
        return True
    from ashare_price_action.data.datetime_ts import ts_open_to_ms

    close_ms = int(ts_open_to_ms(bar.ts_open)) + duration * 1000
    return now_ms < close_ms


def has_forming_bar_at_head(
    bars_newest_first: list[KlineBar],
    timeframe: str | None = None,
    *,
    now_ms: int | None = None,
    symbol: str | None = None,
) -> bool:
    if not bars_newest_first:
        return False
    if not timeframe:
        return not bars_newest_first[0].closed
    return is_bar_still_forming(
        bars_newest_first[0],
        timeframe,
        now_ms=now_ms,
        symbol=symbol,
    )
