"""Unit tests for the agent loop (model ↔ tool iteration)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_kit.agent import Agent, AgentError
from agent_kit.model.base import ModelResponse, ToolCall
from agent_kit.model.mock import MockModel
from agent_kit.skills.base import Skill
from agent_kit.tools.filesystem import FilesystemTool
from agent_kit.tools.shell import ShellTool


def _write_call(path: str = "out.md", content: str = "hello") -> ToolCall:
    return ToolCall(
        id="call_1",
        name="filesystem",
        arguments={"action": "write_file", "path": path, "content": content},
    )


def test_agent_returns_final_answer_without_tools(tmp_path: Path) -> None:
    agent = Agent(model=MockModel(), tools=[])

    result = agent.run("analyze this")

    assert result.output.startswith("# Requirement Summary")
    assert result.iterations == 1
    assert result.tool_invocations == []
    assert result.state.finished is True


def test_agent_executes_tool_then_finishes(tmp_path: Path) -> None:
    model = MockModel(
        script=[
            ModelResponse(content=None, tool_calls=[_write_call()]),
            ModelResponse(content="# Done\n\nfile written"),
        ]
    )
    agent = Agent(model=model, tools=[FilesystemTool(tmp_path)])

    result = agent.run("write the file")

    assert result.output == "# Done\n\nfile written"
    assert result.iterations == 2
    assert result.tool_call_count == 1
    assert result.tool_invocations[0].success is True
    assert (tmp_path / "out.md").read_text(encoding="utf-8") == "hello"
    # the tool result was fed back to the model as a tool message
    assert model.calls[1][-1].role == "tool"
    assert model.calls[1][-1].content == "Wrote 5 characters to out.md."


def test_agent_reports_unknown_tool_to_the_model(tmp_path: Path) -> None:
    model = MockModel(
        script=[
            ModelResponse(content=None, tool_calls=[ToolCall(id="1", name="nope", arguments={})]),
            ModelResponse(content="recovered"),
        ]
    )
    agent = Agent(model=model, tools=[FilesystemTool(tmp_path)])

    result = agent.run("do something")

    assert result.output == "recovered"
    assert result.tool_invocations[0].success is False
    assert "Unknown tool" in result.tool_invocations[0].output


def test_agent_converts_boundary_violation_into_failed_result(tmp_path: Path) -> None:
    outside = _write_call(path="../../escape.md")
    model = MockModel(
        script=[
            ModelResponse(content=None, tool_calls=[outside]),
            ModelResponse(content="gave up on that path"),
        ]
    )
    agent = Agent(model=model, tools=[FilesystemTool(tmp_path / "project")])
    (tmp_path / "project").mkdir()

    result = agent.run("escape the sandbox")

    assert result.tool_invocations[0].success is False
    assert "Access denied" in result.tool_invocations[0].output
    assert not (tmp_path / "escape.md").exists()


def test_agent_stops_at_max_iterations(tmp_path: Path) -> None:
    model = MockModel(script=[ModelResponse(content=None, tool_calls=[_write_call()])])
    agent = Agent(model=model, tools=[FilesystemTool(tmp_path)], max_iterations=3)

    with pytest.raises(AgentError, match="within 3 iterations"):
        agent.run("loop forever")


def test_system_message_contains_skill_instructions_and_tools(tmp_path: Path) -> None:
    skill = Skill(name="demo", instructions="# Demo skill\n\nDo the demo.", path=tmp_path)
    agent = Agent(
        model=MockModel(),
        tools=[FilesystemTool(tmp_path), ShellTool(tmp_path)],
        system_prompt="Base prompt.",
    )

    message = agent.build_system_message(skill)

    assert message.role == "system"
    assert "Base prompt." in message.content
    assert "Do the demo." in message.content
    assert "filesystem" in message.content and "shell" in message.content


def test_tool_specs_are_passed_to_the_model(tmp_path: Path) -> None:
    agent = Agent(model=MockModel(), tools=[FilesystemTool(tmp_path)])
    specs = agent.tool_specs()
    assert [spec.name for spec in specs] == ["filesystem"]
    assert specs[0].parameters["type"] == "object"


def test_agent_state_records_full_transcript(tmp_path: Path) -> None:
    model = MockModel(
        script=[
            ModelResponse(content=None, tool_calls=[_write_call()]),
            ModelResponse(content="final"),
        ]
    )
    result = Agent(model=model, tools=[FilesystemTool(tmp_path)]).run("input")

    roles = [message.role for message in result.state.messages]
    assert roles == ["system", "user", "assistant", "tool", "assistant"]
    assert result.state.final_output == "final"
