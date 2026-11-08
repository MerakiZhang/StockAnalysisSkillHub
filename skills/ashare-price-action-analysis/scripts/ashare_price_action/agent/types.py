from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Protocol

StageName = Literal["stage1", "stage2"]


@dataclass(frozen=True)
class AgentRequest:
    stage: StageName
    run_dir: Path
    messages: list[dict[str, Any]]


@dataclass(frozen=True)
class AgentReply:
    content: str
    reasoning_content: str = ""
    request_id: str = ""
    usage: dict[str, Any] = field(default_factory=dict)


class AgentExecutor(Protocol):
    name: str
    interface: str

    def complete(self, request: AgentRequest) -> AgentReply:
        ...


@dataclass(frozen=True)
class CallbackAgentExecutor:
    callback: Callable[[AgentRequest], AgentReply | str]
    name: str = "callback-agent"
    interface: str = "python-callback"

    def complete(self, request: AgentRequest) -> AgentReply:
        result = self.callback(request)
        if isinstance(result, str):
            return AgentReply(content=result)
        if not isinstance(result, AgentReply):
            raise TypeError("Agent callback must return AgentReply or str")
        return result
