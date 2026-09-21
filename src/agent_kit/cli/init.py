"""``agent-kit init`` — scaffold a new project from the bundled template."""

from __future__ import annotations

from pathlib import Path

import typer

from agent_kit.cli.common import fail, info, relative_to
from agent_kit.scaffold import ScaffoldError, init_project

AI_CHOICES = ("none", "kiro")


def init_command(
    project: Path = typer.Argument(..., help="Directory to create, e.g. my-project."),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite an existing non-empty directory."
    ),
    ai: str = typer.Option(
        "none",
        "--ai",
        help="Also install an assistant integration after scaffolding: none | kiro.",
    ),
) -> None:
    """Create a new agent-kit project (.agent/config.yaml, README, samples)."""
    choice = ai.strip().lower()
    if choice not in AI_CHOICES:
        fail(f"Unknown --ai value '{ai}'. Supported: {', '.join(AI_CHOICES)}.")

    try:
        written = init_project(project, force=force)
    except ScaffoldError as exc:
        fail(str(exc))

    target = Path(project).resolve()
    info(f"✓ Initialized agent-kit project in {target}")
    for path in sorted(written):
        info(f"  + {relative_to(path, target)}")

    if choice == "kiro":
        from agent_kit.integrations.kiro import KiroIntegrationError, install_kiro

        try:
            kiro_files = install_kiro(target, force=force)
        except KiroIntegrationError as exc:
            fail(str(exc))
        info("")
        info("✓ Kiro integration installed")
        for path in sorted(kiro_files):
            info(f"  + {relative_to(path, target)}")

    info("")
    info("Next steps:")
    info(f"  cd {project}")
    info("  agent-kit doctor                    # validate configuration and environment")
    info("  agent-kit config set model.provider mock   # optional: run offline")
    info("  agent-kit run")
    info("  agent-kit evaluate output/sample-001.md")
