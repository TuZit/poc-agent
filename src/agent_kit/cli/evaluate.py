"""``agent-kit evaluate`` — deterministic evaluation of a generated output."""

from __future__ import annotations

from pathlib import Path

import typer

from agent_kit.cli.common import info
from agent_kit.evaluation import REQUIRED_SECTIONS, evaluate_file


def evaluate_command(
    output_file: Path = typer.Argument(..., help="Generated output file to evaluate."),
    require_section: list[str] | None = typer.Option(
        None, "--require-section", "-s", help="Required section (repeatable)."
    ),
    require_concept: list[str] | None = typer.Option(
        None, "--require-concept", "-c", help="Required keyword (repeatable)."
    ),
) -> None:
    """Check an output file: exists, non-empty, has the required sections/concepts."""
    sections = tuple(require_section) if require_section else REQUIRED_SECTIONS
    concepts = tuple(require_concept or ())

    result = evaluate_file(output_file, required_sections=sections, required_concepts=concepts)
    info(result.render())
    raise typer.Exit(code=0 if result.passed else 1)
