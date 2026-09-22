"""Project scaffolding: render and copy bundled templates.

Used by ``agent-kit init`` and by assistant integrations (``agent-kit kiro``).
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path

from agent_kit.paths import AssetError, samples_dir, templates_dir

#: Template directory copied by ``agent-kit init``.
DEFAULT_PROJECT_TEMPLATE = "project"

#: File types whose ``{{PLACEHOLDER}}`` tokens are substituted.
TEXT_SUFFIXES = frozenset({".md", ".yaml", ".yml", ".json", ".txt", ".template", ".hook"})

#: Marker used in templates, e.g. ``{{PROJECT_NAME}}``.
PLACEHOLDER_PATTERN = "{{%s}}"


class ScaffoldError(RuntimeError):
    """Raised when scaffolding cannot proceed."""


def render(text: str, mapping: dict[str, str]) -> str:
    """Replace ``{{KEY}}`` placeholders with values from ``mapping``."""
    rendered = text
    for key, value in mapping.items():
        rendered = rendered.replace(PLACEHOLDER_PATTERN % key, value)
    return rendered


def copy_tree(
    source: Path,
    target: Path,
    mapping: dict[str, str] | None = None,
    preserve: Iterable[str] = (),
) -> list[Path]:
    """Copy ``source`` into ``target``, rendering text files.

    Args:
        mapping: ``{{PLACEHOLDER}}`` values.
        preserve: relative paths (POSIX form) that must never be overwritten when
            they already exist, even with ``force``. Used for files a real project
            already owns, such as ``README.md``.

    Returns:
        The list of files written.
    """
    mapping = mapping or {}
    keep = set(preserve)
    if not source.is_dir():
        raise ScaffoldError(f"Template directory not found: {source}")

    written: list[Path] = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        destination = target / relative

        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue

        if relative.as_posix() in keep and destination.exists():
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix in TEXT_SUFFIXES:
            destination.write_text(
                render(path.read_text(encoding="utf-8"), mapping),
                encoding="utf-8",
            )
        else:
            shutil.copy2(path, destination)
        written.append(destination)
    return written


def ensure_writable_target(target: Path, force: bool = False) -> None:
    """Refuse to clobber a non-empty directory unless ``force`` is set."""
    if not target.exists():
        return
    if not target.is_dir():
        raise ScaffoldError(f"{target} exists and is not a directory.")
    contents = [item for item in target.iterdir() if item.name != ".DS_Store"]
    if contents and not force:
        raise ScaffoldError(
            f"{target} already exists and is not empty. "
            "Use --force to overwrite, or choose another directory."
        )


#: Template files that must never overwrite a file the project already has.
#: Adopting agent-kit in an existing repository must not replace its README.
PRESERVED_PROJECT_FILES: tuple[str, ...] = ("README.md",)


def init_project(
    target: Path | str,
    force: bool = False,
    template: str = DEFAULT_PROJECT_TEMPLATE,
    include_samples: bool = True,
    preserve: Iterable[str] = PRESERVED_PROJECT_FILES,
) -> list[Path]:
    """Create a new agent-kit project from the bundled template.

    ``preserve`` lists template files that are skipped when they already exist
    (default: ``README.md``), so ``init --force`` inside an existing repository
    adds ``.agent/config.yaml`` without clobbering the project's own README.
    """
    target_path = Path(target)
    ensure_writable_target(target_path, force=force)

    template_root = templates_dir() / template
    mapping = {"PROJECT_NAME": target_path.resolve().name}

    written = copy_tree(template_root, target_path, mapping, preserve=preserve)
    if include_samples:
        try:
            written += copy_tree(samples_dir(), target_path / "samples", mapping)
        except AssetError:  # pragma: no cover - samples are shipped with the package
            pass
    return written
