"""Unit tests for the CLI surface (Typer commands)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from agent_kit.cli.main import app


def _out(result) -> str:
    """Combined stdout/stderr of a CliRunner result, across click versions."""
    combined = getattr(result, "output", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    if stderr and stderr not in combined:
        return f"{combined}\n{stderr}"
    return combined


# --- global ---------------------------------------------------------------
def test_help_lists_every_command(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("init", "doctor", "run", "evaluate", "config"):
        assert command in _out(result)


def test_version_flag(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "agent-kit 0.1.0" in _out(result)


def test_no_arguments_shows_help(runner: CliRunner) -> None:
    result = runner.invoke(app, [])
    assert "Usage" in _out(result)


# --- init -----------------------------------------------------------------
def test_init_creates_project(runner: CliRunner, tmp_path: Path) -> None:
    target = tmp_path / "new-project"

    result = runner.invoke(app, ["init", str(target)])

    assert result.exit_code == 0, _out(result)
    assert (target / ".agent" / "config.yaml").is_file()
    assert (target / "README.md").is_file()
    assert (target / "samples" / "requirement-analysis" / "input" / "sample-001.md").is_file()
    assert "Initialized agent-kit project" in _out(result)
    assert "agent-kit doctor" in _out(result)


def test_init_refuses_existing_project(runner: CliRunner, tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "keep.txt").write_text("x", encoding="utf-8")

    result = runner.invoke(app, ["init", str(target)])

    assert result.exit_code == 1
    assert "already exists" in _out(result)
    assert not (target / ".agent").exists()


def test_init_force_overwrites(runner: CliRunner, tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "keep.txt").write_text("x", encoding="utf-8")

    result = runner.invoke(app, ["init", str(target), "--force"])

    assert result.exit_code == 0, _out(result)
    assert (target / ".agent" / "config.yaml").is_file()
    assert (target / "keep.txt").is_file()  # unrelated files are untouched


def test_init_rejects_unknown_integration(runner: CliRunner, tmp_path: Path) -> None:
    target = tmp_path / "p"

    result = runner.invoke(app, ["init", str(target), "--ai", "does-not-exist"])

    assert result.exit_code == 1
    output = _out(result)
    assert "Unknown integration" in output
    assert "Available integrations" in output
    # A typo must not leave a half-scaffolded project behind.
    assert not target.exists()


# --- config ---------------------------------------------------------------
def test_config_show_prints_resolved_configuration(
    runner: CliRunner, mock_project: Path
) -> None:
    result = runner.invoke(app, ["config", "show", "--project", str(mock_project)])

    assert result.exit_code == 0, _out(result)
    assert "provider: mock" in _out(result)
    assert "requirement-analysis" in _out(result)


def test_config_get_scalar_and_nested(runner: CliRunner, mock_project: Path) -> None:
    provider = runner.invoke(
        app, ["config", "get", "model.provider", "--project", str(mock_project)]
    )
    enabled = runner.invoke(
        app, ["config", "get", "tools.filesystem.enabled", "--project", str(mock_project)]
    )
    skill = runner.invoke(app, ["config", "get", "skills.0", "--project", str(mock_project)])

    assert provider.exit_code == 0 and "mock" in _out(provider)
    assert enabled.exit_code == 0 and "True" in _out(enabled)
    assert skill.exit_code == 0 and "requirement-analysis" in _out(skill)


def test_config_get_unknown_key_fails(runner: CliRunner, mock_project: Path) -> None:
    result = runner.invoke(app, ["config", "get", "model.nope", "--project", str(mock_project)])

    assert result.exit_code == 1
    assert "not found" in _out(result)


def test_config_set_writes_value(runner: CliRunner, mock_project: Path) -> None:
    result = runner.invoke(
        app,
        ["config", "set", "model.name", "other-model", "--project", str(mock_project)],
    )

    assert result.exit_code == 0, _out(result)
    assert "name: other-model" in (mock_project / ".agent" / "config.yaml").read_text(
        encoding="utf-8"
    )


def test_config_set_coerces_booleans(runner: CliRunner, mock_project: Path) -> None:
    runner.invoke(
        app,
        ["config", "set", "tools.shell.enabled", "true", "--project", str(mock_project)],
    )

    result = runner.invoke(
        app, ["config", "get", "tools.shell.enabled", "--project", str(mock_project)]
    )
    assert "True" in _out(result)


def test_config_without_project_fails(runner: CliRunner, bare_project: Path) -> None:
    result = runner.invoke(app, ["config", "show", "--project", str(bare_project)])

    assert result.exit_code == 1
    assert "agent-kit init" in _out(result)


# --- doctor ---------------------------------------------------------------
def test_doctor_passes_for_mock_project(runner: CliRunner, mock_project: Path) -> None:
    result = runner.invoke(app, ["doctor", "--project", str(mock_project)])

    output = _out(result)
    assert result.exit_code == 0, output
    assert "Agent Kit Doctor" in output
    assert "Python 3.11+" in output
    assert "Configuration" in output
    assert "Model configuration (mock/mock-model)" in output
    assert "OPENAI_API_KEY" in output
    assert "Agent environment is ready." in output


def test_doctor_fails_without_configuration(runner: CliRunner, bare_project: Path) -> None:
    result = runner.invoke(app, ["doctor", "--project", str(bare_project)])

    assert result.exit_code == 1
    assert "NOT ready" in _out(result)


def test_doctor_reports_unknown_workflow(runner: CliRunner, mock_project: Path) -> None:
    runner.invoke(
        app, ["config", "set", "workflow.name", "does-not-exist", "--project", str(mock_project)]
    )

    result = runner.invoke(app, ["doctor", "--project", str(mock_project)])

    assert result.exit_code == 1
    assert "does-not-exist" in _out(result)


# --- run ------------------------------------------------------------------
def test_run_writes_output_file(runner: CliRunner, mock_project: Path) -> None:
    result = runner.invoke(app, ["run", "--project", str(mock_project)])

    output = _out(result)
    assert result.exit_code == 0, output
    assert "Output written to output/sample-001.md" in output
    assert "Validation passed" in output
    assert (mock_project / "output" / "sample-001.md").is_file()


def test_run_accepts_custom_input_and_output(runner: CliRunner, mock_project: Path) -> None:
    source = mock_project / "custom.md"
    source.write_text("Build a tiny API.", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "run",
            "--project",
            str(mock_project),
            "--input",
            str(source),
            "--output",
            str(mock_project / "out" / "custom.md"),
        ],
    )

    assert result.exit_code == 0, _out(result)
    assert (mock_project / "out" / "custom.md").is_file()


def test_run_fails_when_input_is_missing(runner: CliRunner, mock_project: Path) -> None:
    result = runner.invoke(
        app, ["run", "--project", str(mock_project), "--input", "nope.md"]
    )

    assert result.exit_code == 1
    assert "Input file not found" in _out(result)


def test_run_fails_for_unknown_workflow(runner: CliRunner, mock_project: Path) -> None:
    result = runner.invoke(
        app,
        ["run", "--project", str(mock_project), "--workflow", "does-not-exist"],
    )

    assert result.exit_code == 1
    assert "Unknown workflow" in _out(result)


# --- evaluate -------------------------------------------------------------
def test_evaluate_passes_after_run(runner: CliRunner, mock_project: Path) -> None:
    runner.invoke(app, ["run", "--project", str(mock_project)])

    result = runner.invoke(app, ["evaluate", str(mock_project / "output" / "sample-001.md")])

    output = _out(result)
    assert result.exit_code == 0, output
    assert "Result: PASS" in output
    assert "✓ Output generated" in output
    assert "✓ Open Questions" in output


def test_evaluate_fails_for_missing_file(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["evaluate", str(tmp_path / "nothing.md")])

    assert result.exit_code == 1
    assert "Result: FAIL" in _out(result)


def test_evaluate_honours_required_concepts(runner: CliRunner, mock_project: Path) -> None:
    runner.invoke(app, ["run", "--project", str(mock_project)])
    output_file = str(mock_project / "output" / "sample-001.md")

    passed = runner.invoke(app, ["evaluate", output_file, "-c", "create product"])
    failed = runner.invoke(app, ["evaluate", output_file, "-c", "blockchain"])

    assert passed.exit_code == 0, _out(passed)
    assert failed.exit_code == 1
    assert "Concept: blockchain" in _out(failed)


# --- agents ---------------------------------------------------------------
def test_agents_lists_specialists_and_the_orchestrator(
    runner: CliRunner, mock_project: Path
) -> None:
    result = runner.invoke(app, ["agents", "--project", str(mock_project)])

    output = _out(result)
    assert result.exit_code == 0, output
    for name in ("requirement-analysis", "code-review", "unit-test-generation"):
        assert name in output
    for section in ("Summary", "Test Scope", "Test Cases"):
        assert section in output
    assert "Orchestrator: workflow=orchestration" in output
    assert "strategy=auto" in output


def test_run_code_review_uses_its_own_sample_input(
    runner: CliRunner, mock_project: Path
) -> None:
    result = runner.invoke(
        app, ["run", "--project", str(mock_project), "--workflow", "code-review"]
    )

    assert result.exit_code == 0, _out(result)
    assert (mock_project / "output" / "sample-code-review.md").is_file()


def test_run_orchestration_reports_the_selected_agents(
    runner: CliRunner, mock_project: Path
) -> None:
    result = runner.invoke(
        app, ["run", "--project", str(mock_project), "--workflow", "orchestration"]
    )

    output = _out(result)
    assert result.exit_code == 0, output
    assert "Orchestrator selected: code-review, unit-test-generation" in output
    report = (mock_project / "output" / "sample-orchestration.md").read_text(encoding="utf-8")
    assert "## Agent: Code Review" in report
    assert "## Agent: Unit Test Generation" in report


def test_run_orchestration_accepts_explicit_agents(
    runner: CliRunner, mock_project: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--project",
            str(mock_project),
            "--workflow",
            "orchestration",
            "--agents",
            "code-review",
        ],
    )

    assert result.exit_code == 0, _out(result)
    report = (mock_project / "output" / "sample-orchestration.md").read_text(encoding="utf-8")
    assert "## Agent: Code Review" in report
    assert "## Agent: Unit Test Generation" not in report


def test_run_orchestration_rejects_an_unknown_agent(
    runner: CliRunner, mock_project: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--project",
            str(mock_project),
            "--workflow",
            "orchestration",
            "--agents",
            "does-not-exist",
        ],
    )

    assert result.exit_code == 1
    assert "Unknown agent" in _out(result)


def test_run_orchestration_rejects_an_unknown_strategy(
    runner: CliRunner, mock_project: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--project",
            str(mock_project),
            "--workflow",
            "orchestration",
            "--strategy",
            "llm",
        ],
    )

    assert result.exit_code == 1
    assert "Unknown orchestrator strategy" in _out(result)


def test_evaluate_uses_the_workflow_section_set(runner: CliRunner, mock_project: Path) -> None:
    runner.invoke(app, ["run", "--project", str(mock_project), "--workflow", "code-review"])
    output_file = str(mock_project / "output" / "sample-code-review.md")

    matching = runner.invoke(app, ["evaluate", output_file, "--workflow", "code-review"])
    mismatched = runner.invoke(app, ["evaluate", output_file])

    assert matching.exit_code == 0, _out(matching)
    assert "Result: PASS" in _out(matching)
    # Requirement sections are not present in a code review report.
    assert mismatched.exit_code == 1
    assert "Objective" in _out(mismatched)


def test_doctor_reports_the_orchestrator(runner: CliRunner, mock_project: Path) -> None:
    result = runner.invoke(app, ["doctor", "--project", str(mock_project)])

    output = _out(result)
    assert result.exit_code == 0, output
    assert "Orchestrator agents (3:" in output


def test_doctor_flags_an_unknown_agent(runner: CliRunner, mock_project: Path) -> None:
    runner.invoke(
        app,
        ["config", "set", "orchestrator.agents.0", "typo-agent", "--project", str(mock_project)],
    )

    result = runner.invoke(app, ["doctor", "--project", str(mock_project)])

    assert result.exit_code == 1
    assert "typo-agent" in _out(result)
