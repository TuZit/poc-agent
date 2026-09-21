"""Tool abstraction shared by every built-in tool.

Security model for the POC: a tool is *restricted by construction*. It
receives the project root when it is created and refuses to act outside its
declared boundary. Expected misuse (bad action, non-whitelisted command,
missing argument) is reported as ``ToolResult(success=False, ...)`` so the
agent can recover; a boundary violation raises :class:`ToolError`, which the
agent turns into a failed tool result as well.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from agent_kit.model.base import ToolSpec


class ToolError(Exception):
    """Raised when a tool boundary is violated (e.g. a path escape)."""


@dataclass(frozen=True)
class ToolResult:
    """Outcome of one tool invocation."""

    success: bool
    output: str

    def __bool__(self) -> bool:  # pragma: no cover - convenience only
        return self.success


class Tool(ABC):
    """Base class for all tools."""

    #: Name the model uses when calling the tool.
    name: str = "tool"
    #: Description shown to the model.
    description: str = ""
    #: JSON schema of the arguments.
    parameters: ClassVar[dict[str, Any]] = {}

    def __init__(self, root: Path | str, **options: Any) -> None:
        #: Hard boundary: every tool is anchored to the project directory.
        self.root = Path(root).resolve()
        self.options = options

    def spec(self) -> ToolSpec:
        """Tool description handed to the model."""
        return ToolSpec(name=self.name, description=self.description, parameters=self.parameters)

    def describe(self) -> str:
        return f"{self.name}: {self.description}"

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute one invocation. Arguments are model-supplied and untrusted."""
