"""Unit tests for the specialist agents and the orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_kit.agent.runtime import AgentRuntime
from agent_kit.config import load_config
from agent_kit.evaluation import find_missing_sections
from agent_kit.model.base import ModelResponse
from agent_kit.model.mock import (
    MOCK_CODE_REVIEW,
    MOCK_REQUIREMENT_SUMMARY,
    MOCK_UNIT_TEST_PLAN,
    MockModel,
)
from agent_kit.workflow import (
    ORCHESTRATION_SECTIONS,
    WorkflowError,
    available_specialists,
    get_specialist,
    specialist_workflows,
)

CONFIG = """\
model:
  provider: mock
  name: mock-model
tools:
  filesystem:
    enabled: true
skills:
  - requirement-analysis
  - code-review
  - unit-test-generation
workflow:
  name: requirement-analysis
orchestrator:
  strategy: auto
  planner: rules
  agents:
    - requirement-analysis
    - code-review
    - unit-test-generation
  default_agents:
    - requirement-analysis
"""

MIXED_REQUEST = (
    "Review the checkout diff before we merge, and generate the unit tests we are "
    "missing. The project uses pytest."
)
REQUIREMENT_REQUEST = "Draft the requirement for the new checkout feature."
UNKNOWN_REQUEST = "Tell me a joke about penguins."


def _project(tmp_path: Path, config: str = CONFIG) -> Path:
    project = tmp_path / "project"
    (project / ".agent").mkdir(parents=True, exist_ok=True)
    (project / ".agent" / "config.yaml").write_text(config, encoding="utf-8")
    return project


# --- specialist registry --------------------------------------------------
def test_specialists_exclude_the_orchestrator() -> None:
    assert available_specialists() == [
        "code-review",
        "requirement-analysis",
        "unit-test-generation",
    ]
    assert all(not workflow.is_orchestrator for workflow in specialist_workflows())


def test_every_specialist_declares_the_metadata_the_cli_needs() -> None:
    for workflow in specialist_workflows():
        assert workflow.title
        assert workflow.description
        assert workflow.default_skill
        assert workflow.required_sections
        assert workflow.default_input
        assert not workflow.is_orchestrator


def test_get_specialist_rejects_the_orchestrator_and_unknown_names() -> None:
    with pytest.raises(WorkflowError, match="Unknown agent 'orchestration'"):
        get_specialist("orchestration")
    with pytest.raises(WorkflowError, match="Unknown agent"):
        get_specialist("does-not-exist")


def test_shipped_sample_inputs_exist_and_do_not_collide() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    stems = []
    for workflow in specialist_workflows():
        assert workflow.default_input is not None
        sample = repo_root / workflow.default_input
        assert sample.is_file(), f"missing sample for {workflow.name}: {sample}"
        stems.append(sample.stem)
    # Distinct stems keep `output/<stem>.md` from colliding between agents.
    assert len(stems) == len(set(stems))


# --- specialist runs ------------------------------------------------------
def test_code_review_agent_produces_a_valid_report(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    result = runtime.run_workflow(
        "Review this diff:\n\n+++ b/app.py\n", workflow_name="code-review"
    )

    assert result.valid is True
    assert result.issues == []
    assert result.output.strip() == MOCK_CODE_REVIEW.strip()
    assert find_missing_sections(result.output, result.required_sections) == []


def test_unit_test_agent_produces_a_valid_plan(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    result = runtime.run_workflow(
        "Write unit tests for the pricing module.",
        workflow_name="unit-test-generation",
    )

    assert result.valid is True
    assert result.output.strip() == MOCK_UNIT_TEST_PLAN.strip()


def test_specialist_loads_its_own_skill_not_the_configured_one(tmp_path: Path) -> None:
    """config.skills lists requirement-analysis first, yet code-review wins."""
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    runtime.run_workflow("review this", workflow_name="code-review")

    system_message = runtime.model.calls[0][0]  # type: ignore[attr-defined]
    assert "# Loaded skill: code-review" in system_message.content


def test_specialist_fails_validation_when_the_model_output_is_incomplete(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))
    runtime.model = MockModel(script=[ModelResponse(content="# Code Review\n\nnothing else")])

    result = runtime.run_workflow("review this", workflow_name="code-review")

    assert result.valid is False
    assert any("Summary" in issue for issue in result.issues)


# --- orchestrator ---------------------------------------------------------
def test_orchestrator_selects_two_agents_for_a_mixed_request(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    result = runtime.run_workflow(MIXED_REQUEST, workflow_name="orchestration")

    assert result.valid is True
    assert result.metadata["strategy"] == "auto"
    assert set(result.metadata["selected_agents"]) == {"code-review", "unit-test-generation"}
    assert "# Agent Orchestration Report" in result.output
    assert "## Request Analysis" in result.output
    assert "## Agent: Code Review" in result.output
    assert "## Agent: Unit Test Generation" in result.output
    assert "## Summary" in result.output
    assert find_missing_sections(result.output, ORCHESTRATION_SECTIONS) == []


def test_orchestrator_uses_the_router_for_a_single_intent(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    result = runtime.run_workflow(REQUIREMENT_REQUEST, workflow_name="orchestration")

    assert result.metadata["selected_agents"] == ["requirement-analysis"]
    assert MOCK_REQUIREMENT_SUMMARY.strip() in result.output


def test_orchestrator_falls_back_to_default_agents(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    result = runtime.run_workflow(UNKNOWN_REQUEST, workflow_name="orchestration")

    assert result.metadata["selected_agents"] == ["requirement-analysis"]
    assert "no signal matched" in result.output


def test_orchestrator_all_strategy_runs_every_agent(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    result = runtime.run_workflow(
        UNKNOWN_REQUEST, workflow_name="orchestration", options={"strategy": "all"}
    )

    assert set(result.metadata["selected_agents"]) == {
        "requirement-analysis",
        "code-review",
        "unit-test-generation",
    }
    for title in ("Requirement Analysis", "Code Review", "Unit Test Generation"):
        assert f"## Agent: {title}" in result.output


def test_orchestrator_honours_explicit_agents(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    result = runtime.run_workflow(
        REQUIREMENT_REQUEST,
        workflow_name="orchestration",
        options={"agents": "code-review"},
    )

    assert result.metadata["selected_agents"] == ["code-review"]
    assert result.metadata["strategy"] == "explicit"
    assert "## Agent: Unit Test Generation" not in result.output


def test_orchestrator_rejects_an_unknown_agent(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    with pytest.raises(WorkflowError, match="Unknown agent"):
        runtime.run_workflow(
            REQUIREMENT_REQUEST,
            workflow_name="orchestration",
            options={"agents": "does-not-exist"},
        )


def test_orchestrator_rejects_an_unknown_strategy(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    with pytest.raises(WorkflowError, match="Unknown orchestrator strategy"):
        runtime.run_workflow(
            REQUIREMENT_REQUEST,
            workflow_name="orchestration",
            options={"strategy": "llm"},
        )


def test_orchestrator_reports_an_invalid_sub_agent(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))
    runtime.model = MockModel(script=[ModelResponse(content="# Broken\n\nno sections")])

    result = runtime.run_workflow(MIXED_REQUEST, workflow_name="orchestration")

    assert result.valid is False
    assert any(issue.startswith("code-review:") for issue in result.issues)


def test_orchestrator_lists_agent_statuses_in_the_summary(tmp_path: Path) -> None:
    runtime = AgentRuntime(load_config(_project(tmp_path)))

    result = runtime.run_workflow(MIXED_REQUEST, workflow_name="orchestration")

    assert "- code-review: PASS" in result.output
    assert "- unit-test-generation: PASS" in result.output


def test_orchestrator_errors_when_no_agent_is_enabled(tmp_path: Path) -> None:
    config = CONFIG.replace(
        "  agents:\n    - requirement-analysis\n    - code-review\n    - unit-test-generation\n",
        "  agents: []\n",
    )
    runtime = AgentRuntime(load_config(_project(tmp_path, config)))

    with pytest.raises(WorkflowError, match="No specialist agents are enabled"):
        runtime.run_workflow(REQUIREMENT_REQUEST, workflow_name="orchestration")


def test_runtime_rejects_an_agent_outside_the_allow_list(tmp_path: Path) -> None:
    config = CONFIG.replace(
        "  agents:\n    - requirement-analysis\n    - code-review\n    - unit-test-generation\n",
        "  agents:\n    - requirement-analysis\n",
    )
    runtime = AgentRuntime(load_config(_project(tmp_path, config)))

    with pytest.raises(WorkflowError, match="not enabled for orchestration"):
        runtime.run_specialist("code-review", REQUIREMENT_REQUEST)


def test_runtime_rejects_unknown_agent_names_from_config(tmp_path: Path) -> None:
    config = CONFIG.replace(
        "  agents:\n    - requirement-analysis\n    - code-review\n    - unit-test-generation\n",
        "  agents:\n    - requirement-analysis\n    - typo-agent\n",
    )
    runtime = AgentRuntime(load_config(_project(tmp_path, config)))

    with pytest.raises(WorkflowError, match="Unknown agent"):
        runtime.specialist_workflows()
