"""A-share symbol and exchange-session helpers used by the live data adapter."""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

_CN_TZ = ZoneInfo("Asia/Shanghai")
_SYMBOL_RE = re.compile(
    r"^(?:(sh|sz|bj)[\s-]*)?(\d{6})(?:\.(?:sh|sz|bj))?$",
    re.IGNORECASE,
)
_INDEX_DIGITS = {
    "000300",
    "000016",
    "000905",
    "000852",
    "399001",
    "399006",
    "399300",
}
PRESET_SYMBOLS = ("000001", "600519", "000300", "399006")


def normalize_ashare_symbol(symbol: str) -> str:
    """Return a six-digit stock code or a prefixed known index identifier."""
    match = _SYMBOL_RE.fullmatch(str(symbol or "").strip())
    if not match:
        return ""
    prefix, digits = match.group(1), match.group(2)
    if prefix and (digits in _INDEX_DIGITS or (prefix.lower() == "sh" and digits == "000001")):
        return f"{prefix.lower()}{digits}"
    return digits


def is_index_symbol(symbol: str) -> bool:
    normalized = normalize_ashare_symbol(symbol)
    if normalized.startswith(("sh", "sz")):
        return True
    return normalized in _INDEX_DIGITS


def index_symbol_for_api(symbol: str) -> str:
    normalized = normalize_ashare_symbol(symbol)
    if normalized.startswith(("sh", "sz")):
        return normalized
    if normalized.startswith("399"):
        return f"sz{normalized}"
    return f"sh{normalized}"


def cn_now() -> datetime:
    return datetime.now(tz=_CN_TZ)


def ashare_session_open(now: datetime | None = None) -> bool:
    """Check the weekday continuous-session clock; exchange holidays need data checks."""
    now = now or cn_now()
    if now.weekday() >= 5:
        return False
    minute = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= minute < 11 * 60 + 30 or 13 * 60 <= minute < 15 * 60


def ashare_trading_day(now: datetime | None = None) -> bool:
    now = now or cn_now()
    if now.weekday() >= 5:
        return False
    minute = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= minute < 15 * 60


def ashare_head_bar_live(timeframe: str, now: datetime | None = None) -> bool:
    """Return the session-clock status; callers must also verify the bar is for today."""
    if str(timeframe or "").strip().lower() == "1d":
        return ashare_trading_day(now)
    return ashare_session_open(now)
