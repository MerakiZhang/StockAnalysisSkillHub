from __future__ import annotations

import argparse
import dataclasses
import json
import math
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from ashare_price_action.analysis.decision_nodes import check_preflight_data
from ashare_price_action.analysis.decision_tree import build_stage2_gate_wait_response
from ashare_price_action.analysis.json_validator import JsonValidator, Ok, ValidationError
from ashare_price_action.analysis.prompt_assembler import PromptAssembler
from ashare_price_action.analysis.retry_feedback import build_retry_feedback, parse_previous_for_cheat
from ashare_price_action.analysis.retry_policy import detect_cheat, extract_feedback_targets, should_retry
from ashare_price_action.analysis.router import route_strategy_files
from ashare_price_action.config.paths import PROMPT_DIR, records_pending_dir, resolve_output_dir
from ashare_price_action.config.settings import PromptSettings, ValidationSettings
from ashare_price_action.data.akshare_source import AkShareSource
from ashare_price_action.data.base import IndicatorBundle, KlineBar, KlineFrame
from ashare_price_action.data.snapshot import build_analysis_frame
from ashare_price_action.data.datetime_ts import format_epoch_for_display
from ashare_price_action.agent.workflow import append_assistant_turn
from ashare_price_action.records.analysis_history import (
    compute_incremental_bar_delta,
    find_latest_successful_record,
)
from ashare_price_action.records.experience_reader import ExperienceReader
from ashare_price_action.records.pending_writer import PendingWriter
from ashare_price_action.records.schema import AnalysisRecord, RecordMeta
from ashare_price_action.util.timefmt import now_local_ms
from ashare_price_action.util.trade_metrics import compute_risk_reward


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _state_path(run_dir: Path) -> Path:
    return run_dir / "run.json"


def _load_state(run_dir: Path) -> dict[str, Any]:
    return _read_json(_state_path(run_dir))


def _save_state(run_dir: Path, state: dict[str, Any]) -> None:
    _write_json(_state_path(run_dir), state)


def _frame_to_dict(frame: KlineFrame) -> dict[str, Any]:
    def clean(value: float) -> float | None:
        return None if math.isnan(value) else value

    return {
        "symbol": frame.symbol,
        "timeframe": frame.timeframe,
        "snapshot_ts_local_ms": frame.snapshot_ts_local_ms,
        "bars": [dataclasses.asdict(bar) for bar in frame.bars],
        "indicators": {
            "ema20": [clean(value) for value in frame.indicators.ema20],
            "atr14": [clean(value) for value in frame.indicators.atr14],
        },
    }


def _frame_from_dict(data: dict[str, Any]) -> KlineFrame:
    return KlineFrame(
        symbol=data["symbol"],
        timeframe=data["timeframe"],
        snapshot_ts_local_ms=int(data["snapshot_ts_local_ms"]),
        bars=tuple(KlineBar(**bar) for bar in data["bars"]),
        indicators=IndicatorBundle(
            ema20=tuple(math.nan if value is None else float(value) for value in data["indicators"]["ema20"]),
            atr14=tuple(math.nan if value is None else float(value) for value in data["indicators"]["atr14"]),
        ),
    )


def _load_frame(run_dir: Path) -> KlineFrame:
    return _frame_from_dict(_read_json(run_dir / "frame.json"))


def _load_previous(run_dir: Path, state: dict[str, Any]) -> AnalysisRecord | None:
    filename = state.get("previous_record_file")
    if not filename:
        return None
    path = run_dir / filename
    if not path.exists():
        return None
    return AnalysisRecord.model_validate(_read_json(path))


def _prompt_text(messages: list[dict[str, Any]]) -> str:
    labels = {"system": "SYSTEM", "user": "USER", "assistant": "ASSISTANT"}
    parts: list[str] = []
    for index, message in enumerate(messages, 1):
        role = str(message.get("role", "unknown"))
        parts.append(f"# MESSAGE {index} — {labels.get(role, role.upper())}\n\n{message.get('content', '')}")
    return "\n\n" + ("\n\n" + "=" * 80 + "\n\n").join(parts) if parts else ""


