from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_ROOT))

from ashare_price_action.workflow import _validate_stage, command_prepare, command_show


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Two-stage price-action stock analysis")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--symbol", required=True)
    prepare.add_argument("--timeframe", choices=("1h", "4h", "1d"), default="1d")
    prepare.add_argument("--bars", type=int, default=100)
    prepare.add_argument("--mode", choices=("auto", "full", "incremental"), default="auto")
    prepare.add_argument("--incremental-threshold", type=int, default=10)
    prepare.add_argument("--primary", choices=("sina", "tencent"), default="sina")
    prepare.add_argument("--no-crosscheck", action="store_true")
    prepare.add_argument("--run-dir")
    prepare.add_argument("--output-dir")
    prepare.add_argument("--agent-name", default="host-agent")
    prepare.add_argument("--decision-stance", choices=("conservative", "balanced", "aggressive", "extreme_aggressive"), default="balanced")
    prepare.add_argument("--enable-next-bar", action="store_true")
    prepare.add_argument("--structure-flip-cooldown-bars", type=int, default=3)
    prepare.add_argument("--experience-dir")
    prepare.add_argument("--experience-max-entries", type=int, default=0)
    prepare.add_argument("--experience-max-chars-per-entry", type=int, default=400)
    prepare.add_argument("--load-full-strategy-library", action="store_true")
    prepare.add_argument("--normalization-mode", choices=("strict", "lenient"), default="lenient")
    prepare.add_argument("--stage1-coherence-checks", action="store_true")
    prepare.add_argument("--stage2-coherence-checks", action="store_true")
    prepare.add_argument("--trace-semantic-checks", action="store_true")
    prepare.add_argument("--strict-bar-by-bar-features", action="store_true")
    prepare.add_argument("--no-retry", action="store_true")
    prepare.add_argument("--retry-max", type=int, default=3)
    prepare.add_argument("--retry-max-semantic", type=int, default=1)
    prepare.add_argument("--no-stage2-retry", action="store_true")
    prepare.set_defaults(func=command_prepare)
    for stage in ("stage1", "stage2"):
        validate = sub.add_parser(f"validate-{stage}")
        validate.add_argument("--run-dir", required=True)
        validate.set_defaults(func=lambda args, stage=stage: _validate_stage(Path(args.run_dir).resolve(), stage))
    show = sub.add_parser("show")
    show.add_argument("--run-dir", required=True)
    show.set_defaults(func=command_show)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(json.dumps({
            "status": "failed",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }, ensure_ascii=False))
        return 1
    if args.command.startswith("validate-"):
        state = json.loads((Path(args.run_dir).resolve() / "run.json").read_text(encoding="utf-8"))
        if state.get("status") == "failed":
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
