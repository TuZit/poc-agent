"""Skill data model.

A skill is a directory containing ``SKILL.md``. Instructions live in Markdown
on disk — never hard-coded in Python — so skills can be packaged, versioned and
shipped separately from the runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: Required file inside every skill directory.
SKILL_FILE_NAME = "SKILL.md"


@dataclass(frozen=True)
class Skill:
    """A loaded skill."""

    name: str
    instructions: str
    path: Path

    @property
    def directory(self) -> Path:
        return self.path

    @property
    def templates_dir(self) -> Path | None:
        """Optional ``templates/`` directory shipped next to ``SKILL.md``."""
        candidate = self.path / "templates"
        return candidate if candidate.is_dir() else None

    def describe(self) -> str:
        return f"{self.name} ({self.path})"
