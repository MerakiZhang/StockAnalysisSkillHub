from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from ashare_price_action.agent.types import AgentExecutor, AgentReply, AgentRequest

_DEFAULT_OPTIONS: dict[str, Any] = {
    "timeframe": "1d",
    "bars": 100,
    "mode": "auto",
    "incremental_threshold": 10,
    "primary": "sina",
    "no_crosscheck": False,
    "run_dir": None,
    "output_dir": None,
    "decision_stance": "balanced",
    "enable_next_bar": False,
    "structure_flip_cooldown_bars": 3,
    "experience_dir": None,
    "experience_max_entries": 0,
    "experience_max_chars_per_entry": 400,
    "load_full_strategy_library": False,
    "normalization_mode": "lenient",
    "stage1_coherence_checks": False,
    "stage2_coherence_checks": False,
    "trace_semantic_checks": False,
    "strict_bar_by_bar_features": False,
    "no_retry": False,
    "retry_max": 3,
    "retry_max_semantic": 1,
    "no_stage2_retry": False,
}


def run_analysis(
    *,
    symbol: str,
    executor: AgentExecutor,
    **options: Any,
) -> Path:
    unknown = set(options) - set(_DEFAULT_OPTIONS)
    if unknown:
        raise TypeError(f"Unknown analysis options: {', '.join(sorted(unknown))}")

    from ashare_price_action.workflow import (
        _load_state,
        _validate_stage,
        _write_text,
        command_prepare,
    )

    config = {**_DEFAULT_OPTIONS, **options}
    config["symbol"] = symbol
    config["agent_name"] = executor.name
    config["agent_interface"] = executor.interface
    run_dir = command_prepare(SimpleNamespace(**config))

    while True:
        state = _load_state(run_dir)
        status = str(state["status"])
        if status == "completed":
            return run_dir
        if status.startswith("awaiting_stage1"):
            stage = "stage1"
        elif status.startswith("awaiting_stage2"):
            stage = "stage2"
        else:
            raise RuntimeError(f"Analysis stopped with status {status}: {state.get('failure')}")

        retry_state = state[f"{stage}_retry"]
        request = AgentRequest(
            stage=stage,
            run_dir=run_dir,
            messages=retry_state["messages"],
        )
        reply = executor.complete(request)
        if not isinstance(reply, AgentReply):
            raise TypeError("AgentExecutor.complete must return AgentReply")
        _write_text(run_dir / f"{stage}_raw.json", reply.content)
        _validate_stage(run_dir, stage, reply=reply)
