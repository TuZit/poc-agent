"""Workflow abstraction — separate from the agent runtime.

A workflow owns the *process* (input → skill → analyse → generate → validate);
the :class:`~agent_kit.agent.agent.Agent` owns the model/tool loop.

Two kinds of workflow exist:

* **specialist workflows** (:mod:`agent_kit.workflow.specialists`) — one skill,
  one output contract: ``requirement-analysis``, ``code-review``,
  ``unit-test-generation``;
* **the orchestrator** (:mod:`agent_kit.workflow.orchestration`) — analyses a
  request, selects specialists and runs them.

The registry itself lives in :mod:`agent_kit.workflow.registry`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agent_kit.evaluation.evaluator import find_missing_sections
from agent_kit.skills.base import Skill

if TYPE_CHECKING:  # pragma: no cover - import cycle guards (runtime imports us)
    from agent_kit.agent.runtime import AgentRuntime
    from agent_kit.agent.state import ToolInvocation


class WorkflowError(Exception):
    """Raised for unknown or misconfigured workflows."""


@dataclass(frozen=True)
class WorkflowContext:
    """Everything a workflow needs before it starts."""

    input_text: str
    project_root: Path
    skill: Skill | None = None
    workflow_options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowResult:
    """Outcome of a workflow run."""

    workflow: str
    output: str
    valid: bool
    issues: list[str] = field(default_factory=list)
    tool_invocations: list[ToolInvocation] = field(default_factory=list)
    #: Sections this result was validated against.
    required_sections: tuple[str, ...] = ()
    #: Extra information for programmatic callers (the orchestrator records its
    #: strategy, the selected agents and their signals here).
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def tool_call_count(self) -> int:
        return len(self.tool_invocations)

    def status_line(self) -> str:
        """One-line status used in aggregated reports."""
        state = "PASS" if self.valid else "FAIL"
        return f"{self.workflow}: {state} ({self.tool_call_count} tool call(s))"


class Workflow(ABC):
    """Base class for workflows.

    Subclasses declare metadata so the CLI, the orchestrator and the MCP tools
    can describe themselves without hard-coding anything:

    * :attr:`name` — value used in ``workflow.name``
    * :attr:`title` / :attr:`description` — shown in ``agent-kit agents``
    * :attr:`default_skill` — skill loaded when the configuration declares none
    * :attr:`required_sections` — output contract enforced after the run
    * :attr:`routing_keywords` — signals the router matches against the request
    * :attr:`default_input` — sample input used when ``--input`` is omitted
    """

    name: str = "workflow"
    title: str = ""
    description: str = ""
    default_skill: str | None = None
    required_sections: tuple[str, ...] = ()
    routing_keywords: tuple[str, ...] = ()
    default_input: str | None = None
    #: True for workflows that dispatch to other workflows instead of the model.
    is_orchestrator: bool = False

    @abstractmethod
    def execute(self, context: WorkflowContext, runtime: AgentRuntime) -> WorkflowResult:
        """Run the workflow and return its (already validated) result."""

    def validate(self, output: str) -> list[str]:
        """Issues that make ``output`` invalid for this workflow."""
        return [
            f"Missing required section: '{section}'"
            for section in find_missing_sections(output, self.required_sections)
        ]

    def display_title(self) -> str:
        return self.title or self.name


class SkillWorkflow(Workflow):
    """Workflow shape shared by every specialist agent.

    Load the skill → run the agent → validate the output. Specialists only add
    metadata (skill, sections, routing signals, sample input).
    """

    def execute(self, context: WorkflowContext, runtime: AgentRuntime) -> WorkflowResult:
        skill = context.skill
        if skill is None and self.default_skill:
            skill = runtime.load_skill(self.default_skill)

        agent_result = runtime.build_agent().run(context.input_text, skill=skill)
        issues = self.validate(agent_result.output)

        return WorkflowResult(
            workflow=self.name,
            output=agent_result.output,
            valid=not issues,
            issues=issues,
            tool_invocations=agent_result.tool_invocations,
            required_sections=self.required_sections,
        )


__all__ = [
    "SkillWorkflow",
    "Workflow",
    "WorkflowContext",
    "WorkflowError",
    "WorkflowResult",
]
