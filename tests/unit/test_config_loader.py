"""Unit tests for the configuration loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_kit.config import (
    ConfigError,
    default_config_path,
    dump_config,
    load_config,
)

VALID = """\
agent:
  name: unit-agent

model:
  provider: mock
  name: mock-model

tools:
  filesystem:
    enabled: true
  shell:
    enabled: false

skills:
  - requirement-analysis

workflow:
  name: requirement-analysis
"""


def _write(project: Path, text: str) -> Path:
    config_dir = project / ".agent"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_default_config_path_points_at_agent_dir(tmp_path: Path) -> None:
    assert default_config_path(tmp_path) == tmp_path / ".agent" / "config.yaml"


def test_load_config_reads_every_section(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID)

    config = load_config(tmp_path)

    assert config.agent.name == "unit-agent"
    assert config.model.provider == "mock"
    assert config.model.name == "mock-model"
    assert config.skills == ["requirement-analysis"]
    assert config.workflow.name == "requirement-analysis"
    assert config.project_root == tmp_path.resolve()
    assert config.config_path == path
    assert config.enabled_tool_names() == ["filesystem"]


def test_missing_config_has_actionable_message(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_config(tmp_path)
    assert "agent-kit init" in str(excinfo.value)


def test_invalid_yaml_is_reported(tmp_path: Path) -> None:
    _write(tmp_path, "model: [unclosed\n")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(tmp_path)


def test_empty_file_is_reported(tmp_path: Path) -> None:
    _write(tmp_path, "")
    with pytest.raises(ConfigError, match="empty"):
        load_config(tmp_path)


def test_top_level_must_be_mapping(tmp_path: Path) -> None:
    _write(tmp_path, "- just\n- a list\n")
    with pytest.raises(ConfigError, match="mapping"):
        load_config(tmp_path)


def test_model_provider_is_required(tmp_path: Path) -> None:
    _write(tmp_path, "model:\n  name: gpt-4o-mini\nworkflow:\n  name: requirement-analysis\n")
    with pytest.raises(ConfigError, match=r"model.provider is required"):
        load_config(tmp_path)


def test_model_name_is_required(tmp_path: Path) -> None:
    _write(tmp_path, "model:\n  provider: openai\nworkflow:\n  name: requirement-analysis\n")
    with pytest.raises(ConfigError, match=r"model.name is required"):
        load_config(tmp_path)


def test_workflow_name_is_required(tmp_path: Path) -> None:
    _write(tmp_path, "model:\n  provider: mock\n  name: mock-model\n")
    with pytest.raises(ConfigError, match=r"workflow.name is required"):
        load_config(tmp_path)


def test_skills_must_be_a_list_of_strings(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "model:\n  provider: mock\n  name: mock-model\n"
        "workflow:\n  name: requirement-analysis\nskills: requirement-analysis\n",
    )
    with pytest.raises(ConfigError, match="skills must be a list"):
        load_config(tmp_path)


def test_provider_options_are_passed_through(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "model:\n  provider: openai\n  name: gpt-4o-mini\n  base_url: http://localhost:1234/v1\n"
        "  options:\n    temperature: 0.2\n"
        "workflow:\n  name: requirement-analysis\n",
    )
    config = load_config(tmp_path)
    assert config.model.options == {"base_url": "http://localhost:1234/v1", "temperature": 0.2}


def test_tool_options_and_enabled_flag(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "model:\n  provider: mock\n  name: mock-model\n"
        "workflow:\n  name: requirement-analysis\n"
        "tools:\n  shell:\n    enabled: true\n    timeout: 5\n",
    )
    config = load_config(tmp_path)
    assert config.tools["shell"].enabled is True
    assert config.tools["shell"].options == {"timeout": 5}
    assert config.enabled_tool_names() == ["shell"]


def test_provider_is_normalised_to_lowercase(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "model:\n  provider: OpenAI\n  name: gpt-4o-mini\n"
        "workflow:\n  name: requirement-analysis\n",
    )
    assert load_config(tmp_path).model.provider == "openai"


def test_to_dict_round_trips(tmp_path: Path) -> None:
    _write(tmp_path, VALID)
    config = load_config(tmp_path)

    again = load_config(tmp_path)
    again_path = _write(tmp_path / "copy", dump_config(config.to_dict()))
    again = load_config(tmp_path / "copy")

    assert again.model == config.model
    assert again.skills == config.skills
    assert again.workflow.name == config.workflow.name
    assert again_path.is_file()


def test_model_name_falls_back_to_environment_variable(
    tmp_path: Path, monkeypatch
) -> None:
    """Deployments can pin the model without editing YAML."""
    monkeypatch.setenv("AGENT_KIT_MODEL", "gpt-4o")
    _write(tmp_path, "model:\n  provider: openai\nworkflow:\n  name: requirement-analysis\n")

    config = load_config(tmp_path)

    assert config.model.name == "gpt-4o"


def test_yaml_model_name_wins_over_environment_variable(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENT_KIT_MODEL", "from-env")
    _write(
        tmp_path,
        "model:\n  provider: mock\n  name: from-yaml\n"
        "workflow:\n  name: requirement-analysis\n",
    )

    assert load_config(tmp_path).model.name == "from-yaml"


def test_missing_model_name_mentions_the_environment_variable(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("AGENT_KIT_MODEL", raising=False)
    _write(tmp_path, "model:\n  provider: openai\nworkflow:\n  name: requirement-analysis\n")

    with pytest.raises(ConfigError, match="AGENT_KIT_MODEL"):
        load_config(tmp_path)


# --- orchestrator section -------------------------------------------------
def test_orchestrator_defaults_when_the_section_is_absent(tmp_path: Path) -> None:
    _write(tmp_path, VALID)

    orchestrator = load_config(tmp_path).orchestrator

    assert orchestrator.strategy == "auto"
    assert orchestrator.planner == "rules"
    assert orchestrator.agents == (
        "requirement-analysis",
        "code-review",
        "unit-test-generation",
    )
    assert orchestrator.default_agents == ("requirement-analysis",)


def test_orchestrator_section_is_parsed(tmp_path: Path) -> None:
    _write(
        tmp_path,
        VALID
        + "orchestrator:\n"
        "  strategy: all\n"
        "  planner: rules\n"
        "  agents:\n"
        "    - code-review\n"
        "  default_agents:\n"
        "    - code-review\n",
    )

    orchestrator = load_config(tmp_path).orchestrator

    assert orchestrator.strategy == "all"
    assert orchestrator.agents == ("code-review",)
    assert orchestrator.default_agents == ("code-review",)


def test_orchestrator_agents_may_be_empty(tmp_path: Path) -> None:
    _write(tmp_path, VALID + "orchestrator:\n  agents: []\n")
    assert load_config(tmp_path).orchestrator.agents == ()


def test_orchestrator_rejects_an_unknown_strategy(tmp_path: Path) -> None:
    _write(tmp_path, VALID + "orchestrator:\n  strategy: llm\n")
    with pytest.raises(ConfigError, match=r"orchestrator.strategy must be one of"):
        load_config(tmp_path)


def test_orchestrator_rejects_an_unknown_planner(tmp_path: Path) -> None:
    _write(tmp_path, VALID + "orchestrator:\n  planner: llm\n")
    with pytest.raises(ConfigError, match="not supported yet"):
        load_config(tmp_path)


def test_orchestrator_agents_must_be_a_list(tmp_path: Path) -> None:
    _write(tmp_path, VALID + "orchestrator:\n  agents: code-review\n")
    with pytest.raises(ConfigError, match=r"orchestrator.agents must be a list"):
        load_config(tmp_path)


def test_to_dict_includes_the_orchestrator(tmp_path: Path) -> None:
    _write(tmp_path, VALID)
    data = load_config(tmp_path).to_dict()

    assert data["orchestrator"]["strategy"] == "auto"
    assert data["orchestrator"]["planner"] == "rules"
    assert data["orchestrator"]["agents"] == [
        "requirement-analysis",
        "code-review",
        "unit-test-generation",
    ]
