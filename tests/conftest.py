"""Shared pytest fixtures.

Everything here runs offline: the deterministic ``MockModel`` is used
everywhere, so no test needs ``OPENAI_API_KEY``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_kit.scaffold import init_project

#: Configuration used by most tests: mock model, no network, no secrets.
MOCK_CONFIG = """\
agent:
  name: test-agent

model:
  provider: mock
  name: mock-model

tools:
  filesystem:
    enabled: true
  shell:
    enabled: false

skills:
  - requirement-analysis
  - code-review
  - unit-test-generation

workflow:
  name: requirement-analysis

orchestrator:
  strategy: auto
  planner: rules
  agents:
    - requirement-analysis
    - code-review
    - unit-test-generation
  default_agents:
    - requirement-analysis
"""


def write_config(project: Path, text: str = MOCK_CONFIG) -> Path:
    """Write ``.agent/config.yaml`` inside ``project`` and return its path."""
    config_dir = project / ".agent"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def output_of(result) -> str:
    """Combined stdout/stderr of a CliRunner result, across click versions."""
    combined = getattr(result, "output", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    if stderr and stderr not in combined:
        return f"{combined}\n{stderr}"
    return combined


@pytest.fixture
def runner() -> CliRunner:
    """Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def bare_project(tmp_path: Path) -> Path:
    """Empty directory that is not yet an agent-kit project."""
    project = tmp_path / "bare-project"
    project.mkdir()
    return project


@pytest.fixture
def mock_project(tmp_path: Path) -> Path:
    """Scaffolded project switched to the deterministic mock model."""
    project = tmp_path / "demo-project"
    init_project(project)
    write_config(project, MOCK_CONFIG)
    return project
