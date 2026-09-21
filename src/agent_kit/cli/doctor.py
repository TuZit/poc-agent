"""``agent-kit doctor`` — validate the agent environment.

Checks: Python version, configuration file, model configuration, required
environment variables, optional provider dependencies, enabled tools, skills and
workflow. Every failure carries an actionable hint.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import typer

from agent_kit.cli.common import FAIL_MARK, OK_MARK, info, relative_to
from agent_kit.config import ConfigError, default_config_path, load_config
from agent_kit.model import available_providers, required_env_vars
from agent_kit.skills import SkillError, SkillLoader
from agent_kit.tools import create_enabled_tools
from agent_kit.tools.base import ToolError
from agent_kit.workflow import available_workflows

MIN_PYTHON = (3, 11)


class _Report:
    """Collects check results and renders the doctor report."""

    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str, str]] = []

    def check(self, label: str, passed: bool, hint: str = "", note: str = "") -> None:
        """Record a check.

        Args:
            label: what is being checked.
            passed: the result.
            hint: actionable advice, shown only when the check fails.
            note: informational suffix, shown only when the check passes.
        """
        self.checks.append((label, passed, hint, note))

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _, _ in self.checks)

    def render(self) -> str:
        lines = ["Agent Kit Doctor", ""]
        for label, ok, hint, note in self.checks:
            mark = OK_MARK if ok else FAIL_MARK
            if ok:
                suffix = f" ({note})" if note else ""
            else:
                suffix = f" — {hint}" if hint else ""
            lines.append(f"{mark} {label}{suffix}")
        lines.append("")
        if self.passed:
            lines.append("Agent environment is ready.")
        else:
            failures = sum(1 for _, ok, _, _ in self.checks if not ok)
            lines.append(
                f"Agent environment is NOT ready ({failures} problem(s)). "
                "Fix the items marked ✗ and run 'agent-kit doctor' again."
            )
        return "\n".join(lines)


def doctor_command(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
) -> None:
    """Check that this project can run the agent."""
    report = _Report()

    # 1. Python version ----------------------------------------------------
    version = sys.version_info
    python_ok = (version.major, version.minor) >= MIN_PYTHON
    report.check(
        f"Python 3.11+ ({version.major}.{version.minor}.{version.micro})",
        python_ok,
        "install Python 3.11 or newer (uv python install 3.12)",
    )

    # 2. Configuration file -------------------------------------------------
    config_path = default_config_path(project)
    config_exists = config_path.is_file()
    report.check(
        f"Configuration ({relative_to(config_path, Path(project))})",
        config_exists,
        "run 'agent-kit init <project>' to create .agent/config.yaml",
    )

    config = None
    if config_exists:
        try:
            config = load_config(project)
        except ConfigError as exc:
            report.check("Configuration is valid", False, str(exc))
        else:
            report.check("Configuration is valid", True)

    if config is not None:
        # 3. Model configuration -------------------------------------------
        provider = config.model.provider
        known = provider in available_providers()
        report.check(
            f"Model configuration ({provider}/{config.model.name})",
            known,
            f"unknown provider; available: {', '.join(available_providers())}",
        )

        env_vars = required_env_vars(provider)
        if not env_vars:
            report.check(
                "OPENAI_API_KEY",
                True,
                note=f"not required for provider '{provider}'",
            )
        for var in env_vars:
            present = bool(os.environ.get(var))
            report.check(
                var,
                present,
                f"{var} is not set — export it (see .env.example) or use model.provider: mock",
            )

        if provider == "openai":
            installed = importlib.util.find_spec("openai") is not None
            report.check(
                "openai package installed",
                installed,
                "install with: uv tool install 'agent-kit-poc[openai]' --force",
            )

        # 4. Tools ----------------------------------------------------------
        try:
            tools = create_enabled_tools(config.tools, config.project_root)
        except ToolError as exc:
            report.check("Tools", False, str(exc))
        else:
            names = ", ".join(tool.name for tool in tools) or "none enabled"
            report.check(f"Tools ({names})", True)

        # 5. Skills ---------------------------------------------------------
        loader = SkillLoader(project_root=config.project_root)
        if not config.skills:
            report.check("Skills (none configured)", True)
        for name in config.skills:
            try:
                loader.load(name)
            except SkillError as exc:
                report.check(f"Skill '{name}'", False, str(exc))
            else:
                report.check(f"Skill '{name}'", True)

        # 6. Workflow -------------------------------------------------------
        workflow_ok = config.workflow.name in available_workflows()
        report.check(
            f"Workflow '{config.workflow.name}'",
            workflow_ok,
            f"unknown workflow; available: {', '.join(available_workflows())}",
        )

    info(report.render())
    raise typer.Exit(code=0 if report.passed else 1)
