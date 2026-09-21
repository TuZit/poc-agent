"""Unit tests for the Kiro integration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_kit.cli.main import app
from agent_kit.integrations.kiro import (
    KIRO_SPEC_NAME,
    expected_kiro_files,
    install_kiro,
    kiro_status,
    uninstall_kiro,
)

STEERING = Path(".kiro/steering/agent-kit.md")


def _out(result) -> str:
    combined = getattr(result, "output", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    if stderr and stderr not in combined:
        return f"{combined}\n{stderr}"
    return combined


@pytest.fixture
def kiro_project(tmp_path: Path) -> Path:
    project = tmp_path / "kiro-project"
    (project / ".agent").mkdir(parents=True)
    (project / ".agent" / "config.yaml").write_text(
        "model:\n  provider: mock\n  name: mock-model\n"
        "workflow:\n  name: requirement-analysis\n",
        encoding="utf-8",
    )
    return project


# --- install --------------------------------------------------------------
def test_install_writes_the_documented_kiro_layout(kiro_project: Path) -> None:
    written = install_kiro(kiro_project)

    expected = [
        ".kiro/steering/agent-kit.md",
        ".kiro/steering/agent-kit-requirements.md",
        ".kiro/hooks/agent-kit-context.json",
        ".kiro/hooks/agent-kit-evaluate.json",
        ".kiro/hooks/agent-kit-run.json",
        ".kiro/agents/agent-kit.json",
        ".kiro/prompts/agent-kit.run.md",
        ".kiro/prompts/agent-kit.evaluate.md",
        ".kiro/settings/mcp.json",
        f".kiro/specs/{KIRO_SPEC_NAME}/requirements.md",
        f".kiro/specs/{KIRO_SPEC_NAME}/design.md",
        f".kiro/specs/{KIRO_SPEC_NAME}/tasks.md",
        f".kiro/specs/{KIRO_SPEC_NAME}/.config.kiro",
    ]
    present = {str(path.relative_to(kiro_project)) for path in written}
    assert set(expected) <= present
    for relative in expected:
        assert (kiro_project / relative).is_file(), relative


def test_installed_files_match_expected_set(kiro_project: Path) -> None:
    install_kiro(kiro_project)
    present, missing = kiro_status(kiro_project)
    assert missing == []
    assert len(present) == len(expected_kiro_files(kiro_project))


def test_every_generated_json_file_parses(kiro_project: Path) -> None:
    install_kiro(kiro_project)
    json_files = list((kiro_project / ".kiro").rglob("*.json"))
    assert json_files, "the integration must generate JSON files"
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))


def test_no_legacy_hook_files_are_generated(kiro_project: Path) -> None:
    """`.kiro.hook` (when/then) is the replaced pre-1.0 format."""
    install_kiro(kiro_project)
    assert list((kiro_project / ".kiro").rglob("*.kiro.hook")) == []


def test_hooks_use_the_v1_schema(kiro_project: Path) -> None:
    install_kiro(kiro_project)

    triggers = set()
    for path in sorted((kiro_project / ".kiro" / "hooks").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["version"] == "v1"
        for hook in data["hooks"]:
            assert hook["name"]
            assert hook["action"]["type"] in {"command", "agent"}
            assert hook["action"].get("command") or hook["action"].get("prompt")
            triggers.add(hook["trigger"])

    assert {"UserPromptSubmit", "PostFileSave", "Manual"} == triggers


def test_evaluate_hook_targets_output_files(kiro_project: Path) -> None:
    install_kiro(kiro_project)
    data = json.loads(
        (kiro_project / ".kiro" / "hooks" / "agent-kit-evaluate.json").read_text(encoding="utf-8")
    )
    hook = data["hooks"][0]
    assert hook["trigger"] == "PostFileSave"
    assert "output" in hook["matcher"]
    assert "agent-kit evaluate" in hook["action"]["command"]


def test_steering_files_declare_inclusion_modes(kiro_project: Path) -> None:
    install_kiro(kiro_project)

    always = (kiro_project / STEERING).read_text(encoding="utf-8")
    assert always.startswith("---\ninclusion: always\n---")

    file_match = (kiro_project / ".kiro/steering/agent-kit-requirements.md").read_text(
        encoding="utf-8"
    )
    assert "inclusion: fileMatch" in file_match
    assert "fileMatchPattern" in file_match


def test_mcp_settings_register_the_agent_kit_server(kiro_project: Path) -> None:
    install_kiro(kiro_project)
    settings = json.loads(
        (kiro_project / ".kiro" / "settings" / "mcp.json").read_text(encoding="utf-8")
    )

    server = settings["mcpServers"]["agent-kit"]
    assert server["command"] == "agent-kit"
    assert server["args"] == ["mcp", "serve"]
    assert server["disabled"] is False
    assert "agent_kit_capabilities" in server["autoApprove"]
    # run_workflow writes files and calls a model, so it stays out of autoApprove.
    assert "agent_kit_run_workflow" not in server["autoApprove"]


def test_custom_agent_references_steering_and_mcp_tools(kiro_project: Path) -> None:
    install_kiro(kiro_project)
    agent = json.loads((kiro_project / ".kiro" / "agents" / "agent-kit.json").read_text("utf-8"))

    assert agent["name"] == "agent-kit"
    assert agent["includeMcpJson"] is True
    assert "file://.kiro/steering/**/*.md" in agent["resources"]
    assert "@agent-kit/agent_kit_run_workflow" in agent["tools"] or "@agent-kit" in agent["tools"]


def test_spec_config_carries_a_generated_spec_id(kiro_project: Path) -> None:
    install_kiro(kiro_project)
    config = json.loads(
        (kiro_project / ".kiro" / "specs" / KIRO_SPEC_NAME / ".config.kiro").read_text("utf-8")
    )
    assert config["workflowType"] == "requirements-first"
    assert config["specType"] == "feature"
    assert len(config["specId"]) == 36


def test_requirements_use_ears_notation(kiro_project: Path) -> None:
    install_kiro(kiro_project)
    requirements = (
        kiro_project / ".kiro" / "specs" / KIRO_SPEC_NAME / "requirements.md"
    ).read_text(encoding="utf-8")
    assert "## Requirements" in requirements
    assert "**User Story:**" in requirements
    assert "#### Acceptance Criteria" in requirements
    assert "WHEN " in requirements and "THE SYSTEM SHALL" in requirements


def test_tasks_use_kiro_checkbox_and_traceability_format(kiro_project: Path) -> None:
    install_kiro(kiro_project)
    tasks = (kiro_project / ".kiro" / "specs" / KIRO_SPEC_NAME / "tasks.md").read_text("utf-8")
    assert tasks.startswith("# Implementation Plan:")
    assert "## Tasks" in tasks
    assert "- [x] 1." in tasks
    assert "_Requirements:" in tasks


def test_install_keeps_customised_files_without_force(kiro_project: Path) -> None:
    install_kiro(kiro_project)
    steering = kiro_project / STEERING
    steering.write_text("my own steering", encoding="utf-8")

    written = install_kiro(kiro_project)

    assert steering.read_text(encoding="utf-8") == "my own steering"
    assert steering not in written


def test_install_force_overwrites(kiro_project: Path) -> None:
    install_kiro(kiro_project)
    steering = kiro_project / STEERING
    steering.write_text("my own steering", encoding="utf-8")

    install_kiro(kiro_project, force=True)

    assert "Agent Kit POC" in steering.read_text(encoding="utf-8")


def test_custom_command_is_used_in_templates(kiro_project: Path) -> None:
    install_kiro(kiro_project, agent_kit_command="uv run agent-kit")
    settings = json.loads(
        (kiro_project / ".kiro" / "settings" / "mcp.json").read_text(encoding="utf-8")
    )
    assert settings["mcpServers"]["agent-kit"]["command"] == "uv run agent-kit"


def test_uninstall_removes_managed_files_and_keeps_user_files(kiro_project: Path) -> None:
    install_kiro(kiro_project)
    own_file = kiro_project / ".kiro" / "steering" / "my-notes.md"
    own_file.write_text("mine", encoding="utf-8")

    removed = uninstall_kiro(kiro_project)

    assert (kiro_project / STEERING) not in [path for path in removed] or not (
        kiro_project / STEERING
    ).exists()
    assert not (kiro_project / ".kiro" / "settings" / "mcp.json").exists()
    assert own_file.is_file()
    assert kiro_project / ".kiro" in [own_file.parent, kiro_project / ".kiro"]


# --- CLI ------------------------------------------------------------------
def test_cli_kiro_install_and_status(runner, kiro_project: Path) -> None:
    install = runner.invoke(app, ["kiro", "install", "--project", str(kiro_project)])
    assert install.exit_code == 0, _out(install)
    assert "Kiro integration — 13 file(s)" in _out(install)

    status = runner.invoke(app, ["kiro", "status", "--project", str(kiro_project)])
    assert status.exit_code == 0, _out(status)
    assert "All requested integrations are complete." in _out(status)


def test_cli_kiro_status_fails_when_missing(runner, kiro_project: Path) -> None:
    result = runner.invoke(app, ["kiro", "status", "--project", str(kiro_project)])

    assert result.exit_code == 1
    assert "agent-kit integration install kiro" in _out(result)


def test_cli_kiro_uninstall(runner, kiro_project: Path) -> None:
    runner.invoke(app, ["kiro", "install", "--project", str(kiro_project)])

    result = runner.invoke(
        app, ["kiro", "uninstall", "--project", str(kiro_project), "--yes"]
    )

    assert result.exit_code == 0, _out(result)
    assert not (kiro_project / ".kiro" / "settings" / "mcp.json").exists()


def test_init_with_ai_kiro_installs_the_integration(runner, tmp_path: Path) -> None:
    project = tmp_path / "init-kiro"

    result = runner.invoke(app, ["init", str(project), "--ai", "kiro"])

    assert result.exit_code == 0, _out(result)
    assert (project / ".agent" / "config.yaml").is_file()
    assert (project / STEERING).is_file()
    assert (project / ".kiro" / "settings" / "mcp.json").is_file()
    assert "Kiro integration — 13 file(s)" in _out(result)
