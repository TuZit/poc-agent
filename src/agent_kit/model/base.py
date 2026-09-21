"""Provider-agnostic model abstractions.

Only concrete implementations (e.g. :class:`~agent_kit.model.openai.OpenAIModel`)
may import a provider SDK. :class:`~agent_kit.agent.agent.Agent` depends on
this module alone, which is what keeps the runtime vendor-neutral.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


class ModelError(Exception):
    """Raised for model configuration or invocation failures."""


@dataclass(frozen=True)
class ToolCall:
    """A model request to invoke one tool."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Message:
    """One chat message.

    ``tool_calls`` is only set on assistant messages, ``tool_call_id`` only on
    tool-result messages.
    """

    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None

    @classmethod
    def system(cls, content: str) -> Message:
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str) -> Message:
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: str | None, tool_calls: list[ToolCall] | None = None) -> Message:
        return cls(role="assistant", content=content, tool_calls=list(tool_calls or []))

    @classmethod
    def tool_result(cls, tool_call_id: str, name: str, content: str) -> Message:
        return cls(role="tool", content=content, tool_call_id=tool_call_id, name=name)


@dataclass(frozen=True)
class ToolSpec:
    """JSON-schema description of a tool, as handed to the model."""

    name: str
    description: str
    parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass(frozen=True)
class ModelResponse:
    """A single model turn: final text and/or tool calls."""

    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def wants_tool_call(self) -> bool:
        return bool(self.tool_calls)


class Model(ABC):
    """Minimal chat-model interface.

    Implementations must be constructible from ``name`` plus keyword options so
    that :func:`agent_kit.model.create_model` can build them from configuration.
    """

    #: Provider key used in ``model.provider``.
    provider: str = "abstract"

    #: Environment variables this provider needs. ``doctor`` reports these.
    required_env_vars: tuple[str, ...] = ()

    def __init__(self, name: str, **options: Any) -> None:
        self.name = name
        self.options = options

    @abstractmethod
    def generate(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> ModelResponse:
        """Generate the next assistant turn for ``messages``."""

    def describe(self) -> str:
        """Short human-readable description used by ``doctor`` and ``run``."""
        return f"{self.provider}/{self.name}"