def _write_stage_prompt(run_dir: Path, stage: str, messages: list[dict[str, Any]]) -> None:
    _write_json(run_dir / f"{stage}_messages.json", messages)
    _write_text(run_dir / f"{stage}_prompt.md", _prompt_text(messages))
    system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
    user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    _write_text(run_dir / f"{stage}_system.md", system)
    _write_text(run_dir / f"{stage}_user.md", user)


def _assembler(state: dict[str, Any]) -> PromptAssembler:
    prompt_settings = PromptSettings(
        stage2_load_full_strategy_library=bool(state.get("load_full_strategy_library", False)),
        experience_max_entries=int(state.get("experience_max_entries", 0)),
        experience_max_chars_per_entry=int(state.get("experience_max_chars_per_entry", 400)),
        stage1_inject_pattern_briefs=True,
    )
    experience_dir = (
        Path(state["experience_dir"])
        if state.get("experience_dir")
        else Path(state.get("output_dir") or resolve_output_dir()) / "experience"
    )
    return PromptAssembler(
        PROMPT_DIR,
        experience_reader=ExperienceReader(experience_dir),
        prompt_settings=prompt_settings,
    )


def _validator(state: dict[str, Any]) -> JsonValidator:
    settings = ValidationSettings(
        normalization_mode=state.get("normalization_mode", "lenient"),
        stage1_coherence_checks=bool(state.get("stage1_coherence_checks", False)),
        stage2_coherence_checks=bool(state.get("stage2_coherence_checks", False)),
        trace_semantic_checks=bool(state.get("trace_semantic_checks", False)),
        strict_bar_by_bar_features=bool(state.get("strict_bar_by_bar_features", False)),
        retry_enabled=bool(state.get("retry_enabled", True)),
        retry_max=int(state.get("retry_max", 3)),
        retry_max_semantic=int(state.get("retry_max_semantic", 1)),
        retry_stage2=bool(state.get("retry_stage2", True)),
    )
    return JsonValidator(settings)


def _validation_settings(state: dict[str, Any]) -> ValidationSettings:
    return _validator(state)._validation


def _record_meta(state: dict[str, Any]) -> RecordMeta:
    return RecordMeta(
        timestamp_local_iso=state["timestamp_local_iso"],
        timestamp_local_ms=int(state["timestamp_local_ms"]),
        symbol=state["symbol"],
        timeframe=state["timeframe"],
        bar_count=int(state["bars"]),
        ai_provider={
            "model": state.get("agent_name", "host-agent"),
            "interface": state.get("agent_interface", "host-files"),
        },
        decision_stance=state["decision_stance"],
    )


def _base_record(run_dir: Path, state: dict[str, Any]) -> AnalysisRecord:
    frame = _load_frame(run_dir)
    return AnalysisRecord(
        meta=_record_meta(state),
        kline_data=[dataclasses.asdict(bar) for bar in frame.bars],
        htf_text="",
        stage1_messages=[],
        stage1_response=None,
        stage1_diagnosis=None,
        stage2_messages=[],
        stage2_response=None,
        stage2_decision=None,
        strategy_files_used=[],
        experience_loaded=[],
        exception=None,
        usage_total={},
    )


def _save_failure(run_dir: Path, state: dict[str, Any], stage: str, error: ValidationError) -> None:
    record = _base_record(run_dir, state)
    update: dict[str, Any] = {
        "exception": {
            "type": "validation_error",
            "stage": stage,
            "category": error.category,
            "message": error.message,
            "missing_fields": error.missing_fields,
            "invalid_fields": error.invalid_fields,
            "raw_text": error.raw_text,
            "parse_position": error.parse_position,
        }
    }
    for name in ("stage1", "stage2"):
        messages_file = run_dir / f"{name}_messages.json"
        response_file = run_dir / f"{name}_response.json"
        diagnosis_file = run_dir / f"{name}_diagnosis.json"
        decision_file = run_dir / f"{name}_decision.json"
        if messages_file.exists():
            update[f"{name}_messages"] = _read_json(messages_file)
        if response_file.exists():
            update[f"{name}_response"] = _read_json(response_file)
        if name == "stage1" and diagnosis_file.exists():
            update["stage1_diagnosis"] = _read_json(diagnosis_file)
        if name == "stage2" and decision_file.exists():
            update["stage2_decision"] = _read_json(decision_file)
    record = record.model_copy(update=update)
    path = PendingWriter(records_pending_dir(state.get("output_dir"))).save_partial(record, f"{stage}_{error.category}")
    state.update(status="failed", record_path=str(path), failure=record.exception)
    _save_state(run_dir, state)


