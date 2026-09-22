"""``agent-kit agents`` — describe the specialist agents and the orchestrator."""

from __future__ import annotations

from pathlib import Path

import typer

from agent_kit.cli.common import fail, info
from agent_kit.config import ConfigError, load_config
from agent_kit.workflow import specialist_workflows


def agents_command(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
) -> None:
    """List the specialist agents, their output contract and the orchestrator setup."""
    try:
        config = load_config(project)
    except ConfigError as exc:
        fail(str(exc))

    enabled = list(config.orchestrator.agents)
    info("Specialist agents")
    info("")
    for workflow in specialist_workflows():
        allowed = "yes" if workflow.name in enabled else "no"
        info(f"{workflow.name:<24} {workflow.display_title()}")
        info(f"{'':<24} {workflow.description}")
        info(
            f"{'':<24} skill: {workflow.default_skill or '(none)'} | "
            f"workflow: {workflow.name} | allowed by orchestrator: {allowed}"
        )
        info(f"{'':<24} sections: {', '.join(workflow.required_sections)}")
        if workflow.default_input:
            info(f"{'':<24} sample: {workflow.default_input}")
        info("")

    info(
        f"Orchestrator: workflow=orchestration | strategy={config.orchestrator.strategy} | "
        f"planner={config.orchestrator.planner}"
    )
    fallback = ", ".join(config.orchestrator.default_agents) or "(none)"
    info(f"  agents: {', '.join(enabled) or '(none)'}")
    info(f"  fallback when no signal matches: {fallback}")
    info("")
    info("Run one agent:        agent-kit run --workflow code-review")
    info("Run the orchestrator: agent-kit run --workflow orchestration")
    info("Force agents:         agent-kit run --workflow orchestration \\")
    info("                        --agents code-review,unit-test-generation")
