"""Unit tests for the generic agent-tool integration framework.

This phase ships Kiro only, so these tests pin the registry contract: Kiro is the
sole registered integration, name parsing and lookup behave, and adding a tool
later requires no CLI change.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_kit.cli.main import app
from agent_kit.integrations import (
    INTEGRATION_REGISTRY,
    KIRO,
    IntegrationError,
    TemplateIntegration,
    available_integrations,
    get_integration,
    install_many,
    integration_descriptions,
    parse_integration_names,
    resolve_integrations,
)


def _out(result) -> str:
    combined = getattr(result, "output", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    if stderr and stderr not in combined:
        return f"{combined}\n{stderr}"
    return combined


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".agent").mkdir(parents=True)
    (root / ".agent" / "config.yaml").write_text(
        "model:\n  provider: mock\n  name: mock-model\n"
        "workflow:\n  name: requirement-analysis\n",
        encoding="utf-8",
    )
    return root


# --- registry -------------------------------------------------------------
def test_only_kiro_is_registered_in_this_phase() -> None:
    assert available_integrations() == ["kiro"]
    assert list(INTEGRATION_REGISTRY) == ["kiro"]


def test_registry_exposes_titles_and_descriptions() -> None:
    descriptions = integration_descriptions()
    assert descriptions == [("kiro", "Kiro", KIRO.description)]
    assert "steering" in KIRO.description


def test_get_integration_is_case_insensitive() -> None:
    assert get_integration("Kiro") is KIRO
    assert get_integration("  kiro ") is KIRO


def test_unknown_integration_lists_the_available_names() -> None:
    with pytest.raises(IntegrationError) as excinfo:
        get_integration("claude")

    message = str(excinfo.value)
    assert "Unknown integration 'claude'" in message
    assert "kiro" in message


# --- name parsing ---------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, []),
        ("kiro", ["kiro"]),
        ("KIRO", ["kiro"]),
        (" kiro , kiro ", ["kiro"]),
        (["kiro"], ["kiro"]),
        ("kiro,kiro", ["kiro"]),
        ("", []),
    ],
)
def test_parse_integration_names(value, expected) -> None:
    assert parse_integration_names(value) == expected


def test_resolve_integrations_returns_instances() -> None:
    assert resolve_integrations("kiro") == [KIRO]
    assert resolve_integrations(None) == []


# --- lifecycle through the framework --------------------------------------
def test_install_many_returns_written_files_per_integration(project: Path) -> None:
    written = install_many([KIRO], project)

    assert set(written) == {"kiro"}
    assert len(written["kiro"]) == 21
    assert (project / ".kiro" / "settings" / "mcp.json").is_file()


def test_custom_integration_can_be_added_without_cli_changes(tmp_path: Path) -> None:
    """The seam that makes future agent tools additive."""

    class DemoIntegration(TemplateIntegration):
        name = "demo"
        title = "Demo Tool"
        description = "installs demo files"

    root = tmp_path / "demo-project"
    integration = DemoIntegration()

    # No shipped template directory yet: assert the contract, not the files.
    assert integration.destination_root(root) == root
    assert integration.code_generated_files == ()
    # A registered integration whose templates are missing fails loudly.
    with pytest.raises(IntegrationError, match="Templates for 'demo' not found"):
        integration.managed_files(root)
    assert integration.placeholders(root, "agent-kit")["AGENT_KIT_COMMAND"] == "agent-kit"


def test_destination_root_defaults_to_project_root(tmp_path: Path) -> None:
    assert KIRO.destination_root(tmp_path) == tmp_path / ".kiro"


# --- CLI ------------------------------------------------------------------
def test_cli_integration_list_shows_kiro(runner: CliRunner, project: Path) -> None:
    result = runner.invoke(app, ["integration", "list", "--project", str(project)])

    assert result.exit_code == 0, _out(result)
    output = _out(result)
    assert "kiro" in output
    assert "Kiro" in output


def test_cli_integration_install_and_status(runner: CliRunner, project: Path) -> None:
    install = runner.invoke(app, ["integration", "install", "kiro", "--project", str(project)])
    assert install.exit_code == 0, _out(install)
    assert "Kiro integration — 21 file(s)" in _out(install)

    status = runner.invoke(app, ["integration", "status", "--project", str(project)])
    assert status.exit_code == 0, _out(status)
    assert "All requested integrations are complete." in _out(status)


def test_cli_integration_install_all_is_equivalent_to_kiro(
    runner: CliRunner, project: Path
) -> None:
    result = runner.invoke(app, ["integration", "install", "all", "--project", str(project)])

    assert result.exit_code == 0, _out(result)
    assert (project / ".kiro" / "settings" / "mcp.json").is_file()


def test_cli_integration_status_fails_when_nothing_installed(
    runner: CliRunner, project: Path
) -> None:
    result = runner.invoke(app, ["integration", "status", "--project", str(project)])

    assert result.exit_code == 1
    assert "agent-kit integration install kiro" in _out(result)


def test_cli_integration_rejects_unknown_name(runner: CliRunner, project: Path) -> None:
    result = runner.invoke(app, ["integration", "install", "claude", "--project", str(project)])

    assert result.exit_code == 1
    assert "Unknown integration" in _out(result)


def test_cli_integration_uninstall(runner: CliRunner, project: Path) -> None:
    runner.invoke(app, ["integration", "install", "kiro", "--project", str(project)])

    result = runner.invoke(
        app, ["integration", "uninstall", "kiro", "--project", str(project), "--yes"]
    )

    assert result.exit_code == 0, _out(result)
    assert not (project / ".kiro" / "settings" / "mcp.json").exists()


def test_cli_init_accepts_both_integration_and_ai_flags(runner: CliRunner, tmp_path: Path) -> None:
    long_form = tmp_path / "long-form"
    short_form = tmp_path / "short-form"

    first = runner.invoke(app, ["init", str(long_form), "--integration", "kiro"])
    second = runner.invoke(app, ["init", str(short_form), "--ai", "kiro"])

    assert first.exit_code == 0, _out(first)
    assert second.exit_code == 0, _out(second)
    for project_path in (long_form, short_form):
        assert (project_path / ".kiro" / "settings" / "mcp.json").is_file()
