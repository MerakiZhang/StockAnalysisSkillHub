from __future__ import annotations

from typing import Any


def append_assistant_turn(
    messages: list[dict[str, Any]],
    reply: Any,
) -> list[dict[str, Any]]:
    content = getattr(reply, "content", None) or ""
    if not content.strip():
        return messages
    if messages and messages[-1].get("role") == "assistant":
        if (messages[-1].get("content") or "").strip() == content.strip():
            return messages
    return messages + [{"role": "assistant", "content": content}]
