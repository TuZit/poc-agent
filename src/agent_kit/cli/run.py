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
from agent_kit.workflow import WorkflowError, create_workflow

#: Fallback input when neither ``--input`` nor a workflow sample is available.
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
        None,
        "--workflow",
        help=(
            "Override the configured workflow: requirement-analysis | code-review | "
            "unit-test-generation | orchestration."
        ),
    ),
    agents: str | None = typer.Option(
        None,
        "--agents",
        help="With --workflow orchestration: force these agents (comma-separated).",
    ),
    strategy: str | None = typer.Option(
        None,
        "--strategy",
        help="With --workflow orchestration: 'auto' (route by signals) or 'all'.",
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

    workflow_name = workflow or config.workflow.name
    try:
        workflow_object = create_workflow(workflow_name)
    except WorkflowError as exc:
        fail(str(exc))

    # Default input follows the workflow (each specialist ships its own sample).
    default_input = Path(workflow_object.default_input or DEFAULT_INPUT)
    source_path = Path(input_file) if input_file else Path(project) / default_input
    if not source_path.is_file():
        fail(
            f"Input file not found: {source_path}. "
            "Pass --input <file> or add the sample input to samples/."
        )

    destination = (
        Path(output_file) if output_file else Path(project) / "output" / f"{source_path.stem}.md"
    )

    run_options: dict[str, object] = {}
    if agents:
        run_options["agents"] = agents
    if strategy:
        run_options["strategy"] = strategy

    info(f"Running workflow '{workflow_name}' — {runtime.describe()}")
    try:
        result = runtime.run_workflow(
            source_path.read_text(encoding="utf-8"),
            workflow_name=workflow_name,
            skill_name=skill,
            options=run_options,
        )
    except (WorkflowError, SkillError, ModelError, AgentError) as exc:
        fail(str(exc))

    selected = result.metadata.get("selected_agents")
    if selected:
        info(
            f"✓ Orchestrator selected: {', '.join(selected)} "
            f"(strategy: {result.metadata.get('strategy')})"
        )

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
