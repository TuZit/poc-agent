"""Unit tests for project scaffolding."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_kit.paths import samples_dir, templates_dir
from agent_kit.scaffold import (
    ScaffoldError,
    copy_tree,
    ensure_writable_target,
    init_project,
    render,
)


def test_render_replaces_placeholders() -> None:
    assert render("name: {{PROJECT_NAME}}", {"PROJECT_NAME": "demo"}) == "name: demo"
    assert render("{{MISSING}}", {"OTHER": "x"}) == "{{MISSING}}"


def test_bundled_assets_exist() -> None:
    assert (templates_dir() / "project" / ".agent" / "config.yaml").is_file()
    assert (samples_dir() / "requirement-analysis" / "input" / "sample-001.md").is_file()


def test_copy_tree_renders_text_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("# {{PROJECT_NAME}}", encoding="utf-8")
    bundle = source / "binary.bin"
    bundle.write_bytes(b"\x00\x01")

    written = copy_tree(source, tmp_path / "target", {"PROJECT_NAME": "demo"})

    assert (tmp_path / "target" / "README.md").read_text(encoding="utf-8") == "# demo"
    assert (tmp_path / "target" / "binary.bin").read_bytes() == b"\x00\x01"
    assert len(written) == 2


def test_copy_tree_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(ScaffoldError, match="not found"):
        copy_tree(tmp_path / "nope", tmp_path / "target")


def test_ensure_writable_target_blocks_non_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "existing.md").write_text("x", encoding="utf-8")
    with pytest.raises(ScaffoldError, match="already exists"):
        ensure_writable_target(tmp_path)
    ensure_writable_target(tmp_path, force=True)  # does not raise


def test_ensure_writable_target_rejects_a_file(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("x", encoding="utf-8")
    with pytest.raises(ScaffoldError, match="not a directory"):
        ensure_writable_target(path)


def test_init_project_creates_expected_files(tmp_path: Path) -> None:
    target = tmp_path / "my-project"

    written = init_project(target)

    assert (target / ".agent" / "config.yaml").is_file()
    assert (target / "README.md").is_file()
    assert (target / "samples" / "requirement-analysis" / "input" / "sample-001.md").is_file()
    assert (target / "samples" / "requirement-analysis" / "expected" / "sample-001.md").is_file()
    assert len(written) == 4


def test_init_project_substitutes_project_name(tmp_path: Path) -> None:
    target = tmp_path / "named-project"

    init_project(target)

    assert "name: named-project" in (target / ".agent" / "config.yaml").read_text(encoding="utf-8")
    assert "# named-project" in (target / "README.md").read_text(encoding="utf-8")


def test_init_project_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    target = tmp_path / "my-project"
    init_project(target)
    (target / ".agent" / "config.yaml").write_text("custom\n", encoding="utf-8")

    with pytest.raises(ScaffoldError):
        init_project(target)

    assert (target / ".agent" / "config.yaml").read_text(encoding="utf-8") == "custom\n"


def test_init_project_force_restores_template(tmp_path: Path) -> None:
    target = tmp_path / "my-project"
    init_project(target)
    (target / ".agent" / "config.yaml").write_text("custom\n", encoding="utf-8")

    init_project(target, force=True)

    assert "provider: openai" in (target / ".agent" / "config.yaml").read_text(encoding="utf-8")