def _model_reply(raw_text: str) -> SimpleNamespace:
    return SimpleNamespace(content=raw_text, reasoning_content="")


def _raw_response(raw_text: str, attempt: int, reply: Any | None = None) -> dict[str, Any]:
    return {
        "content": raw_text,
        "reasoning_content": str(getattr(reply, "reasoning_content", "") or ""),
        "request_id": str(getattr(reply, "request_id", "") or f"agent-attempt-{attempt}"),
        "usage": dict(getattr(reply, "usage", {}) or {}),
    }


def _retry_or_fail(
    run_dir: Path,
    state: dict[str, Any],
    stage: str,
    error: ValidationError,
    messages: list[dict[str, Any]],
    raw_text: str,
    frame: KlineFrame,
) -> None:
    settings = _validation_settings(state)
    retry_state = state[f"{stage}_retry"]
    attempt = int(retry_state["retry_attempt"])
    if not should_retry(
        error.category,
        error.invalid_fields,
        error.missing_fields,
        attempt=attempt,
        settings=settings,
    ):
        _save_failure(run_dir, state, stage, error)
        print(json.dumps({"status": "failed", "category": error.category, "message": error.message,
                          "missing_fields": error.missing_fields, "invalid_fields": error.invalid_fields}, ensure_ascii=False))
        return
    retry_state["retry_attempt"] = attempt + 1
    retry_state["previous_raw"] = raw_text
    retry_state["previous_obj"] = parse_previous_for_cheat(raw_text)
    retry_state["previous_feedback_targets"] = sorted(
        extract_feedback_targets(error.invalid_fields, error.missing_fields)
    )
    max_attempts = int(settings.retry_max)
    feedback = build_retry_feedback(
        error,
        stage=stage,
        attempt=attempt + 1,
        max_attempts=max_attempts,
        frame=frame,
        previous_raw=raw_text,
    )
    assistant_content = raw_text if raw_text.strip() else "(本轮未输出正文，程序已请求重试)"
    messages = messages + [
        {"role": "assistant", "content": assistant_content},
        {"role": "user", "content": feedback},
    ]
    retry_state["messages"] = messages
    state["status"] = f"awaiting_{stage}_retry"
    _save_state(run_dir, state)
    _write_stage_prompt(run_dir, stage, messages)
    print(json.dumps({
        "status": state["status"],
        "retry": attempt + 1,
        "max_retries": max_attempts,
        "prompt": str(run_dir / f"{stage}_prompt.md"),
        "raw_output_target": str(run_dir / f"{stage}_raw.json"),
        "message": error.message,
        "missing_fields": error.missing_fields,
        "invalid_fields": error.invalid_fields,
    }, ensure_ascii=False))


def _retry_cheat(
    state: dict[str, Any],
    stage: str,
    result: Ok,
    raw_text: str,
    validate_kwargs: dict[str, Any],
) -> list[str]:
    retry_state = state[f"{stage}_retry"]
    if int(retry_state["retry_attempt"]) <= 0 or retry_state.get("previous_obj") is None:
        return []
    before_norm = _validator(state).normalize_parsed(
        stage,
        retry_state["previous_obj"],
        **validate_kwargs,
    )
    return detect_cheat(
        stage,
        before_norm,
        result.obj,
        before_raw=retry_state["previous_obj"],
        after_raw=parse_previous_for_cheat(raw_text),
        feedback_mentioned=set(retry_state.get("previous_feedback_targets") or []),
    )


