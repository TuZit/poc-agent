"""Unit tests for workflows and the runtime that assembles them."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_kit.agent.runtime import AgentRuntime
from agent_kit.config import load_config
from agent_kit.evaluation import REQUIRED_SECTIONS, find_missing_sections
from agent_kit.model.base import ModelResponse, ToolCall
from agent_kit.model.mock import MOCK_REQUIREMENT_SUMMARY, MockModel
from agent_kit.workflow import (
    WORKFLOW_REGISTRY,
    WorkflowError,
    available_workflows,
    create_workflow,
)

REQUIREMENT = "Build an e-commerce product management API with REST and authentication."

CONFIG_WITH_SKILL = """\
model:
  provider: mock
  name: mock-model
tools:
  filesystem:
    enabled: true
skills:
  - requirement-analysis
workflow:
  name: requirement-analysis
"""

CONFIG_WITHOUT_SKILL = """\
model:
  provider: mock
  name: mock-model
workflow:
  name: requirement-analysis
"""


def _project(tmp_path: Path, config: str = CONFIG_WITH_SKILL) -> Path:
    project = tmp_path / "project"
    (project / ".agent").mkdir(parents=True, exist_ok=True)
    (project / ".agent" / "config.yaml").write_text(config, encoding="utf-8")
    return project


def test_workflow_registry_contains_requirement_analysis() -> None:
    assert "requirement-analysis" in WORKFLOW_REGISTRY
    assert available_workflows() == ["requirement-analysis"]
    assert create_workflow("requirement-analysis").name == "requirement-analysis"


def test_unknown_workflow_raises() -> None:
    with pytest.raises(WorkflowError, match="Unknown workflow"):
        create_workflow("code-review")


def test_requirement_analysis_workflow_produces_valid_output(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    result = runtime.run_workflow(REQUIREMENT)

    assert result.workflow == "requirement-analysis"
    assert result.valid is True
    assert result.issues == []
    assert find_missing_sections(result.output, REQUIRED_SECTIONS) == []
    assert result.output.strip() == MOCK_REQUIREMENT_SUMMARY.strip()
    assert "Create product" in result.output


def test_workflow_reports_missing_sections(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))
    runtime.model = MockModel(script=[ModelResponse(content="# Requirement Summary\n\nnothing")])

    result = runtime.run_workflow(REQUIREMENT)

    assert result.valid is False
    assert any("Objective" in issue for issue in result.issues)


def test_runtime_uses_workflow_default_skill_when_none_configured(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path, CONFIG_WITHOUT_SKILL)))

    result = runtime.run_workflow(REQUIREMENT)

    assert result.valid is True
    system_message = runtime.model.calls[0][0]  # type: ignore[attr-defined]
    assert "Loaded skill: requirement-analysis" in system_message.content


def test_runtime_exposes_model_tools_and_skills(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    assert runtime.model.describe() == "mock/mock-model"
    assert [tool.name for tool in runtime.tools] == ["filesystem"]
    assert runtime.load_configured_skills()[0].name == "requirement-analysis"
    assert "model=mock/mock-model" in runtime.describe()


def test_workflow_records_tool_usage(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))
    runtime.model = MockModel(
        script=[
            ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="filesystem",
                        arguments={
                            "action": "write_file",
                            "path": "output/summary.md",
                            "content": "# Requirement Summary\n",
                        },
                    )
                ],
            ),
            ModelResponse(content=MOCK_REQUIREMENT_SUMMARY),
        ]
    )

    result = runtime.run_workflow(REQUIREMENT)

    assert result.tool_call_count == 1
    assert result.tool_invocations[0].tool == "filesystem"
    assert (tmp_path / "project" / "output" / "summary.md").is_file()
    assert result.valid is True


def test_skill_override_argument_is_honoured(tmp_path: Path) -> None:
    custom = tmp_path / "project" / ".agent" / "skills" / "custom"
    custom.mkdir(parents=True)
    (custom / "SKILL.md").write_text("# Custom\n\nCustom instructions.", encoding="utf-8")
    runtime = AgentRuntime(load_config(_project(tmp_path, CONFIG_WITHOUT_SKILL)))

    runtime.run_workflow(REQUIREMENT, skill_name="custom")

    system_message = runtime.model.calls[0][0]  # type: ignore[attr-defined]
    assert "Custom instructions." in system_message.content
