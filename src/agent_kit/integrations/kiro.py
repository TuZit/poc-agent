"""Kiro integration.

Generates the workspace files Kiro needs to use agent-kit as a first-class tool:

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

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from agent_kit.paths import AssetError, integrations_dir
from agent_kit.scaffold import render

#: Directory Kiro reads from inside a workspace.
KIRO_DIR_NAME = ".kiro"

#: Spec folder created inside ``.kiro/specs``.
KIRO_SPEC_NAME = "agent-kit-poc"

#: Placeholders substituted in the integration templates.
TEMPLATE_VALUES = {
    "AGENT_KIT_COMMAND": "agent-kit",
    "DEFAULT_INPUT": "samples/requirement-analysis/input/sample-001.md",
    "DEFAULT_OUTPUT": "output/sample-001.md",
}


class KiroIntegrationError(RuntimeError):
    """Raised when the Kiro integration cannot be installed."""


@dataclass(frozen=True)
class KiroInstallResult:
    """Outcome of an install/uninstall operation."""

    written: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    removed: list[Path] = field(default_factory=list)

    @property
    def files(self) -> list[Path]:
        return list(self.written)


def kiro_template_dir() -> Path:
    """Directory holding the Kiro integration templates."""
    try:
        return integrations_dir() / "kiro"
    except AssetError as exc:  # pragma: no cover - packaging failure
        raise KiroIntegrationError(str(exc)) from exc


def expected_kiro_files(project_root: Path | str) -> list[Path]:
    """Project-relative paths this integration manages."""
    root = Path(project_root)
    template = kiro_template_dir()
    files = [
        root / KIRO_DIR_NAME / path.relative_to(template)
        for path in sorted(template.rglob("*"))
        if path.is_file()
    ]
    files.append(root / KIRO_DIR_NAME / "specs" / KIRO_SPEC_NAME / ".config.kiro")
    return files


def _write_spec_config(project_root: Path, force: bool) -> Path | None:
    """Write Kiro's per-spec metadata file with a fresh spec id."""
    spec_config = project_root / KIRO_DIR_NAME / "specs" / KIRO_SPEC_NAME / ".config.kiro"
    if spec_config.exists() and not force:
        return None
    spec_config.parent.mkdir(parents=True, exist_ok=True)
    spec_config.write_text(
        "{\n"
        f'  "specId": "{uuid.uuid4()}",\n'
        '  "workflowType": "requirements-first",\n'
        '  "specType": "feature"\n'
        "}\n",
        encoding="utf-8",
    )
    return spec_config


def install_kiro(
    project_root: Path | str,
    force: bool = False,
    agent_kit_command: str = "agent-kit",
) -> list[Path]:
    """Render the Kiro integration into ``<project>/.kiro``.

    Existing files are left untouched unless ``force`` is set, so a project can
    customise its steering and hooks without losing them on re-install.

    Returns the list of paths written.
    """
    root = Path(project_root).resolve()
    template = kiro_template_dir()
    if not template.is_dir():  # pragma: no cover - packaging failure
        raise KiroIntegrationError(f"Kiro templates not found at {template}.")

    mapping = {
        **TEMPLATE_VALUES,
        "AGENT_KIT_COMMAND": agent_kit_command,
        "PROJECT_NAME": root.name,
    }

    result = _install_tree(template, root / KIRO_DIR_NAME, mapping, force=force)

    spec_config = _write_spec_config(root, force=force)
    if spec_config is not None:
        result.written.append(spec_config)
    else:
        result.skipped.append(root / KIRO_DIR_NAME / "specs" / KIRO_SPEC_NAME / ".config.kiro")

    return sorted(result.written)


def _install_tree(
    source: Path,
    target: Path,
    mapping: dict[str, str],
    force: bool,
) -> KiroInstallResult:
    result = KiroInstallResult()
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        destination = target / relative

        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue

        if destination.exists() and not force:
            result.skipped.append(destination)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            render(path.read_text(encoding="utf-8"), mapping),
            encoding="utf-8",
        )
        result.written.append(destination)
    return result


def uninstall_kiro(project_root: Path | str) -> list[Path]:
    """Remove the files this integration manages, then prune empty directories."""
    root = Path(project_root).resolve()
    removed: list[Path] = []
    for path in expected_kiro_files(root):
        if path.is_file():
            path.unlink()
            removed.append(path)

    kiro_dir = root / KIRO_DIR_NAME
    if kiro_dir.is_dir():
        # Deepest first so parents become empty and can be pruned.
        for directory in sorted(
            (item for item in kiro_dir.rglob("*") if item.is_dir()),
            key=lambda item: len(item.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass  # not empty: user content stays
        try:
            kiro_dir.rmdir()
        except OSError:
            pass
    return removed


def kiro_status(project_root: Path | str) -> tuple[list[Path], list[Path]]:
    """Return ``(present, missing)`` for the managed Kiro files."""
    root = Path(project_root)
    present: list[Path] = []
    missing: list[Path] = []
    for path in expected_kiro_files(root):
        (present if path.is_file() else missing).append(path)
    return present, missing


__all__ = [
    "KIRO_DIR_NAME",
    "KIRO_SPEC_NAME",
    "KiroInstallResult",
    "KiroIntegrationError",
    "expected_kiro_files",
    "install_kiro",
    "kiro_status",
    "kiro_template_dir",
    "uninstall_kiro",
]