def _experience(state: dict[str, Any], diagnosis: dict[str, Any]) -> list[Any]:
    maximum = int(state.get("experience_max_entries", 0))
    if maximum <= 0:
        return []
    reader = ExperienceReader(
        Path(state["experience_dir"])
        if state.get("experience_dir")
        else Path(state.get("output_dir") or resolve_output_dir()) / "experience"
    )
    return reader.read_for_stage2(
        str(diagnosis.get("cycle_position", "unknown")),
        direction=str(diagnosis.get("direction", "") or ""),
        patterns=diagnosis.get("detected_patterns") or [],
        max_entries=maximum,
        max_chars_per_entry=int(state.get("experience_max_chars_per_entry", 400)),
    )


def _prepare_stage2(run_dir: Path, state: dict[str, Any], raw_text: str) -> None:
    frame = _load_frame(run_dir)
    diagnosis = _read_json(run_dir / "stage1_diagnosis.json")
    messages_s1 = _read_json(run_dir / "stage1_messages.json")
    strategy_files = route_strategy_files(diagnosis)
    experience = _experience(state, diagnosis)
    state["strategy_files_used"] = strategy_files
    state["experience_loaded"] = [
        entry.model_dump() if hasattr(entry, "model_dump") else dict(entry) for entry in experience
    ]
    if str(diagnosis.get("gate_result", "proceed")).lower() in ("wait", "unknown"):
        decision = build_stage2_gate_wait_response(diagnosis)
        _write_json(run_dir / "stage2_decision.json", decision)
        _write_json(run_dir / "stage2_messages.json", [])
        state["stage2_response"] = None
        _finalize(run_dir, state)
        return
    previous = _load_previous(run_dir, state)
    messages = _assembler(state).build_stage2_continuation(
        frame=frame,
        stage1_messages=messages_s1,
        stage1_reply_content=raw_text,
        stage1_json=diagnosis,
        strategy_files=strategy_files,
        experience_entries=experience,
        decision_stance=state["decision_stance"],
        previous_record=previous,
        enable_next_bar_prediction=bool(state.get("enable_next_bar_prediction", False)),
        use_prefix_chain=True,
        structure_flip_cooldown_bars=int(state.get("structure_flip_cooldown_bars", 3)),
    )
    state["stage2_retry"] = {
        "retry_attempt": 0,
        "messages": messages,
        "previous_raw": None,
        "previous_obj": None,
        "previous_feedback_targets": [],
    }
    state["status"] = "awaiting_stage2"
    _save_state(run_dir, state)
    _write_stage_prompt(run_dir, "stage2", messages)
    print(json.dumps({
        "status": state["status"],
        "prompt": str(run_dir / "stage2_prompt.md"),
        "raw_output_target": str(run_dir / "stage2_raw.json"),
        "strategy_files": strategy_files,
        "experience_entries": len(experience),
    }, ensure_ascii=False))


