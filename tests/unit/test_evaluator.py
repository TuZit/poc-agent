"""Unit tests for the deterministic evaluator."""

from __future__ import annotations

from pathlib import Path

from agent_kit.evaluation import (
    REQUIRED_SECTIONS,
    SAMPLE_SECTIONS,
    evaluate_file,
    evaluate_text,
    extract_sections,
    find_missing_concepts,
    find_missing_sections,
)
from agent_kit.model.mock import MOCK_REQUIREMENT_SUMMARY

GOOD_OUTPUT = """\
# Requirement Summary

## Objective

Ship something useful.

## Actors

- User

## Functional Requirements

1. Do the thing

## Non-Functional Requirements

- Fast

## Assumptions

- None

## Open Questions

- When?
"""


def test_extract_sections_is_case_and_level_agnostic() -> None:
    text = "# Title\n\n## Objective\n\n### ACTORS\n\n#### no-trailing-hash ##\n"
    sections = extract_sections(text)
    assert {"title", "objective", "actors", "no-trailing-hash"} <= sections


def test_good_output_passes_every_check() -> None:
    result = evaluate_text(GOOD_OUTPUT)

    assert result.passed is True
    assert result.failed_checks == []
    assert [check.name for check in result.checks] == ["Output generated", *REQUIRED_SECTIONS]


def test_missing_section_fails_and_is_named() -> None:
    result = evaluate_text(GOOD_OUTPUT.replace("## Actors", "## People"))

    assert result.passed is False
    assert [check.name for check in result.failed_checks] == ["Actors"]
    assert "missing section 'Actors'" in result.failed_checks[0].detail


def test_empty_output_fails() -> None:
    result = evaluate_text("   \n")

    assert result.passed is False
    assert result.checks[0].name == "Output generated"
    assert "empty" in result.checks[0].detail


def test_required_concepts_are_checked() -> None:
    result = evaluate_text(
        GOOD_OUTPUT, required_concepts=("Do the thing", "search product")
    )

    assert result.passed is False
    assert [check.name for check in result.failed_checks] == ["Concept: search product"]


def test_mock_summary_satisfies_sample_sections() -> None:
    result = evaluate_text(MOCK_REQUIREMENT_SUMMARY, required_sections=SAMPLE_SECTIONS)
    assert result.passed is True


def test_evaluate_missing_file_fails_cleanly(tmp_path: Path) -> None:
    result = evaluate_file(tmp_path / "nope.md")

    assert result.passed is False
    assert "file not found" in result.checks[0].detail


def test_evaluate_file_reads_content(tmp_path: Path) -> None:
    path = tmp_path / "output.md"
    path.write_text(GOOD_OUTPUT, encoding="utf-8")

    result = evaluate_file(path)

    assert result.passed is True
    assert result.source == str(path)


def test_render_reports_pass_and_fail(tmp_path: Path) -> None:
    passed = evaluate_text(GOOD_OUTPUT).render()
    failed = evaluate_text("# Nothing").render()

    assert "Result: PASS" in passed
    assert "Result: FAIL" in failed
    assert "✗ Objective" in failed


def test_find_helpers() -> None:
    assert find_missing_sections(GOOD_OUTPUT) == []
    assert find_missing_sections("# Empty") == list(REQUIRED_SECTIONS)
    assert find_missing_concepts("Create product", ("create product", "delete product")) == [
        "delete product"
    ]
