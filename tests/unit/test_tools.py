"""Unit tests for the restricted tools — the security boundary is the point."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_kit.config import ToolSection
from agent_kit.tools import (
    DEFAULT_ALLOWED_COMMANDS,
    FilesystemTool,
    ShellTool,
    ToolError,
    available_tools,
    create_enabled_tools,
    create_tool,
)


# --- registry -------------------------------------------------------------
def test_registry_lists_builtin_tools() -> None:
    assert available_tools() == ["filesystem", "shell"]


def test_unknown_tool_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ToolError, match="Unknown tool"):
        create_tool("nope", tmp_path)


def test_create_enabled_tools_skips_disabled(tmp_path: Path) -> None:
    tools = create_enabled_tools(
        {
            "filesystem": ToolSection(enabled=True),
            "shell": ToolSection(enabled=False),
        },
        tmp_path,
    )
    assert [tool.name for tool in tools] == ["filesystem"]


def test_tool_specs_expose_json_schema(tmp_path: Path) -> None:
    spec = FilesystemTool(tmp_path).spec()
    assert spec.name == "filesystem"
    assert spec.parameters["required"] == ["action", "path"]
    assert spec.parameters["properties"]["action"]["enum"] == ["read_file", "write_file"]


# --- filesystem -----------------------------------------------------------
def test_filesystem_write_then_read(tmp_path: Path) -> None:
    tool = FilesystemTool(tmp_path)

    write_result = tool.execute(action="write_file", path="notes/a.md", content="hello")
    read_result = tool.execute(action="read_file", path="notes/a.md")

    assert write_result.success is True
    assert read_result.success is True
    assert read_result.output == "hello"
    assert (tmp_path / "notes" / "a.md").read_text(encoding="utf-8") == "hello"


def test_filesystem_blocks_parent_traversal(tmp_path: Path) -> None:
    tool = FilesystemTool(tmp_path / "project")
    tool.root.mkdir()

    with pytest.raises(ToolError, match="Access denied"):
        tool.execute(action="write_file", path="../../escape.md", content="nope")


def test_filesystem_blocks_absolute_path_outside_root(tmp_path: Path) -> None:
    tool = FilesystemTool(tmp_path / "project")
    tool.root.mkdir()

    with pytest.raises(ToolError, match="Access denied"):
        tool.execute(action="read_file", path=str(tmp_path / "outside.txt"))


def test_filesystem_allows_absolute_path_inside_root(tmp_path: Path) -> None:
    tool = FilesystemTool(tmp_path)
    inside = tmp_path / "inside.txt"
    inside.write_text("ok", encoding="utf-8")

    assert tool.execute(action="read_file", path=str(inside)).output == "ok"


def test_filesystem_read_missing_file_fails_cleanly(tmp_path: Path) -> None:
    result = FilesystemTool(tmp_path).execute(action="read_file", path="missing.md")
    assert result.success is False
    assert "not found" in result.output.lower()


def test_filesystem_write_requires_content(tmp_path: Path) -> None:
    result = FilesystemTool(tmp_path).execute(action="write_file", path="a.md")
    assert result.success is False
    assert "content" in result.output


def test_filesystem_rejects_unknown_action(tmp_path: Path) -> None:
    result = FilesystemTool(tmp_path).execute(action="delete_file", path="a.md")
    assert result.success is False
    assert "Unknown action" in result.output


def test_filesystem_rejects_project_root_as_target(tmp_path: Path) -> None:
    result = FilesystemTool(tmp_path).execute(action="write_file", path=".", content="x")
    assert result.success is False


# --- shell ----------------------------------------------------------------
def test_shell_whitelist_is_exactly_the_documented_set() -> None:
    assert DEFAULT_ALLOWED_COMMANDS == ("python", "pytest", "git")


def test_shell_rejects_non_whitelisted_command(tmp_path: Path) -> None:
    result = ShellTool(tmp_path).execute(command="bash", args=["-c", "echo hi"])
    assert result.success is False
    assert "not allowed" in result.output
    assert "python" in result.output  # the whitelist is echoed back


def test_shell_runs_whitelisted_command(tmp_path: Path) -> None:
    result = ShellTool(tmp_path).execute(command="python", args=["-c", "print('hello from tool')"])
    assert result.success is True
    assert "hello from tool" in result.output


def test_shell_runs_inside_project_root(tmp_path: Path) -> None:
    result = ShellTool(tmp_path).execute(
        command="python", args=["-c", "import os; print(os.getcwd())"]
    )
    assert result.success is True
    assert str(tmp_path.resolve()) in result.output


def test_shell_rejects_non_string_arguments(tmp_path: Path) -> None:
    result = ShellTool(tmp_path).execute(command="python", args=[1, 2])  # type: ignore[list-item]
    assert result.success is False
    assert "list of strings" in result.output


def test_shell_does_not_interpret_shell_operators(tmp_path: Path) -> None:
    """Arguments are passed as a list with shell=False, so metacharacters are inert."""
    result = ShellTool(tmp_path).execute(
        command="python",
        args=["-c", "import sys; print(sys.argv[1])", "&& echo pwned > owned.txt"],
    )
    assert result.success is True
    assert "&& echo pwned > owned.txt" in result.output  # passed through verbatim
    assert not (tmp_path / "owned.txt").exists()  # the redirect never ran


def test_shell_reports_failing_exit_code(tmp_path: Path) -> None:
    result = ShellTool(tmp_path).execute(command="python", args=["-c", "raise SystemExit(3)"])
    assert result.success is False
    assert "exit code 3" in result.output


def test_shell_spec_enum_matches_whitelist(tmp_path: Path) -> None:
    spec = ShellTool(tmp_path).spec()
    assert spec.parameters["properties"]["command"]["enum"] == list(DEFAULT_ALLOWED_COMMANDS)
