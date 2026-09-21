"""Shared helpers for the CLI layer."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import typer

OK_MARK = "✓"
FAIL_MARK = "✗"


def fail(message: str, code: int = 1) -> NoReturn:
    """Print an actionable error and exit with ``code``."""
    typer.echo(f"{FAIL_MARK} {message}", err=True)
    raise typer.Exit(code=code)


def info(message: str) -> None:
    typer.echo(message)


def relative_to(path: Path, base: Path) -> str:
    """Path relative to ``base`` when possible, else the absolute path."""
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)
