"""Skill discovery and loading.

Lookup order (first match wins, so projects can override shipped skills):

1. ``<project>/.agent/skills/<name>/SKILL.md`` — project-local skill
2. ``<bundled>/skills/<name>/SKILL.md``       — shipped with agent-kit

The loader validates that the file exists and is non-empty before handing the
instructions to the agent.
"""

from __future__ import annotations

from pathlib import Path

from agent_kit.paths import AssetError, skills_dir
from agent_kit.skills.base import SKILL_FILE_NAME, Skill


class SkillError(Exception):
    """Raised when a skill cannot be found or is invalid."""


def project_skills_dir(project_root: Path | str) -> Path:
    return Path(project_root) / ".agent" / "skills"


def default_search_paths(project_root: Path | str | None = None) -> list[Path]:
    """Search paths in priority order."""
    paths: list[Path] = []
    if project_root is not None:
        paths.append(project_skills_dir(project_root))
    try:
        paths.append(skills_dir())
    except AssetError:  # pragma: no cover - only when assets are missing
        pass
    return paths


class SkillLoader:
    """Discovers and loads skills from :data:`SKILL_FILE_NAME` files."""

    def __init__(
        self,
        search_paths: list[Path] | None = None,
        project_root: Path | str | None = None,
    ) -> None:
        if search_paths is None:
            search_paths = (
                default_search_paths(project_root) if project_root is not None else [skills_dir()]
            )
        self.search_paths = [Path(path) for path in search_paths]

    # -- discovery ---------------------------------------------------------
    def discover(self) -> list[str]:
        """Names of every skill visible in the search paths."""
        names: list[str] = []
        for base in self.search_paths:
            if not base.is_dir():
                continue
            for skill_file in sorted(base.glob(f"*/{SKILL_FILE_NAME}")):
                name = skill_file.parent.name
                if name not in names:
                    names.append(name)
        return names

    def find(self, name: str) -> Path:
        """Return the ``SKILL.md`` path for ``name`` or raise :class:`SkillError`."""
        for base in self.search_paths:
            candidate = base / name / SKILL_FILE_NAME
            if candidate.is_file():
                return candidate
        available = ", ".join(self.discover()) or "(none)"
        searched = ", ".join(str(path) for path in self.search_paths) or "(no search paths)"
        raise SkillError(
            f"Skill '{name}' not found. Searched: {searched}. Available skills: {available}."
        )

    # -- loading -----------------------------------------------------------
    def load(self, name: str) -> Skill:
        """Load and validate one skill."""
        skill_file = self.find(name)
        try:
            instructions = skill_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise SkillError(f"Cannot read skill '{name}' at {skill_file}: {exc}") from exc
        if not instructions.strip():
            raise SkillError(f"Skill '{name}' is invalid: {skill_file} is empty.")
        return Skill(name=name, instructions=instructions.strip(), path=skill_file.parent)

    def load_all(self, names: list[str]) -> list[Skill]:
        return [self.load(name) for name in names]
