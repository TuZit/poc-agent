"""``agent-kit init`` — scaffold a new project from the bundled template."""

from __future__ import annotations

from pathlib import Path

import typer

from agent_kit.cli.common import fail, info, relative_to
from agent_kit.cli.integration import install_integrations
from agent_kit.integrations import (
    IntegrationError,
    available_integrations,
    parse_integration_names,
    resolve_integrations,
)
from agent_kit.scaffold import ScaffoldError, init_project


def init_command(
    project: Path = typer.Argument(..., help="Directory to create, e.g. my-project."),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite an existing non-empty directory."
    ),
    integration: list[str] | None = typer.Option(
        None,
        "--integration",
        "--ai",
        "-i",
        help=(
            "Agent-tool integration(s) to install: "
            f"{', '.join(available_integrations())} — comma-separated or repeated. "
            "Use 'all' for every integration."
        ),
    ),
) -> None:
    """Create a new agent-kit project (.agent/config.yaml, README, samples)."""
    requested = parse_integration_names(integration)
    if "all" in requested:
        requested = available_integrations()
    try:
        # Validate names before touching the filesystem: a typo must not leave a
        # half-scaffolded project behind.
        resolve_integrations(requested)
    except IntegrationError as exc:
        fail(str(exc))

    try:
        written = init_project(project, force=force)
    except ScaffoldError as exc:
        fail(str(exc))

    target = Path(project).resolve()
    info(f"✓ Initialized agent-kit project in {target}")
    for path in sorted(written):
        info(f"  + {relative_to(path, target)}")

    if requested:
        info("")
        install_integrations(requested, target, force=force)

    info("")
    info("Next steps:")
    info(f"  cd {project}")
    info("  agent-kit doctor                    # validate configuration and environment")
    info("  agent-kit config set model.provider mock   # optional: run offline")
    info("  agent-kit run")
    info("  agent-kit evaluate output/sample-001.md")
