"""Mutable execution state for a single agent run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_kit.model.base import Message


@dataclass
class ToolInvocation:
    """Record of one executed tool call (for tracing and tests)."""

    tool: str
    arguments: dict[str, Any]
    success: bool
    output: str

    def summary(self) -> str:
        status = "ok" if self.success else "failed"
        return f"{self.tool}({', '.join(self.arguments)}) -> {status}"


@dataclass
class AgentState:
    """Everything that happens during one :meth:`Agent.run`."""

    messages: list[Message] = field(default_factory=list)
    iterations: int = 0
    tool_invocations: list[ToolInvocation] = field(default_factory=list)
    finished: bool = False
    final_output: str | None = None

    def add(self, message: Message) -> None:
        self.messages.append(message)

    def record_tool(self, invocation: ToolInvocation) -> None:
        self.tool_invocations.append(invocation)

    @property
    def tool_call_count(self) -> int:
        return len(self.tool_invocations)
