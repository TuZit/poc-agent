"""``agent-kit run`` — execute the configured workflow end to end."""

from __future__ import annotations

from pathlib import Path

import typer

from agent_kit.agent.agent import AgentError
from agent_kit.agent.runtime import AgentRuntime
from agent_kit.cli.common import fail, info, relative_to
from agent_kit.config import ConfigError, load_config
from agent_kit.model.base import ModelError
from agent_kit.skills import SkillError
from agent_kit.tools.base import ToolError
from agent_kit.workflow import WorkflowError

#: Default input used when ``--input`` is not given (relative to the project).
DEFAULT_INPUT = Path("samples") / "requirement-analysis" / "input" / "sample-001.md"


def run_command(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
    input_file: Path | None = typer.Option(
        None, "--input", "-i", help=f"Input file to process (default: {DEFAULT_INPUT})."
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output file (default: output/<input-stem>.md)."
    ),
    skill: str | None = typer.Option(None, "--skill", help="Override the configured skill."),
    workflow: str | None = typer.Option(
        None, "--workflow", help="Override the configured workflow."
    ),
) -> None:
    """Load config → load skill → init model and tools → run workflow → write output."""
    try:
        config = load_config(project)
    except ConfigError as exc:
        fail(str(exc))

    try:
        runtime = AgentRuntime(config)
    except (ModelError, ToolError) as exc:
        fail(str(exc))

    source_path = Path(input_file) if input_file else Path(project) / DEFAULT_INPUT
    if not source_path.is_file():
        fail(
            f"Input file not found: {source_path}. "
            "Pass --input <file> or add the sample input to samples/."
        )

    destination = (
        Path(output_file) if output_file else Path(project) / "output" / f"{source_path.stem}.md"
    )
    workflow_name = workflow or config.workflow.name

    info(f"Running workflow '{workflow_name}' — {runtime.describe()}")
    try:
        result = runtime.run_workflow(
            source_path.read_text(encoding="utf-8"),
            workflow_name=workflow_name,
            skill_name=skill,
        )
    except (WorkflowError, SkillError, ModelError, AgentError) as exc:
        fail(str(exc))

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result.output, encoding="utf-8")

    info(f"✓ Output written to {relative_to(destination, Path(project))}")
    if result.tool_invocations:
        info(f"✓ Tool calls: {result.tool_call_count}")
        for invocation in result.tool_invocations:
            info(f"    - {invocation.summary()}")

    if not result.valid:
        for issue in result.issues:
            info(f"✗ {issue}")
        fail("Workflow output failed validation. See issues above.")

    info("✓ Validation passed: all required sections present.")
    info("")
    info(f"Next: agent-kit evaluate {relative_to(destination, Path(project))}")
