"""Kiro integration.

Generates the workspace files Kiro reads:

    .kiro/steering/*.md           project context always available to the agent
    .kiro/hooks/*.json            v1 hooks: evaluate on save, manual run, env context
    .kiro/settings/mcp.json       registers ``agent-kit mcp serve`` as an MCP server
    .kiro/agents/agent-kit.json   a custom Kiro agent wired to the MCP tools
    .kiro/specs/agent-kit-poc/    requirements / design / tasks in Kiro's spec format
    .kiro/prompts/agent-kit.*.md  file-based prompts (as Spec Kit's kiro-cli integration does)

Format notes (verified against kiro.dev docs):

* Steering files are Markdown with optional YAML frontmatter (``inclusion``:
  ``always`` | ``fileMatch`` | ``manual`` | ``auto``).
* Hooks use the current ``v1`` schema: ``.kiro/hooks/<name>.json`` containing
  ``{"version": "v1", "hooks": [{"name", "trigger", "matcher", "action"}]}``.
  The legacy ``*.kiro.hook`` (``when``/``then``) format is *not* generated.
* MCP servers are registered in ``.kiro/settings/mcp.json`` under ``mcpServers``.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from agent_kit.integrations.base import (
    IntegrationError,
    IntegrationStatus,
    TemplateIntegration,
)

#: Directory Kiro reads from inside a workspace.
KIRO_DIR_NAME = ".kiro"

#: Spec folder created inside ``.kiro/specs``.
KIRO_SPEC_NAME = "agent-kit-poc"

#: Kiro's per-spec metadata file (relative to ``.kiro/``), generated with a fresh id.
SPEC_CONFIG_RELATIVE = f"specs/{KIRO_SPEC_NAME}/.config.kiro"

#: Backwards-compatible alias (the generic error type).
KiroIntegrationError = IntegrationError


class KiroIntegration(TemplateIntegration):
    """Kiro: steering, hooks, MCP registration, custom agent, prompts, specs."""

    name = "kiro"
    title = "Kiro"
    description = (
        "steering + v1 hooks + MCP server + custom agent + prompts + EARS spec "
        "(.kiro/)"
    )
    template_dir_name = "kiro"
    code_generated_files = (SPEC_CONFIG_RELATIVE,)

    def destination_root(self, project_root: Path) -> Path:
        """Kiro reads everything from ``.kiro/`` in the workspace."""
        return project_root / KIRO_DIR_NAME

    def extra_files(self, project_root: Path, force: bool, command: str) -> list[Path]:
        """Write Kiro's ``.config.kiro`` with a generated spec id."""
        spec_config = self.destination_root(project_root) / SPEC_CONFIG_RELATIVE
        if spec_config.exists() and not force:
            return []
        spec_config.parent.mkdir(parents=True, exist_ok=True)
        spec_config.write_text(
            json.dumps(
                {
                    "specId": str(uuid.uuid4()),
                    "workflowType": "requirements-first",
                    "specType": "feature",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return [spec_config]


#: Shared instance used by the CLI, the registry and the compatibility helpers.
KIRO = KiroIntegration()


# --- backwards-compatible functional API ----------------------------------
def kiro_template_dir() -> Path:
    """Directory holding the Kiro integration templates."""
    return KIRO.template_dir()


def expected_kiro_files(project_root: Path | str) -> list[Path]:
    """Project-relative paths this integration manages."""
    return KIRO.managed_files(Path(project_root))


def install_kiro(
    project_root: Path | str,
    force: bool = False,
    agent_kit_command: str = "agent-kit",
) -> list[Path]:
    """Render the Kiro integration into ``<project>/.kiro``.

    Existing files are left untouched unless ``force`` is set, so a project can
    customise its steering and hooks without losing them on re-install.
    """
    return KIRO.install(project_root, force=force, command=agent_kit_command)


def uninstall_kiro(project_root: Path | str) -> list[Path]:
    """Remove the managed Kiro files and prune emptied directories."""
    return KIRO.uninstall(project_root)


def kiro_status(project_root: Path | str) -> tuple[list[Path], list[Path]]:
    """Return ``(present, missing)`` for the managed Kiro files."""
    status: IntegrationStatus = KIRO.status(project_root)
    return status.present, status.missing


__all__ = [
    "KIRO",
    "KIRO_DIR_NAME",
    "KIRO_SPEC_NAME",
    "SPEC_CONFIG_RELATIVE",
    "KiroIntegration",
    "KiroIntegrationError",
    "expected_kiro_files",
    "install_kiro",
    "kiro_status",
    "kiro_template_dir",
    "uninstall_kiro",
]
