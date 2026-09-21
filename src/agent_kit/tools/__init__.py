"""Tool registry — build the enabled tool set from configuration.

Adding a tool means writing one :class:`~agent_kit.tools.base.Tool` subclass and
registering it here; ``.agent/config.yaml`` then decides whether it is enabled.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from agent_kit.config.loader import ToolSection
from agent_kit.tools.base import Tool, ToolError, ToolResult
from agent_kit.tools.filesystem import FilesystemTool
from agent_kit.tools.shell import DEFAULT_ALLOWED_COMMANDS, ShellTool

TOOL_REGISTRY: dict[str, type[Tool]] = {
    FilesystemTool.name: FilesystemTool,
    ShellTool.name: ShellTool,
}


def available_tools() -> list[str]:
    return sorted(TOOL_REGISTRY)


def create_tool(name: str, project_root: Path | str, **options: object) -> Tool:
    """Instantiate a single tool by configuration name."""
    tool_class = TOOL_REGISTRY.get(name)
    if tool_class is None:
        raise ToolError(
            f"Unknown tool '{name}'. Available tools: {', '.join(available_tools())}."
        )
    return tool_class(root=project_root, **options)


def create_enabled_tools(
    tools: Mapping[str, ToolSection],
    project_root: Path | str,
) -> list[Tool]:
    """Instantiate every tool whose configuration entry has ``enabled: true``."""
    enabled: list[Tool] = []
    for name, section in tools.items():
        if not section.enabled:
            continue
        enabled.append(create_tool(name, project_root, **section.options))
    return enabled


__all__ = [
    "DEFAULT_ALLOWED_COMMANDS",
    "TOOL_REGISTRY",
    "FilesystemTool",
    "ShellTool",
    "Tool",
    "ToolError",
    "ToolResult",
    "available_tools",
    "create_enabled_tools",
    "create_tool",
]