def _render_summary(record: AnalysisRecord, state: dict[str, Any]) -> str:
    diagnosis = record.stage1_diagnosis or {}
    output = record.stage2_decision or {}
    decision = output.get("decision") or {}
    lines = [
        f"# {record.meta.symbol} {record.meta.timeframe} PA 两阶段分析",
        "",
        f"- 分析模式：{state.get('effective_mode', 'full')}",
        f"- K 线：{record.meta.bar_count} 根已收盘，K1={format_epoch_for_display(record.kline_data[0]['ts_open']) if record.kline_data else 'N/A'}",
        f"- 数据来源：{state.get('source_meta', {}).get('provider', 'unknown')}（{state.get('source_meta', {}).get('adjust', 'qfq')}）",
        f"- 交易倾向：{record.meta.decision_stance}",
        "",
        "## 市场概览",
        "",
        f"- 周期位置：{diagnosis.get('cycle_position')}",
        f"- 备选周期：{diagnosis.get('alternative_cycle_position')}",
        f"- 方向：{diagnosis.get('direction')}",
        f"- 市场阶段：{diagnosis.get('market_phase')} / {diagnosis.get('transition_risk')}",
        f"- 诊断置信度：{diagnosis.get('diagnosis_confidence')}",
        f"- 形态：{', '.join(diagnosis.get('detected_patterns') or []) or '无'}",
        f"- 关键信号：{'；'.join(diagnosis.get('key_signals') or []) or '无'}",
        f"- 风险提示：{diagnosis.get('risk_warning') or '无'}",
        "",
        "## 交易决策",
        "",
        f"- 类型：{decision.get('order_type')}",
        f"- 方向：{decision.get('order_direction')}",
        f"- 入场：{decision.get('entry_price')}",
        f"- 止损：{decision.get('stop_loss_price')}",
        f"- TP1：{decision.get('take_profit_price')}",
        f"- TP2：{decision.get('take_profit_price_2')}",
        f"- 交易置信度：{decision.get('trade_confidence')}",
        f"- 预估胜率：{decision.get('estimated_win_rate')}",
        f"- 理由：{decision.get('reasoning')}",
        f"- 风险评估：{decision.get('risk_assessment')}",
        f"- 失效条件：{decision.get('invalidation_condition')}",
        f"- 观察点：{'；'.join(decision.get('watch_points') or []) or '无'}",
    ]
    rr = compute_risk_reward(
        decision.get("entry_price"),
        decision.get("take_profit_price"),
        decision.get("stop_loss_price"),
        decision.get("order_direction"),
    )
    if rr:
        lines.append(f"- 盈亏比：{rr['ratio_text']}（风险 {rr['risk']:.6g} / 回报 {rr['reward']:.6g}）")
    lines.extend([
        f"- 终局：{(output.get('terminal') or {}).get('outcome')} / {(output.get('terminal') or {}).get('node_id')}",
        "",
        "## 下一市场周期预测",
        "",
        f"- {json.dumps(output.get('next_cycle_prediction'), ensure_ascii=False)}",
        "",
        "## 决策路径",
        "",
        "### 阶段一闸门",
    ])
    for node in diagnosis.get("gate_trace") or []:
        lines.append(
            f"- {node.get('node_id')} [{node.get('bar_range')}] {node.get('answer')}"
            f" {node.get('branch') or ''}：{node.get('reason')}"
        )
    lines.append("### 阶段二决策")
    for node in output.get("decision_trace") or []:
        lines.append(
            f"- {node.get('node_id')} [{node.get('bar_range')}] {node.get('answer')}"
            f" {node.get('branch') or ''}：{node.get('reason')}"
        )
    lines.extend(["", "本结果仅供学习研究，不构成投资建议，不会自动下单。", ""])
    return "\n".join(lines)


def _finalize(run_dir: Path, state: dict[str, Any]) -> None:
    record = _base_record(run_dir, state)
    stage1_messages = _read_json(run_dir / "stage1_messages.json")
    stage1_response = _read_json(run_dir / "stage1_response.json")
    diagnosis = _read_json(run_dir / "stage1_diagnosis.json")
    stage2_messages = _read_json(run_dir / "stage2_messages.json") if (run_dir / "stage2_messages.json").exists() else []
    stage2_response = _read_json(run_dir / "stage2_response.json") if (run_dir / "stage2_response.json").exists() else None
    decision = _read_json(run_dir / "stage2_decision.json")
    if not state.get("enable_next_bar_prediction", False) and not decision.get("gate_shortcircuited"):
        decision.pop("next_bar_prediction", None)
        _write_json(run_dir / "stage2_decision.json", decision)
    record = record.model_copy(update={
        "stage1_messages": stage1_messages,
        "stage1_response": stage1_response,
        "stage1_diagnosis": diagnosis,
        "stage2_messages": stage2_messages,
        "stage2_response": stage2_response,
        "stage2_decision": decision,
        "strategy_files_used": state.get("strategy_files_used", []),
        "experience_loaded": state.get("experience_loaded", []),
        "exception": None,
    })
    path = PendingWriter(records_pending_dir(state.get("output_dir"))).save_full(record)
    if not path.is_file():
        raise OSError(f"分析记录未能落盘：{path}")
    summary = _render_summary(record, state)
    _write_text(run_dir / "summary.md", summary)
    state.update(status="completed", record_path=str(path), summary_path=str(run_dir / "summary.md"))
    _save_state(run_dir, state)
    print(json.dumps({"status": "completed", "record": str(path), "summary": str(run_dir / "summary.md")}, ensure_ascii=False))


