"""Map a validated Stage 1 diagnosis to Stage 2 Markdown resources."""
from __future__ import annotations

import logging
from typing import Any

from ashare_price_action.analysis.pattern_routing import merge_detected_patterns
from ashare_price_action.analysis.prompt_catalog import (
    ALL_PROMPT_FILES,
    ALWAYS_IN,
    BARBWIRE,
    BEAR_CHANNEL_FILES,
    BEAR_SPIKE_FILES,
    BREAKOUT,
    BULL_CHANNEL_FILES,
    BULL_SPIKE_FILES,
    CHANNEL_WIDTH,
    DOUBLE_TOP_BOTTOM,
    FINAL_FLAG,
    HIGH_LOW_COUNTS,
    MAGNETS,
    MAJOR_TREND_REVERSAL,
    RANGE_FILES,
    SECOND_ENTRY,
    TRIANGLES,
    WEDGE,
)

logger = logging.getLogger(__name__)

_ALL_VALID_FILES = ALL_PROMPT_FILES
_CHANNEL_STATES = frozenset({"micro_channel", "tight_channel", "normal_channel", "broad_channel"})
_RANGE_STATES = frozenset({"trading_range", "trending_tr"})
_SKIP_STATES = frozenset({"extreme_tr", "unknown"})


def route_strategy_files(stage1_json: dict[str, Any]) -> list[str]:
    """Return ordered, deduplicated Markdown resources for Stage 2."""
    cp = stage1_json.get("cycle_position", "unknown")
    direction = stage1_json.get("direction", "neutral")
    patterns = merge_detected_patterns(stage1_json)
    spike_stage = stage1_json.get("spike_stage")
    alternative_cp = stage1_json.get("alternative_cycle_position")

    files = list(_base_files_for_cycle(cp, direction, spike_stage=spike_stage))

    trend_context = stage1_json.get("trend_context") or {}
    recent_spike = trend_context.get("recent_spike") if isinstance(trend_context, dict) else None
    if recent_spike == "bullish" and cp != "spike" and direction == "bullish":
        files.extend(BULL_SPIKE_FILES)
    elif recent_spike == "bearish" and cp != "spike" and direction == "bearish":
        files.extend(BEAR_SPIKE_FILES)

    if alternative_cp and alternative_cp != cp:
        files.extend(_base_files_for_cycle(str(alternative_cp), direction, spike_stage=None))

    if "wedge" in patterns:
        files.append(WEDGE)
    if (
        cp in _CHANNEL_STATES
        or any(p in patterns for p in ("reversal_attempt", "mtr", "final_flag", "h2", "l2"))
    ):
        files.append(SECOND_ENTRY)
    if "mtr" in patterns:
        files.append(MAJOR_TREND_REVERSAL)
    if "final_flag" in patterns:
        files.append(FINAL_FLAG)
    if cp in _CHANNEL_STATES or any(p in patterns for p in ("h1", "h2", "l1", "l2")):
        files.append(HIGH_LOW_COUNTS)
    if any(p in patterns for p in ("breakout_failure", "failed_breakout", "breakout_test", "breakout_pullback")):
        files.append(BREAKOUT)
    if any(p in patterns for p in ("always_in", "ail", "ais", "20gb", "gap_bar")):
        files.append(ALWAYS_IN)
    if cp in _RANGE_STATES or any(p in patterns for p in ("barbwire", "wire", "overlap", "middle_range")):
        files.append(BARBWIRE)
    if any(p in patterns for p in ("failed_signal", "breakout_failure", "failed_breakout", "magnet", "trapped_traders")):
        files.append(MAGNETS)
    if any(p in patterns for p in ("ascending_triangle", "descending_triangle", "symmetrical_triangle", "expanding_triangle")):
        files.append(TRIANGLES)
    if "double_top_bottom" in patterns:
        files.append(DOUBLE_TOP_BOTTOM)

    return list(dict.fromkeys(files))


def _base_files_for_cycle(
    cp: str,
    direction: str,
    *,
    spike_stage: Any = None,
) -> list[str]:
    """Return base resources before pattern overlays."""
    if cp == "spike" and spike_stage == "transitioning":
        return _channel_files(direction)

    if cp in _CHANNEL_STATES:
        files = _channel_files(direction)
        if cp == "micro_channel" and spike_stage in ("active", "ending"):
            if direction == "bullish":
                files.extend(BULL_SPIKE_FILES)
            elif direction == "bearish":
                files.extend(BEAR_SPIKE_FILES)
        return files

    if cp == "spike":
        if direction == "bullish":
            files = list(BULL_SPIKE_FILES)
        elif direction == "bearish":
            files = list(BEAR_SPIKE_FILES)
        else:
            logger.info("Spike with neutral direction: no directional spike resource loaded")
            files = []
        if spike_stage == "ending":
            files.extend(_channel_files(direction))
        return files

    if cp in _RANGE_STATES:
        return list(RANGE_FILES)

    if cp in _SKIP_STATES:
        return []

    logger.warning(
        "Unknown cycle_position %r; no strategy resources loaded. "
        "Run normalize_stage1() before routing.",
        cp,
    )
    return []


def _channel_files(direction: str) -> list[str]:
    if direction == "bullish":
        files = list(BULL_CHANNEL_FILES)
    elif direction == "bearish":
        files = list(BEAR_CHANNEL_FILES)
    else:
        logger.info("Channel-like state with neutral direction: load range resource")
        files = list(RANGE_FILES)
    files.append(CHANNEL_WIDTH)
    return files
