"""Stage-1 pattern tags, entry_setup overlays, and stage-1 briefs for routing."""
from __future__ import annotations

import re
from typing import Any

# H1/H2/L1/L2 count setup — avoid bare「计数」(e.g. EMA缺口计数) false positives.
_HL_COUNT_SETUP_RE = re.compile(
    r"(?<![a-z])(?:h[12]|l[12])(?![a-z])|计数入场|high\s*[12]|low\s*[12]",
    re.IGNORECASE,
)

# Maps bar_analysis.entry_setup_type -> detected_patterns keys to merge before routing.
ENTRY_SETUP_TYPE_PATTERN_OVERLAY: dict[str, tuple[str, ...]] = {
    "wedge": ("wedge",),
    "breakout_pullback": ("breakout_pullback",),
    "mtr": ("mtr", "reversal_attempt"),
    "h1": ("h1",),
    "h2": ("h2", "reversal_attempt"),
    "l1": ("l1",),
    "l2": ("l2", "reversal_attempt"),
    "tr_boundary": ("middle_range", "barbwire"),
}

# Keywords in key_signals / risk_warning → detected_patterns tag (sync + post-sync coherence).
_PATTERN_KEYWORD_TAGS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("楔形", "三推", "三推动", "wedge"), "wedge"),
    (("突破测试", "突破回踩", "失败的失败"), "breakout_test"),
    (("假突破", "突破失败", "failed breakout", "突破后快速收复"), "breakout_failure"),
    (("mtr", "主要趋势反转", "趋势反转尝试"), "mtr"),
    (("铁丝网", "barbwire", "凝滞区"), "barbwire"),
    (("重叠度高", "重叠多", "k线重叠", "重叠严重"), "overlap"),
    (("区间下沿", "区间上沿", "区间边界", "交易区间", "交易区间下沿", "交易区间上沿"), "middle_range"),
    (("h1", "h2", "l1", "l2", "计数入场", "high1", "high2", "low1", "low2"), "h1"),
    (("always in", "ail", "ais", "20gb", "缺口棒"), "always_in"),
    (("磁力", "套住", "trapped", "信号失败"), "failed_signal"),
    (("双顶", "双底", "双重顶", "双重底", "double top", "double bottom"), "double_top_bottom"),
    (("上升三角形",), "ascending_triangle"),
    (("下降三角形",), "descending_triangle"),
    (("对称三角形",), "symmetrical_triangle"),
    (("扩张三角形",), "expanding_triangle"),
    (("最终旗形", "final flag", "ffes"), "final_flag"),
)

_CYCLE_POSITION_PATTERN_TAGS: dict[str, tuple[str, ...]] = {
    "trading_range": ("middle_range", "barbwire", "overlap"),
    "trending_tr": ("middle_range", "overlap"),
}

_HL_PATTERN_KEYWORDS: dict[str, str] = {
    "h1": "h1",
    "h2": "h2",
    "l1": "l1",
    "l2": "l2",
}

