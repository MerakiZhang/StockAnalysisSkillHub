"""AkShare A-share snapshots using only Sina and Tencent endpoints."""
from __future__ import annotations

import logging
import math
import os
import time
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from ashare_price_action.data.ashare_common import (
    PRESET_SYMBOLS,
    ashare_head_bar_live,
    cn_now,
    index_symbol_for_api,
    is_index_symbol,
    normalize_ashare_symbol,
)
from ashare_price_action.data.base import (
    DataSource,
    DataSourceTransientError,
    KlineBar,
    normalize_kline_bar,
)
from ashare_price_action.data.datetime_ts import datetime_to_ts_ms

logger = logging.getLogger(__name__)

_CN_TZ = ZoneInfo("Asia/Shanghai")
_AK_MIN_INTERVAL_S = 0.9
_SUPPORTED_TIMEFRAMES = ("1h", "4h", "1d")
_last_ak_fetch_mono = 0.0


def _row_time_to_ts_ms(value: Any) -> int:
    if value is None:
        raise ValueError("K 线时间不能为空")
    if isinstance(value, datetime):
        parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_CN_TZ)
        return int(parsed.timestamp() * 1000)
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt).replace(tzinfo=_CN_TZ)
            return int(parsed.timestamp() * 1000)
        except ValueError:
            continue
    return datetime_to_ts_ms(text)


def _normalize_ohlcv_df(df: Any, *, time_col: str) -> Any:
    import pandas as pd

    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    rename: dict[Any, str] = {}
    time_mapped = False
    for col in out.columns:
        name = str(col).strip()
        if name in ("时间", "日期", "date", "datetime", "time", "day"):
            if str(col) == time_col:
                time_mapped = True
            elif not time_mapped:
                rename[col] = time_col
                time_mapped = True
        elif name in ("开盘", "open", "Open"):
            rename[col] = "open"
        elif name in ("收盘", "close", "Close"):
            rename[col] = "close"
        elif name in ("最高", "high", "High"):
            rename[col] = "high"
        elif name in ("最低", "low", "Low"):
            rename[col] = "low"
        elif name in ("成交量", "volume", "Volume"):
            rename[col] = "volume"
        elif name in ("成交额", "amount", "Amount"):
            rename[col] = "amount"
    out = out.rename(columns=rename)
    drop_cols = [
        col
        for col in out.columns
        if str(col).strip() in ("时间", "日期", "date", "datetime", "time", "day")
        and col != time_col
    ]
    if drop_cols:
        out = out.drop(columns=drop_cols, errors="ignore")
    required = ("open", "high", "low", "close")
    if time_col not in out.columns or any(col not in out.columns for col in required):
        return pd.DataFrame()
    if "volume" not in out.columns:
        out["volume"] = 0.0
    if "amount" not in out.columns:
        out["amount"] = 0.0
    numeric = [*required, "volume", "amount"]
    for col in numeric:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=[time_col, *numeric])
    finite = out[numeric].apply(lambda col: col.map(math.isfinite)).all(axis=1)
    positive = (out[list(required)] > 0).all(axis=1)
    geometry = (
        (out["high"] >= out[["open", "close", "low"]].max(axis=1))
        & (out["low"] <= out[["open", "close", "high"]].min(axis=1))
        & (out["volume"] >= 0)
        & (out["amount"] >= 0)
    )
    out = out.loc[finite & positive & geometry]
    return (
        out.drop_duplicates(subset=[time_col], keep="last")
        .sort_values(time_col)
        .reset_index(drop=True)
    )


