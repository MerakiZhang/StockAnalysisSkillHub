from __future__ import annotations

import os
from pathlib import Path

SKILL_ROOT: Path = Path(__file__).resolve().parents[3]
PROMPT_DIR: Path = SKILL_ROOT / "references" / "prompts"
DEFAULT_OUTPUT_DIRNAME = "ashare-price-action-data"


def resolve_output_dir(value: str | Path | None = None) -> Path:
    configured = value or os.environ.get("ASHARE_PRICE_ACTION_OUTPUT_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.cwd() / DEFAULT_OUTPUT_DIRNAME).resolve()


def records_pending_dir(output_dir: str | Path | None = None) -> Path:
    return resolve_output_dir(output_dir) / "records" / "pending"