STAGE1_DETECTED_PATTERNS_GUIDE = """
## detected_patterns 判定表（阶段一必填标签）

在 `detected_patterns` 中填写规定的英文 key，可多个并存。程序据此加载阶段二 Markdown 资源；形态不是周期状态，也不是独立下单理由。

| key | 何时填写 | 阶段二资源 |
|---|---|---|
| wedge | 三次同向推进，结合幅度递减和边界收敛；含回撤与反转候选 | patterns/wedge.md |
| reversal_attempt | 有反转证据但未必满足完整 MTR | patterns/second-entry.md |
| mtr | 趋势线突破、原趋势恢复失败、极点测试失败等组件齐全 | patterns/major-trend-reversal.md |
| final_flag | 趋势末端的水平整理或末端旗形 | patterns/final-flag.md |
| h1 / h2 / l1 / l2 | 有真实回撤腿和极点触发的计数结构 | patterns/high-low-counts.md |
| breakout_test / breakout_pullback | 突破回测或失败的失败 | patterns/breakout.md |
| breakout_failure / failed_breakout | 突破后快速回到原结构 | patterns/breakout.md、patterns/magnets.md |
| always_in / ail / ais / 20gb / gap_bar | Always In、均线游程和几何缺口标签 | patterns/always-in.md |
| barbwire / wire / overlap / middle_range | 铁丝网、重叠或区间中部 | patterns/barbwire.md |
| failed_signal / magnet / trapped_traders | 失败信号、可能回测位或被套结构 | patterns/magnets.md |
| ascending_triangle / descending_triangle / symmetrical_triangle / expanding_triangle | 四类三角形边界 | patterns/triangles.md |
| double_top_bottom | 双顶、双底或微型双顶底 | patterns/double-top-bottom.md |

阶段二常驻风险与目标资源为 stage2/risk-and-targets.md 和 stage2/measured-move.md。

`entry_setup_type` 与标签必须一致：wedge→wedge，breakout_pullback→breakout_pullback，MTR→mtr/reversal_attempt，H1/H2/L1/L2→对应小写标签。`tr_boundary` 的程序补全规则保持不变。无特殊形态时填 `[]`，不要只把形态藏在 `key_signals`。
""".strip()

STAGE1_PATTERN_BRIEFS_BLOCK = """
## 特殊形态阶段一速查

- **wedge**：识别三推、幅度和边界；形态方向不等于交易方向。
- **breakout_test / breakout_pullback**：突破后的回测或失败的失败，需有真实后续 K 线。
- **breakout_failure**：突破后快速回到原结构；无跟随但未收回时只能算未确认。
- **reversal_attempt / mtr**：反转候选与完整 MTR 分开；逆原趋势只诊断。
- **h1/h2/l1/l2**：按回撤腿和极点触发计数；二次结构不自动提高胜率。
- **barbwire / overlap / middle_range**：记录紧凑、重叠和中部风险，程序补全规则不变。
- **always_in / 20gb**：表示当前主方向或均线游程；逆势不能靠文字双确认放行。
- **failed_signal / magnet**：可能回测失败信号或入场价，不是必然吸引。
- **final_flag / double_top_bottom / 三角形**：均为叠加形态，不替代底层周期状态。
""".strip()


def _barbwire_blocked(stage1_json: dict[str, Any]) -> bool:
    """True when program_features explicitly forbids barbwire auto-tagging."""
    pf = stage1_json.get("program_features")
    if isinstance(pf, dict) and pf.get("barbwire_candidate") is False:
        return True
    return False


def _barbwire_candidate(stage1_json: dict[str, Any], kline_frame: Any = None) -> bool:
    if _barbwire_blocked(stage1_json):
        return False
    pf = stage1_json.get("program_features")
    if isinstance(pf, dict) and "barbwire_candidate" in pf:
        return bool(pf["barbwire_candidate"])
    if kline_frame is not None:
        try:
            from ashare_price_action.analysis.market_features import compute_simple_market_features

            return compute_simple_market_features(kline_frame).barbwire_candidate
        except Exception:
            pass
    return False


def _barbwire_keyword_negated(text: str) -> bool:
    """Skip keyword sync when narrative discusses sub-threshold barbwire score."""
    lowered = text.lower()
    if "未达阈值" in lowered and "铁丝网" in lowered:
        return True
    if re.search(r"铁丝网分数\s*0\.\d+", lowered) and "未达" in lowered:
        return True
    return False


def _should_sync_barbwire_tag(
    stage1_json: dict[str, Any],
    text: str,
    *,
    kline_frame: Any = None,
) -> bool:
    if _barbwire_blocked(stage1_json):
        return False
    if _barbwire_keyword_negated(text):
        return False
    return _barbwire_candidate(stage1_json, kline_frame)


