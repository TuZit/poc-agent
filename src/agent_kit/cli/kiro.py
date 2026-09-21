"""``agent-kit kiro`` — alias for ``agent-kit integration <cmd> kiro``.

Kept because it is the documented shorthand and remains stable even as more
agent-tool integrations are added.
"""

from __future__ import annotations

from pathlib import Path

import typer

from agent_kit.cli.integration import (
    install_integrations,
    show_status,
    uninstall_integrations,
)

KIRO = "kiro"

kiro_app = typer.Typer(
    help="Kiro integration: steering, hooks, MCP server and spec artifacts.",
    no_args_is_help=True,
)


@kiro_app.command("install")
def install_command(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing .kiro files (default: keep them)."
    ),
    command: str = typer.Option(
        "agent-kit", "--command", help="Command Kiro should use to reach agent-kit."
    ),
) -> None:
    """Write .kiro/steering, hooks, specs, prompts, the MCP server and a custom agent."""
    install_integrations(KIRO, project, force=force, command=command)
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo("  1. Open this folder in Kiro (or run 'kiro-cli' here).")
    typer.echo("  2. Use the 'agent-kit' MCP tools, or: kiro-cli --agent agent-kit")
    typer.echo("  3. Read docs/kiro-integration.md for hook and steering details.")


@kiro_app.command("status")
def status_command(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
) -> None:
    """Show which managed .kiro files are present or missing."""
    ok = show_status([KIRO], project)
    raise typer.Exit(code=0 if ok else 1)


@kiro_app.command("uninstall")
def uninstall_command(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Remove the managed .kiro files (your own files are kept)."""
    uninstall_integrations([KIRO], project, assume_yes=yes)
