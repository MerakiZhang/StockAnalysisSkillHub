"""China-market datetime conversion and display helpers."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_CN_TZ = ZoneInfo("Asia/Shanghai")


def datetime_to_ts_ms(value: object) -> int:
    """Convert a datetime-like value to epoch milliseconds without inventing dates."""
    if value is None:
        raise ValueError("datetime value is required")
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"invalid datetime value: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_CN_TZ)
    return int(parsed.timestamp() * 1000)


def ts_open_to_ms(ts_open: float) -> float:
    value = float(ts_open)
    if value <= 0:
        return value
    return value * 1000.0 if value < 1e10 else value


def format_epoch_for_display(ts_open: float, *, short: bool = False) -> str:
    """Display an epoch timestamp using the A-share market's Asia/Shanghai timezone."""
    seconds = float(ts_open)
    if seconds > 1e12:
        seconds /= 1000.0
    fmt = "%Y-%m-%d %H:%M" if short else "%Y-%m-%d %H:%M:%S"
    return datetime.fromtimestamp(seconds, tz=_CN_TZ).strftime(fmt)
