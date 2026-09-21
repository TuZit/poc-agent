"""``agent-kit integration`` — install agent-tool integrations.

One command group serves every registered integration; this phase ships Kiro.
``agent-kit kiro ...`` remains as a shorthand alias for it, and adding another
tool later needs no change here (see ``docs/agent-integrations.md``).
"""

from __future__ import annotations

from pathlib import Path

import typer

from agent_kit.cli.common import fail, info, relative_to
from agent_kit.integrations import (
    IntegrationError,
    available_integrations,
    get_integration,
    integration_descriptions,
    resolve_integrations,
)


def install_integrations(
    values: str | list[str],
    project: Path,
    force: bool = False,
    command: str = "agent-kit",
) -> list[Path]:
    """Install one or more integrations, printing a per-integration report."""
    root = Path(project).resolve()
    if not (root / ".agent" / "config.yaml").is_file():
        info(
            "! No .agent/config.yaml found — run 'agent-kit init' first so the MCP tools "
            "have a project to operate on."
        )

    try:
        integrations = resolve_integrations(values)
    except IntegrationError as exc:
        fail(str(exc))

    written: list[Path] = []
    for integration in integrations:
        try:
            files = integration.install(root, force=force, command=command)
        except IntegrationError as exc:
            fail(str(exc))
        info(f"✓ {integration.title} integration — {len(files)} file(s)")
        for path in files:
            info(f"  + {relative_to(path, root)}")
        written.extend(files)

    if written:
        info("")
        info("Next steps:")
        info("  1. Open this folder in your AI tool.")
        info("  2. The agent-kit MCP tools become available (see docs/agent-integrations.md).")
    return written


def show_status(values: str | list[str] | None, project: Path) -> bool:
    """Print status for the requested integrations (all when ``values`` is None)."""
    root = Path(project).resolve()
    try:
        integrations = (
            resolve_integrations(values)
            if values
            else [get_integration(name) for name in available_integrations()]
        )
    except IntegrationError as exc:
        fail(str(exc))

    info("Agent-tool integration status")
    info("")
    all_installed = True
    for integration in integrations:
        status = integration.status(root)
        info(f"{integration.title} ({integration.name})")
        for path in status.present:
            info(f"  ✓ {relative_to(path, root)}")
        for path in status.missing:
            info(f"  ✗ {relative_to(path, root)}")
        if not status.installed:
            all_installed = False
            info(f"  → run: agent-kit integration install {integration.name}")
        info("")

    if all_installed:
        info("All requested integrations are complete.")
    return all_installed


def uninstall_integrations(values: str | list[str], project: Path, assume_yes: bool) -> int:
    """Remove managed files for the requested integrations."""
    root = Path(project).resolve()
    try:
        integrations = resolve_integrations(values)
    except IntegrationError as exc:
        fail(str(exc))

    managed = sum(len(integration.status(root).present) for integration in integrations)
    if managed == 0:
        info("Nothing to remove: no managed files found.")
        return 0
    if not assume_yes:
        typer.confirm(f"Remove {managed} managed file(s)?", abort=True)

    removed = 0
    for integration in integrations:
        files = integration.uninstall(root)
        removed += len(files)
        info(f"✓ {integration.title}: removed {len(files)} file(s)")
    return removed


integration_app = typer.Typer(
    help="Install agent-tool integrations (registered: see 'agent-kit integration list').",
    no_args_is_help=True,
)


@integration_app.command("list")
def list_command(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
) -> None:
    """List the supported integrations and whether they are installed here."""
    root = Path(project).resolve()
    info("Available agent-tool integrations")
    info("")
    for name, title, description in integration_descriptions():
        status = resolve_integrations([name])[0].status(root)
        mark = "✓ installed" if status.installed else "— not installed"
        info(f"{name:<10} {title:<14} {mark}")
        if description:
            info(f"{'':<10} {description}")
    info("")
    info("Install with: agent-kit integration install <name>[,<name>...]")


@integration_app.command("install")
def install_command(
    name: str = typer.Argument(
        ...,
        help="Integration name(s), comma-separated, e.g. 'kiro,claude'. Use 'all' for everything.",
    ),
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing files (default: keep them)."
    ),
    command: str = typer.Option(
        "agent-kit", "--command", help="Command the AI tool should use to reach agent-kit."
    ),
) -> None:
    """Write the files an AI coding tool needs (steering, MCP, prompts, hooks)."""
    requested = available_integrations() if name.strip().lower() == "all" else name
    install_integrations(requested, project, force=force, command=command)


@integration_app.command("status")
def status_command(
    name: str | None = typer.Argument(
        None, help="Integration name(s). Omit to check every integration."
    ),
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
) -> None:
    """Show which managed files are present or missing."""
    ok = show_status(name, project)
    raise typer.Exit(code=0 if ok else 1)


@integration_app.command("uninstall")
def uninstall_command(
    name: str = typer.Argument(..., help="Integration name(s), comma-separated."),
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Remove the managed files (your own files are kept)."""
    uninstall_integrations(name, project, assume_yes=yes)


__all__ = [
    "install_integrations",
    "integration_app",
    "show_status",
    "uninstall_integrations",
]
