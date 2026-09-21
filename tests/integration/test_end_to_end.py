"""End-to-end integration test.

    init → write configuration → run workflow → generate output → evaluate → PASS

Uses ``MockModel`` throughout, so no API key is required.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_kit.agent.runtime import AgentRuntime
from agent_kit.cli.main import app
from agent_kit.config import load_config
from agent_kit.evaluation import SAMPLE_SECTIONS, evaluate_file, extract_sections
from agent_kit.model.base import ModelResponse, ToolCall
from agent_kit.model.mock import MOCK_REQUIREMENT_SUMMARY, MockModel
from agent_kit.paths import samples_dir

MOCK_CONFIG = """\
agent:
  name: e2e-agent

model:
  provider: mock
  name: mock-model

tools:
  filesystem:
    enabled: true
  shell:
    enabled: true

skills:
  - requirement-analysis

workflow:
  name: requirement-analysis
"""


def _out(result) -> str:
    combined = getattr(result, "output", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    if stderr and stderr not in combined:
        return f"{combined}\n{stderr}"
    return combined


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove the whole pipeline runs without any provider credential."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_full_poc_flow(tmp_path: Path) -> None:
    runner = CliRunner()
    project = tmp_path / "demo-project"

    # 1. install/init ------------------------------------------------------
    init_result = runner.invoke(app, ["init", str(project)])
    assert init_result.exit_code == 0, _out(init_result)

    # 2. configure the deterministic model ---------------------------------
    (project / ".agent" / "config.yaml").write_text(MOCK_CONFIG, encoding="utf-8")

    # 3. doctor ------------------------------------------------------------
    doctor_result = runner.invoke(app, ["doctor", "--project", str(project)])
    assert doctor_result.exit_code == 0, _out(doctor_result)
    assert "Agent environment is ready." in _out(doctor_result)

    # 4. run the workflow --------------------------------------------------
    run_result = runner.invoke(app, ["run", "--project", str(project)])
    assert run_result.exit_code == 0, _out(run_result)

    output_file = project / "output" / "sample-001.md"
    assert output_file.is_file(), "run must generate output/sample-001.md"
    assert output_file.read_text(encoding="utf-8").strip(), "output must not be empty"

    # 5. evaluate ----------------------------------------------------------
    evaluate_result = runner.invoke(app, ["evaluate", str(output_file)])
    assert evaluate_result.exit_code == 0, _out(evaluate_result)
    assert "Result: PASS" in _out(evaluate_result)


def test_generated_output_covers_the_sample_expectations(tmp_path: Path) -> None:
    runner = CliRunner()
    project = tmp_path / "demo-project"
    runner.invoke(app, ["init", str(project)])
    (project / ".agent" / "config.yaml").write_text(MOCK_CONFIG, encoding="utf-8")
    runner.invoke(app, ["run", "--project", str(project)])

    generated = (project / "output" / "sample-001.md").read_text(encoding="utf-8")
    expected = (
        samples_dir() / "requirement-analysis" / "expected" / "sample-001.md"
    ).read_text(encoding="utf-8")

    # Structure is compared, not exact text: every expected section must exist.
    assert extract_sections(expected) <= extract_sections(generated)

    result = evaluate_file(project / "output" / "sample-001.md", SAMPLE_SECTIONS)
    assert result.passed is True


def test_agent_uses_the_filesystem_tool_inside_the_pipeline(tmp_path: Path) -> None:
    project = tmp_path / "tool-project"
    (project / ".agent").mkdir(parents=True)
    (project / ".agent" / "config.yaml").write_text(MOCK_CONFIG, encoding="utf-8")

    runtime = AgentRuntime(load_config(project))
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
                            "content": "# Requirement Summary\n\n## Objective\n\nPersisted.\n",
                        },
                    )
                ],
            ),
            ModelResponse(content=MOCK_REQUIREMENT_SUMMARY),
        ]
    )

    result = runtime.run_workflow("Build an e-commerce product management API.")

    assert result.tool_call_count == 1
    assert result.tool_invocations[0].success is True
    assert (project / "output" / "summary.md").is_file()
    assert result.valid is True


def test_runtime_is_usable_without_the_cli(tmp_path: Path) -> None:
    """Development principle 7: the runtime must not depend on the CLI."""
    project = tmp_path / "library-project"
    (project / ".agent").mkdir(parents=True)
    (project / ".agent" / "config.yaml").write_text(MOCK_CONFIG, encoding="utf-8")

    runtime = AgentRuntime(load_config(project))
    result = runtime.run_workflow("Build a product API.")

    assert result.valid is True
    assert result.output.startswith("# Requirement Summary")
    assert evaluate_file.__module__.startswith("agent_kit.evaluation")