def _df_to_bars_asc(df: Any, *, time_col: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        rows.append(
            {
                "ts_open": _row_time_to_ts_ms(row[time_col]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "amount": float(row["amount"]),
                "pct_chg": None,
            }
        )
    for index in range(1, len(rows)):
        previous = rows[index - 1]["close"]
        if previous > 0:
            rows[index]["pct_chg"] = (rows[index]["close"] - previous) / previous * 100.0
    return rows


def _merge_ohlcv(chunk: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "ts_open": chunk[0]["ts_open"],
        "open": chunk[0]["open"],
        "high": max(row["high"] for row in chunk),
        "low": min(row["low"] for row in chunk),
        "close": chunk[-1]["close"],
        "volume": sum(row["volume"] for row in chunk),
        "amount": sum(row.get("amount", 0.0) for row in chunk),
        "pct_chg": chunk[-1].get("pct_chg"),
    }


def _resample_rows_to_4h(rows_asc: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Combine four complete 60-minute bars per trading day, never across dates."""
    by_date: dict[Any, list[dict[str, Any]]] = {}
    for row in rows_asc:
        date = datetime.fromtimestamp(int(row["ts_open"]) / 1000, tz=_CN_TZ).date()
        by_date.setdefault(date, []).append(row)
    output: list[dict[str, Any]] = []
    for date in sorted(by_date):
        chunk = by_date[date]
        if len(chunk) == 4:
            output.append(_merge_ohlcv(chunk))
        else:
            logger.warning("跳过 %s 的不完整四小时合成：只有 %d 根小时线", date, len(chunk))
    return output


def _rows_to_kline_bars(rows_newest_first: list[dict[str, Any]], n: int) -> list[KlineBar]:
    bars: list[KlineBar] = []
    for index, row in enumerate(rows_newest_first[:n]):
        bars.append(
            normalize_kline_bar(
                KlineBar(
                    seq=index + 1,
                    ts_open=float(int(row["ts_open"])),
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"],
                    amount=float(row.get("amount", 0.0) or 0.0),
                    pct_chg=row.get("pct_chg"),
                    closed=row.get("closed", index != 0),
                )
            )
        )
    return bars


def _api_symbol(symbol: str) -> str:
    normalized = normalize_ashare_symbol(symbol)
    if is_index_symbol(normalized):
        return index_symbol_for_api(normalized)
    if normalized.startswith(("4", "8", "920")):
        return f"bj{normalized}"
    if normalized.startswith(("5", "6", "9")):
        return f"sh{normalized}"
    return f"sz{normalized}"


class AkShareSource(DataSource):
    """Single-source snapshots: Sina primary, Tencent daily fallback/check."""

    def __init__(self, *, primary: str = "sina", crosscheck: bool = True) -> None:
        primary = str(primary or "sina").strip().lower()
        if primary not in ("sina", "tencent"):
            raise ValueError("primary must be 'sina' or 'tencent'")
        self._primary = primary
        self._crosscheck = bool(crosscheck)
        self._symbol = ""
        self._timeframe = ""
        self._connected = False
        self.last_fetch_meta: dict[str, Any] = {}

    def connect(self) -> None:
        os.environ.setdefault("TQDM_DISABLE", "1")
        try:
            import akshare  # noqa: F401
        except ImportError as exc:
            raise DataSourceTransientError(
                "缺少 akshare，请使用满足 requirements.txt 的 Python 环境"
            ) from exc
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def list_symbols(self) -> list[str]:
        return list(PRESET_SYMBOLS)

    def supported_timeframes(self) -> list[str]:
        return list(_SUPPORTED_TIMEFRAMES)

    def subscribe(self, symbol: str, timeframe: str) -> None:
        if timeframe not in _SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {timeframe!r}; use 1h, 4h or 1d")
        code = normalize_ashare_symbol(symbol)
        if not code:
            raise ValueError("A 股代码无效，请输入 6 位数字或带市场前缀的已知指数代码")
        self._symbol = code
        self._timeframe = timeframe

    def unsubscribe(self) -> None:
        self._symbol = ""
        self._timeframe = ""

    def is_symbol_available(self, symbol: str) -> bool:
        return bool(normalize_ashare_symbol(symbol))

    @staticmethod
    def _throttle() -> None:
        global _last_ak_fetch_mono
        wait = _AK_MIN_INTERVAL_S - (time.monotonic() - _last_ak_fetch_mono)
        if wait > 0:
            time.sleep(wait)
        _last_ak_fetch_mono = time.monotonic()

    @classmethod
    def _call(cls, label: str, fn: Any, *, attempts: int = 3) -> Any:
        last_exc: Exception | None = None
        for attempt in range(attempts):
            cls._throttle()
            try:
                return fn()
            except Exception as exc:
                last_exc = exc
                if attempt + 1 < attempts:
                    time.sleep(1.0 + attempt)
                    logger.debug("%s retry %d: %s", label, attempt + 2, exc)
        assert last_exc is not None
        raise last_exc

    def _daily(self, source: str, symbol: str, n: int) -> list[dict[str, Any]]:
        import akshare as ak

        api_symbol = _api_symbol(symbol)
        end = cn_now().strftime("%Y%m%d")
        start = (cn_now() - timedelta(days=max(n * 3, 500))).strftime("%Y%m%d")
        if source == "sina":
            if is_index_symbol(symbol):
                df = self._call(
                    f"sina index daily {api_symbol}",
                    lambda: ak.stock_zh_index_daily(symbol=api_symbol),
                )
            else:
                df = self._call(
                    f"sina daily {api_symbol}",
                    lambda: ak.stock_zh_a_daily(
                        symbol=api_symbol, start_date=start, end_date=end, adjust="qfq"
                    ),
                )
        elif source == "tencent":
            if is_index_symbol(symbol):
                df = self._call(
                    f"tencent index daily {api_symbol}",
                    lambda: ak.stock_zh_index_daily_tx(
                        symbol=api_symbol, start_date=start, end_date=end
                    ),
                )
            else:
                df = self._call(
                    f"tencent daily {api_symbol}",
                    lambda: ak.stock_zh_a_hist_tx(
                        symbol=api_symbol, start_date=start, end_date=end, adjust="qfq"
                    ),
                )
        else:
            raise ValueError(f"unknown source {source}")
        normalized = _normalize_ohlcv_df(df, time_col="date")
        if normalized.empty:
            return []
        return _df_to_bars_asc(normalized.tail(n + 8), time_col="date")

    def _minute_sina(self, symbol: str, n: int) -> list[dict[str, Any]]:
        import akshare as ak

        api_symbol = _api_symbol(symbol)
        df = self._call(
            f"sina 60m {api_symbol}",
            lambda: ak.stock_zh_a_minute(symbol=api_symbol, period="60", adjust="qfq"),
        )
        normalized = _normalize_ohlcv_df(df, time_col="day")
        if normalized.empty:
            return []
        return _df_to_bars_asc(normalized.tail(n + 12), time_col="day")

    def _fetch_history(
        self, source: str, symbol: str, timeframe: str, n: int
    ) -> list[dict[str, Any]]:
        if timeframe == "1d":
            return self._daily(source, symbol, n)
        rows = self._minute_sina(symbol, n * 4 + 8 if timeframe == "4h" else n)
        if timeframe == "4h":
            return _resample_rows_to_4h(rows)[-n:]
        return rows

    def latest_snapshot(self, n: int) -> list[KlineBar]:
        if not self._connected:
            raise DataSourceTransientError("AkShare 未连接")
        if not self._symbol or not self._timeframe:
            raise DataSourceTransientError("AkShare 未订阅品种/周期")
        fetch_n = max(int(n), 1)
        attempts: list[dict[str, str]] = []
        sources = [self._primary]
        if self._timeframe == "1d":
            sources.append("tencent" if self._primary == "sina" else "sina")
        rows: list[dict[str, Any]] = []
        used = ""
        errors: list[str] = []
        for source in sources:
            try:
                rows = self._fetch_history(source, self._symbol, self._timeframe, fetch_n + 8)
                if not rows:
                    raise DataSourceTransientError("接口返回空数据")
                used = source
                attempts.append({"source": source, "status": "ok"})
                break
            except Exception as exc:
                errors.append(f"{source}: {exc}")
                attempts.append({"source": source, "status": "failed", "error": str(exc)})
        if not rows:
            raise DataSourceTransientError("；".join(errors) or "AkShare 拉取失败")

        latest_date = datetime.fromtimestamp(
            int(rows[-1]["ts_open"]) / 1000, tz=_CN_TZ
        ).date()
        live = ashare_head_bar_live(self._timeframe) and latest_date == cn_now().date()
        rows_newest = list(reversed(rows[-fetch_n:]))
        for index, row in enumerate(rows_newest):
            row["closed"] = not (index == 0 and live)
        index = is_index_symbol(self._symbol)
        self.last_fetch_meta = {
            "provider": used,
            "primary_provider": self._primary,
            "interfaces": (
                ["stock_zh_a_minute"]
                if self._timeframe != "1d"
                else ["stock_zh_index_daily" if index else "stock_zh_a_daily"]
                if used == "sina"
                else ["stock_zh_index_daily_tx" if index else "stock_zh_a_hist_tx"]
            ),
            "adjust": "none" if index else "qfq",
            "symbol": self._symbol,
            "api_symbol": _api_symbol(self._symbol),
            "timeframe": self._timeframe,
            "fetched_at_cn": cn_now().isoformat(timespec="seconds"),
            "attempts": attempts,
            "crosscheck": None,
        }
        if self._timeframe == "1d" and self._crosscheck:
            other = "tencent" if used == "sina" else "sina"
            try:
                other_rows = self._daily(other, self._symbol, min(fetch_n, 10))
                self.last_fetch_meta["crosscheck"] = self._compare_daily(
                    used, rows, other, other_rows
                )
            except Exception as exc:
                self.last_fetch_meta["crosscheck"] = {
                    "provider": other,
                    "status": "failed",
                    "error": str(exc),
                    "action": "仅记录，不修改主快照",
                }
        return _rows_to_kline_bars(rows_newest, fetch_n)

    @staticmethod
    def _compare_daily(
        primary: str,
        primary_rows: list[dict[str, Any]],
        other: str,
        other_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        other_by_ts = {int(row["ts_open"]): row for row in other_rows}
        differences: list[dict[str, Any]] = []
        compared = 0
        for row in primary_rows[-5:]:
            peer = other_by_ts.get(int(row["ts_open"]))
            if peer is None:
                continue
            compared += 1
            close_delta = float(row["close"]) - float(peer["close"])
            volume_delta = float(row["volume"]) - float(peer["volume"])
            volume_tolerance = max(100.0, abs(float(row["volume"])) * 0.001)
            if abs(close_delta) > 1e-8 or abs(volume_delta) > volume_tolerance:
                differences.append(
                    {
                        "ts_open": int(row["ts_open"]),
                        "primary_close": row["close"],
                        "other_close": peer["close"],
                        "close_delta": close_delta,
                        "primary_volume": row["volume"],
                        "other_volume": peer["volume"],
                        "volume_delta": volume_delta,
                        "volume_tolerance": volume_tolerance,
                    }
                )
        return {
            "provider": other,
            "status": "different" if differences else "ok",
            "primary_provider": primary,
            "compared_bars": compared,
            "differences": differences,
            "action": "仅记录，不修改主快照；复权序列不得混用",
        }
