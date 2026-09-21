"""``agent-kit kiro`` — install and inspect the Kiro integration."""

from __future__ import annotations

from pathlib import Path

import typer

from agent_kit.cli.common import fail, info, relative_to

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
    from agent_kit.integrations.kiro import KiroIntegrationError, install_kiro

    root = Path(project).resolve()
    if not (root / ".agent" / "config.yaml").is_file():
        info(
            "! No .agent/config.yaml found — run 'agent-kit init' first so the MCP tools "
            "have a project to operate on."
        )

    try:
        written = install_kiro(root, force=force, agent_kit_command=command)
    except KiroIntegrationError as exc:
        fail(str(exc))

    info(f"✓ Kiro integration installed in {relative_to(root / '.kiro', root)}")
    for path in written:
        info(f"  + {relative_to(path, root)}")
    info("")
    info("Next steps:")
    info("  1. Open this folder in Kiro (or run 'kiro-cli' here).")
    info("  2. Use the 'agent-kit' MCP tools, or the custom agent: kiro-cli --agent agent-kit")
    info("  3. Read docs/kiro-integration.md for the hook and steering details.")


@kiro_app.command("status")
def status_command(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
) -> None:
    """Show which managed .kiro files are present or missing."""
    from agent_kit.integrations.kiro import kiro_status

    root = Path(project).resolve()
    present, missing = kiro_status(root)

    info("Kiro integration status")
    info("")
    for path in present:
        info(f"✓ {relative_to(path, root)}")
    for path in missing:
        info(f"✗ {relative_to(path, root)}")
    info("")
    if missing:
        info("Run 'agent-kit kiro install' to create the missing files.")
        raise typer.Exit(code=1)
    info("Kiro integration is complete.")


@kiro_app.command("uninstall")
def uninstall_command(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Remove the managed .kiro files (your own files in .kiro/ are kept)."""
    from agent_kit.integrations.kiro import kiro_status, uninstall_kiro

    root = Path(project).resolve()
    present, _ = kiro_status(root)
    if not present:
        info("Nothing to remove: no managed Kiro files found.")
        return
    if not yes:
        typer.confirm(f"Remove {len(present)} managed file(s) under .kiro/?", abort=True)

    removed = uninstall_kiro(root)
    info(f"✓ Removed {len(removed)} file(s).")
