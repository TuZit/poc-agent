"""Unit tests for skill discovery and loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_kit.skills import SKILL_FILE_NAME, SkillError, SkillLoader

SKILL_BODY = """\
# Custom Skill

## Purpose

Do the custom thing.
"""


def _write_skill(root: Path, name: str, body: str) -> Path:
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / SKILL_FILE_NAME).write_text(body, encoding="utf-8")
    return directory


def test_loads_bundled_skill(tmp_path: Path) -> None:
    loader = SkillLoader(project_root=tmp_path)

    skill = loader.load("requirement-analysis")

    assert skill.name == "requirement-analysis"
    assert "# Requirement Analysis" in skill.instructions
    assert skill.templates_dir is not None
    assert (skill.templates_dir / "requirement-summary.md").is_file()


def test_discover_lists_bundled_skills(tmp_path: Path) -> None:
    loader = SkillLoader(project_root=tmp_path)
    assert "requirement-analysis" in loader.discover()


def test_project_local_skill_takes_precedence(tmp_path: Path) -> None:
    local_root = tmp_path / ".agent" / "skills"
    _write_skill(local_root, "requirement-analysis", SKILL_BODY)

    skill = SkillLoader(project_root=tmp_path).load("requirement-analysis")

    assert "Do the custom thing." in skill.instructions
    assert skill.path == local_root / "requirement-analysis"


def test_project_local_only_skill_is_found(tmp_path: Path) -> None:
    _write_skill(tmp_path / ".agent" / "skills", "my-skill", SKILL_BODY)

    skill = SkillLoader(project_root=tmp_path).load("my-skill")

    assert skill.name == "my-skill"
    assert "my-skill" in SkillLoader(project_root=tmp_path).discover()


def test_missing_skill_lists_alternatives(tmp_path: Path) -> None:
    loader = SkillLoader(project_root=tmp_path)

    with pytest.raises(SkillError) as excinfo:
        loader.load("does-not-exist")

    message = str(excinfo.value)
    assert "does-not-exist" in message
    assert "requirement-analysis" in message  # available skills are listed


def test_empty_skill_file_is_rejected(tmp_path: Path) -> None:
    _write_skill(tmp_path / ".agent" / "skills", "broken", "   \n")

    with pytest.raises(SkillError, match="empty"):
        SkillLoader(project_root=tmp_path).load("broken")


def test_load_all_returns_configured_skills(tmp_path: Path) -> None:
    _write_skill(tmp_path / ".agent" / "skills", "my-skill", SKILL_BODY)
    loader = SkillLoader(project_root=tmp_path)

    skills = loader.load_all(["my-skill", "requirement-analysis"])

    assert [skill.name for skill in skills] == ["my-skill", "requirement-analysis"]


def test_custom_search_paths_are_honoured(tmp_path: Path) -> None:
    custom = tmp_path / "elsewhere"
    _write_skill(custom, "custom-skill", SKILL_BODY)

    loader = SkillLoader(search_paths=[custom])

    assert loader.discover() == ["custom-skill"]
    assert loader.load("custom-skill").name == "custom-skill"
