"""Command line interface for Agent Kit POC.

    agent-kit init <project> [--ai kiro]
    agent-kit doctor
    agent-kit config show|get|set
    agent-kit run [--input FILE] [--output FILE]
    agent-kit evaluate <output-file>
    agent-kit kiro install|status
    agent-kit mcp serve

Every command is a thin shell around the runtime in
:mod:`agent_kit.agent.runtime`; the CLI holds no agent logic of its own.
"""

from __future__ import annotations

import typer

from agent_kit import __version__
from agent_kit.cli.config import config_app
from agent_kit.cli.doctor import doctor_command
from agent_kit.cli.evaluate import evaluate_command
from agent_kit.cli.init import init_command
from agent_kit.cli.run import run_command

app = typer.Typer(
    name="agent-kit",
    help="Agent Kit POC — installable, configuration-driven AI agent kit.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"agent-kit {__version__}")
        raise typer.Exit(code=0)


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the agent-kit version and exit.",
    ),
) -> None:
    """Agent Kit POC command line interface."""


app.command("init", help="Create a new agent-kit project from the bundled template.")(init_command)
app.command("doctor", help="Validate configuration, model, tools, skills and environment.")(
    doctor_command
)
app.command("run", help="Run the configured workflow and write the output file.")(run_command)
app.command("evaluate", help="Deterministically evaluate a generated output file.")(
    evaluate_command
)
app.add_typer(config_app, name="config")


def _register_optional_commands() -> None:
    """Register integrations that may be unavailable in a slim installation."""
    try:
        from agent_kit.cli.kiro import kiro_app
    except ImportError:  # pragma: no cover - integration module always ships
        return
    app.add_typer(kiro_app, name="kiro")

    try:
        from agent_kit.cli.mcp import mcp_app
    except ImportError:  # pragma: no cover
        return
    app.add_typer(mcp_app, name="mcp")


_register_optional_commands()


def main() -> None:  # pragma: no cover - console-script convenience
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