def command_prepare(args: argparse.Namespace) -> Path:
    timestamp_ms = now_local_ms()
    timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
    output_dir = resolve_output_dir(getattr(args, "output_dir", None))
    run_name = f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_{args.symbol}_{args.timeframe}"
    run_dir = Path(args.run_dir).resolve() if args.run_dir else output_dir / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    source = AkShareSource(primary=args.primary, crosscheck=not args.no_crosscheck)
    source.connect()
    try:
        source.subscribe(args.symbol, args.timeframe)
        raw_bars = source.latest_snapshot(args.bars + 51)
    finally:
        source.disconnect()
    frame = build_analysis_frame(raw_bars, args.bars, args.symbol, args.timeframe)
    if frame is None:
        raise ValueError(f"无法取得 {args.bars} 根已收盘 K 线及指标预热数据")
    preflight = check_preflight_data(frame)
    if not preflight.ok:
        raise ValueError(preflight.reason)
    state: dict[str, Any] = {
        "schema_version": 1,
        "status": "preparing",
        "output_dir": str(output_dir),
        "agent_name": getattr(args, "agent_name", "host-agent"),
        "agent_interface": getattr(args, "agent_interface", "host-files"),
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "bars": args.bars,
        "timestamp_local_ms": timestamp_ms,
        "timestamp_local_iso": timestamp.isoformat(timespec="milliseconds"),
        "decision_stance": args.decision_stance,
        "enable_next_bar_prediction": args.enable_next_bar,
        "structure_flip_cooldown_bars": args.structure_flip_cooldown_bars,
        "experience_max_entries": args.experience_max_entries,
        "experience_max_chars_per_entry": args.experience_max_chars_per_entry,
        "experience_dir": args.experience_dir,
        "load_full_strategy_library": args.load_full_strategy_library,
        "normalization_mode": args.normalization_mode,
        "stage1_coherence_checks": args.stage1_coherence_checks,
        "stage2_coherence_checks": args.stage2_coherence_checks,
        "trace_semantic_checks": args.trace_semantic_checks,
        "strict_bar_by_bar_features": args.strict_bar_by_bar_features,
        "retry_enabled": not args.no_retry,
        "retry_max": args.retry_max,
        "retry_max_semantic": args.retry_max_semantic,
        "retry_stage2": not args.no_stage2_retry,
        "requested_mode": args.mode,
        "effective_mode": "full",
        "incremental_new_bar_count": None,
        "source_meta": source.last_fetch_meta,
        "strategy_files_used": [],
        "experience_loaded": [],
    }
    previous = None
    delta = None
    if args.mode != "full":
        previous = find_latest_successful_record(
            symbol=args.symbol,
            timeframe=args.timeframe,
            directory=records_pending_dir(output_dir),
        )
        if previous is not None:
            delta = compute_incremental_bar_delta(frame, previous)
            if delta is not None and (args.mode == "incremental" or delta.new_count <= args.incremental_threshold):
                state["effective_mode"] = "incremental"
                state["incremental_new_bar_count"] = delta.new_count
                state["incremental_anchor_ts_open"] = delta.anchor_ts_open
                state["incremental_new_bar_ts_opens"] = list(delta.new_bar_ts_opens)
            else:
                state["incremental_fallback_reason"] = (
                    "未找到上一轮 K1 锚点" if delta is None else f"新增 {delta.new_count} 根超过阈值 {args.incremental_threshold}"
                )
        else:
            state["incremental_fallback_reason"] = "没有上一轮成功记录"
    if previous is not None:
        _write_json(run_dir / "previous_record.json", previous.model_dump())
        state["previous_record_file"] = "previous_record.json"
    _write_json(run_dir / "frame.json", _frame_to_dict(frame))
    _write_json(run_dir / "source.json", source.last_fetch_meta)
    if state["effective_mode"] == "incremental" and previous is not None:
        messages = _assembler(state).build_incremental_stage1(
            frame,
            previous,
            int(state["incremental_new_bar_count"]),
            analysis_mode="original",
            )
    else:
        messages = _assembler(state).build_stage1(frame, analysis_mode="original")
    state["stage1_retry"] = {
        "retry_attempt": 0,
        "messages": messages,
        "previous_raw": None,
        "previous_obj": None,
        "previous_feedback_targets": [],
    }
    state["status"] = "awaiting_stage1"
    _save_state(run_dir, state)
    _write_stage_prompt(run_dir, "stage1", messages)
    print(json.dumps({
        "status": state["status"],
        "run_dir": str(run_dir),
        "output_dir": str(output_dir),
        "mode": state["effective_mode"],
        "incremental_new_bar_count": state["incremental_new_bar_count"],
        "incremental_fallback_reason": state.get("incremental_fallback_reason"),
        "source": source.last_fetch_meta,
        "prompt": str(run_dir / "stage1_prompt.md"),
        "raw_output_target": str(run_dir / "stage1_raw.json"),
    }, ensure_ascii=False))
    return run_dir