def _collect_detected_pattern_tags(
    stage1_json: dict[str, Any],
    *,
    kline_frame: Any = None,
) -> list[str]:
    """Merge model tags + entry_setup_type + key_signals heuristics (stable order)."""
    raw = stage1_json.get("detected_patterns") or []
    patterns: list[str] = []
    seen: set[str] = set()
    for p in raw:
        key = str(p).strip().lower()
        if key and key not in seen:
            seen.add(key)
            patterns.append(key)

    est = _entry_setup_type(stage1_json)
    for key in ENTRY_SETUP_TYPE_PATTERN_OVERLAY.get(est, ()):
        if key == "barbwire" and not _barbwire_candidate(stage1_json, kline_frame):
            continue
        if key not in seen:
            seen.add(key)
            patterns.append(key)

    cp = str(stage1_json.get("cycle_position", "") or "").strip().lower()
    for key in _CYCLE_POSITION_PATTERN_TAGS.get(cp, ()):
        if key == "barbwire" and not _barbwire_candidate(stage1_json, kline_frame):
            continue
        if key not in seen:
            seen.add(key)
            patterns.append(key)

    blob = " ".join(str(s) for s in (stage1_json.get("key_signals") or [])).lower()
    risk = str(stage1_json.get("risk_warning") or "").lower()
    text = f"{blob} {risk}"
    for keywords, tag in _PATTERN_KEYWORD_TAGS:
        if tag == "h1":
            if _mentions_hl_count_setup(text):
                for hl in ("h1", "h2", "l1", "l2"):
                    if re.search(rf"(?<![a-z]){hl}(?![a-z])", text) and hl not in seen:
                        seen.add(hl)
                        patterns.append(hl)
            continue
        if tag == "barbwire":
            if not any(k.lower() in text for k in keywords):
                continue
            if not _should_sync_barbwire_tag(stage1_json, text, kline_frame=kline_frame):
                continue
        if any(k.lower() in text for k in keywords) and tag not in seen:
            seen.add(tag)
            patterns.append(tag)

    return patterns


def sync_detected_patterns_field(
    stage1_json: dict[str, Any],
    *,
    kline_frame: Any = None,
) -> list[str]:
    """Write merged tags back into stage1_json['detected_patterns'] (in-place)."""
    patterns = _collect_detected_pattern_tags(stage1_json, kline_frame=kline_frame)
    stage1_json["detected_patterns"] = patterns
    return patterns


def merge_detected_patterns(
    stage1_json: dict[str, Any],
    *,
    kline_frame: Any = None,
) -> list[str]:
    """Union of detected_patterns and entry_setup_type overlay (stable order)."""
    return _collect_detected_pattern_tags(stage1_json, kline_frame=kline_frame)


def _mentions_hl_count_setup(text: str) -> bool:
    """True when narrative explicitly refers to H1/H2/L1/L2 count entry (not EMA gap count)."""
    return bool(_HL_COUNT_SETUP_RE.search(text))


def _entry_setup_type(stage1_json: dict[str, Any]) -> str:
    bar = stage1_json.get("bar_analysis")
    if not isinstance(bar, dict):
        return ""
    return str(bar.get("entry_setup_type") or "").strip().lower()


_HL_WORD_RE = re.compile(r"(?i)(?:high|low)\s*([12])(?![0-9])")


def _hl_tags_from_text(text: str) -> list[str]:
    tags: list[str] = []
    for m in _HL_WORD_RE.finditer(text):
        prefix = "h" if m.group(0).lower().startswith("h") else "l"
        tags.append(f"{prefix}{m.group(1)}")
    for hl in ("h1", "h2", "l1", "l2"):
        if re.search(rf"(?<![a-z]){hl}(?![a-z])", text) and hl not in tags:
            tags.append(hl)
    return tags


