"""Deterministic evaluator — no LLM-as-a-judge in this POC.

Checks performed:

1. the output file exists and is not empty;
2. every required Markdown section heading is present;
3. every required concept (keyword) is present (optional, opt-in).

Section matching is case-insensitive and heading-level agnostic, so
``## Objective`` and ``### OBJECTIVE`` both count. Exact text matching is
deliberately *not* performed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

#: Sections the ``requirement-analysis`` skill must produce.
REQUIRED_SECTIONS: tuple[str, ...] = (
    "Objective",
    "Actors",
    "Functional Requirements",
    "Non-Functional Requirements",
    "Assumptions",
    "Open Questions",
)

#: Extra sections the sample expected output uses.
SAMPLE_SECTIONS: tuple[str, ...] = (*REQUIRED_SECTIONS, "Product Attributes")

_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(?P<title>.+?)\s*#*\s*$", re.MULTILINE)


@dataclass(frozen=True)
class CheckResult:
    """One deterministic check."""

    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class EvaluationResult:
    """Aggregated evaluation outcome."""

    passed: bool
    checks: list[CheckResult] = field(default_factory=list)
    source: str = ""

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [check for check in self.checks if not check.passed]

    def render(self, title: str = "Evaluation") -> str:
        """Human-readable report, e.g. for the CLI."""
        lines = [title, ""]
        for check in self.checks:
            mark = "✓" if check.passed else "✗"
            suffix = f" — {check.detail}" if check.detail and not check.passed else ""
            lines.append(f"{mark} {check.name}{suffix}")
        lines.append("")
        lines.append(f"Result: {'PASS' if self.passed else 'FAIL'}")
        return "\n".join(lines)


def extract_sections(text: str) -> set[str]:
    """Return normalised Markdown heading titles found in ``text``."""
    return {match.group("title").strip().casefold() for match in _HEADING_RE.finditer(text)}


def find_missing_sections(
    text: str,
    required_sections: tuple[str, ...] = REQUIRED_SECTIONS,
) -> list[str]:
    """Required sections that are absent from ``text`` (original casing)."""
    present = extract_sections(text)
    return [section for section in required_sections if section.casefold() not in present]


def find_missing_concepts(text: str, required_concepts: tuple[str, ...]) -> list[str]:
    """Required concepts (substring, case-insensitive) absent from ``text``."""
    haystack = text.casefold()
    return [concept for concept in required_concepts if concept.casefold() not in haystack]


def evaluate_text(
    text: str,
    required_sections: tuple[str, ...] = REQUIRED_SECTIONS,
    required_concepts: tuple[str, ...] = (),
    source: str = "<text>",
) -> EvaluationResult:
    """Evaluate output text against the required sections and concepts."""
    checks: list[CheckResult] = []

    non_empty = bool(text and text.strip())
    checks.append(
        CheckResult(
            name="Output generated",
            passed=non_empty,
            detail="" if non_empty else f"{source} is empty",
        )
    )

    for section in required_sections:
        present = section.casefold() in extract_sections(text)
        checks.append(
            CheckResult(
                name=section,
                passed=present,
                detail=f"missing section '{section}'",
            )
        )

    for concept in required_concepts:
        present = concept.casefold() in text.casefold()
        checks.append(
            CheckResult(
                name=f"Concept: {concept}",
                passed=present,
                detail=f"missing concept '{concept}'",
            )
        )

    return EvaluationResult(
        passed=all(check.passed for check in checks),
        checks=checks,
        source=source,
    )


def evaluate_file(
    path: Path | str,
    required_sections: tuple[str, ...] = REQUIRED_SECTIONS,
    required_concepts: tuple[str, ...] = (),
) -> EvaluationResult:
    """Evaluate an output file. A missing/unreadable file is a failed check."""
    file_path = Path(path)
    if not file_path.is_file():
        return EvaluationResult(
            passed=False,
            checks=[
                CheckResult(
                    name="Output generated",
                    passed=False,
                    detail=f"file not found: {file_path}",
                )
            ],
            source=str(file_path),
        )

    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return EvaluationResult(
            passed=False,
            checks=[
                CheckResult(
                    name="Output generated",
                    passed=False,
                    detail=f"cannot read {file_path}: {exc}",
                )
            ],
            source=str(file_path),
        )

    return evaluate_text(
        text,
        required_sections=required_sections,
        required_concepts=required_concepts,
        source=str(file_path),
    )