def _validate_stage(run_dir: Path, stage: str, *, reply: Any | None = None) -> None:
    state = _load_state(run_dir)
    raw_path = run_dir / f"{stage}_raw.json"
    if not raw_path.exists():
        raise FileNotFoundError(f"请先由模型写入 {raw_path}，内容只能是该阶段裸 JSON")
    raw_text = str(reply.content) if reply is not None else raw_path.read_text(encoding="utf-8")
    retry_state = state[f"{stage}_retry"]
    messages = retry_state["messages"]
    response_count = int(retry_state.get("response_count", 0)) + 1
    retry_state["response_count"] = response_count
    _write_text(run_dir / f"{stage}_raw_attempt_{response_count}.json", raw_text)
    _write_json(run_dir / f"{stage}_response.json", _raw_response(raw_text, response_count, reply))
    frame = _load_frame(run_dir)
    validator = _validator(state)
    if stage == "stage1":
        kwargs: dict[str, Any] = {
            "kline_frame": frame,
            "incremental_new_bar_count": int(state.get("incremental_new_bar_count") or 0),
            "incremental_previous_stage1": (
                _load_previous(run_dir, state).stage1_diagnosis
                if int(state.get("incremental_new_bar_count") or 0) > 0 and _load_previous(run_dir, state)
                else None
            ),
        }
    else:
        kwargs = {
            "kline_frame": frame,
            "decision_stance": state["decision_stance"],
            "stage1_json": _read_json(run_dir / "stage1_diagnosis.json"),
            "skip_next_bar": not state.get("enable_next_bar_prediction", False),
            "previous_record": _load_previous(run_dir, state),
            "structure_flip_cooldown_bars": int(state.get("structure_flip_cooldown_bars", 3)),
        }
    result = validator.validate(stage, raw_text, **kwargs)
    if isinstance(result, ValidationError):
        _save_state(run_dir, state)
        _retry_or_fail(run_dir, state, stage, result, messages, raw_text, frame)
        return
    cheats = _retry_cheat(state, stage, result, raw_text, kwargs)
    if cheats:
        error = ValidationError(
            category="c",
            stage=stage,
            raw_text=raw_text,
            message="重试后篡改了不可变字段: " + "; ".join(cheats),
            invalid_fields=[f"cheat:{item}" for item in cheats],
        )
        _save_failure(run_dir, state, stage, error)
        print(json.dumps({"status": "failed", "cheats": cheats}, ensure_ascii=False))
        return
    messages = append_assistant_turn(messages, _model_reply(raw_text))
    retry_state["messages"] = messages
    _write_stage_prompt(run_dir, stage, messages)
    if stage == "stage1":
        _write_json(run_dir / "stage1_diagnosis.json", result.obj)
        state["status"] = "stage1_validated"
        _save_state(run_dir, state)
        _prepare_stage2(run_dir, state, raw_text)
    else:
        _write_json(run_dir / "stage2_decision.json", result.obj)
        state["status"] = "stage2_validated"
        _save_state(run_dir, state)
        _finalize(run_dir, state)


def command_show(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir).resolve()
    state = _load_state(run_dir)
    if (run_dir / "summary.md").exists():
        print((run_dir / "summary.md").read_text(encoding="utf-8"))
    else:
        print(json.dumps(state, ensure_ascii=False, indent=2))