def ensure_detected_patterns_coherent(
    stage1_json: dict[str, Any],
    *,
    kline_frame: Any = None,
) -> bool:
    """Auto-add detected_patterns tags implied by key_signals / entry_setup_type."""
    before = list(stage1_json.get("detected_patterns") or [])
    sync_detected_patterns_field(stage1_json, kline_frame=kline_frame)
    patterns: list[str] = list(stage1_json.get("detected_patterns") or [])
    seen = {str(p).strip().lower() for p in patterns}

    blob = " ".join(str(s) for s in (stage1_json.get("key_signals") or [])).lower()
    risk = str(stage1_json.get("risk_warning") or "").lower()
    text = f"{blob} {risk}"

    changed = patterns != before

    if _mentions_hl_count_setup(text) or _hl_tags_from_text(text):
        for hl in _hl_tags_from_text(text) or _HL_PATTERN_KEYWORDS:
            if hl not in seen:
                seen.add(hl)
                patterns.append(hl)
                changed = True

    for keywords, required in _PATTERN_KEYWORD_TAGS:
        if required == "h1":
            continue
        if required == "barbwire":
            if not any(k.lower() in text for k in keywords):
                continue
            if not _should_sync_barbwire_tag(stage1_json, text, kline_frame=kline_frame):
                continue
        if any(k.lower() in text for k in keywords) and required not in seen:
            seen.add(required)
            patterns.append(required)
            changed = True

    est = _entry_setup_type(stage1_json)
    if est == "wedge" and "wedge" not in seen:
        patterns.append("wedge")
        changed = True
    if est == "breakout_pullback" and "breakout_pullback" not in seen:
        patterns.append("breakout_pullback")
        changed = True
    if est == "tr_boundary":
        for required in ("middle_range", "barbwire"):
            if required == "barbwire" and not _barbwire_candidate(stage1_json, kline_frame):
                continue
            if required not in seen:
                seen.add(required)
                patterns.append(required)
                changed = True

    if changed:
        stage1_json["detected_patterns"] = patterns
    return changed


def validate_detected_patterns_vs_key_signals(
    stage1: dict[str, Any],
    *,
    kline_frame: Any = None,
) -> list[str]:
    """Warn when narrative mentions a pattern but detected_patterns omits the router key."""
    errors: list[str] = []
    patterns = {str(p).strip().lower() for p in (stage1.get("detected_patterns") or [])}
    blob = " ".join(str(s) for s in (stage1.get("key_signals") or [])).lower()
    risk = str(stage1.get("risk_warning") or "").lower()
    text = f"{blob} {risk}"

    for keywords, required in _PATTERN_KEYWORD_TAGS:
        if required == "h1":
            if _mentions_hl_count_setup(text):
                if not patterns.intersection(_HL_PATTERN_KEYWORDS.keys()):
                    errors.append(
                        "key_signals mentions H1/H2/L1/L2 count setup but "
                        "detected_patterns lacks h1/h2/l1/l2"
                    )
            continue
        if required == "barbwire":
            if not any(k.lower() in text for k in keywords):
                continue
            if not _should_sync_barbwire_tag(stage1, text, kline_frame=kline_frame):
                continue
        if any(k.lower() in text for k in keywords):
            if required not in patterns:
                errors.append(
                    f"key_signals/risk_warning mentions pattern related to {required!r} "
                    f"but detected_patterns lacks {required!r}"
                )

    est = _entry_setup_type(stage1)
    if est == "wedge" and "wedge" not in patterns:
        errors.append(
            "bar_analysis.entry_setup_type=wedge requires detected_patterns to include 'wedge'"
        )
    if est == "breakout_pullback" and "breakout_pullback" not in patterns:
        errors.append(
            "bar_analysis.entry_setup_type=breakout_pullback requires "
            "detected_patterns to include 'breakout_pullback'"
        )
    if est == "tr_boundary":
        for required in ("middle_range", "barbwire"):
            if required == "barbwire" and not _barbwire_candidate(stage1, kline_frame):
                continue
            if required not in patterns:
                errors.append(
                    f"bar_analysis.entry_setup_type=tr_boundary requires "
                    f"detected_patterns to include {required!r}"
                )

    return errors
