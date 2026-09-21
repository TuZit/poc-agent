"""Workflow abstraction — separate from the agent runtime.

A workflow owns the *process* (input → skill → analyze → generate → validate);
the :class:`~agent_kit.agent.agent.Agent` owns the model/tool loop. Additional
workflows (``code-review``, ``test-generation``, ``documentation-generation``,
``api-validation``, ``migration``) register in :data:`WORKFLOW_REGISTRY`.
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

    @property
    def tool_call_count(self) -> int:
        return len(self.tool_invocations)


class Workflow(ABC):
    """Base class for workflows."""

    #: Name used in ``workflow.name``.
    name: str = "workflow"
    #: Skill loaded when the configuration declares no skill.
    default_skill: str | None = None
    #: One-line description for ``agent-kit workflow list`` style output.
    description: str = ""

    @abstractmethod
    def execute(self, context: WorkflowContext, runtime: AgentRuntime) -> WorkflowResult:
        """Run the workflow and return its (already validated) result."""


class RequirementAnalysisWorkflow(Workflow):
    """Input requirement → load skill → analyze → generate → validate → return."""

    name = "requirement-analysis"
    default_skill = "requirement-analysis"
    description = "Turn a raw requirement into a structured requirement summary."

    def execute(self, context: WorkflowContext, runtime: AgentRuntime) -> WorkflowResult:
        skill = context.skill
        if skill is None and self.default_skill:
            skill = runtime.load_skill(self.default_skill)

        agent = runtime.build_agent()
        agent_result = agent.run(context.input_text, skill=skill)

        issues = [
            f"Missing required section: '{section}'"
            for section in find_missing_sections(agent_result.output)
        ]
        return WorkflowResult(
            workflow=self.name,
            output=agent_result.output,
            valid=not issues,
            issues=issues,
            tool_invocations=agent_result.tool_invocations,
        )


WORKFLOW_REGISTRY: dict[str, type[Workflow]] = {
    RequirementAnalysisWorkflow.name: RequirementAnalysisWorkflow,
}


def available_workflows() -> list[str]:
    return sorted(WORKFLOW_REGISTRY)


def create_workflow(name: str) -> Workflow:
    """Instantiate a workflow by name."""
    workflow_class = WORKFLOW_REGISTRY.get(name)
    if workflow_class is None:
        raise WorkflowError(
            f"Unknown workflow '{name}'. Available workflows: {', '.join(available_workflows())}."
        )
    return workflow_class()


__all__ = [
    "WORKFLOW_REGISTRY",
    "RequirementAnalysisWorkflow",
    "Workflow",
    "WorkflowContext",
    "WorkflowError",
    "WorkflowResult",
    "available_workflows",
    "create_workflow",
]
