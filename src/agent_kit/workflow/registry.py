"""Workflow registry.

One place to add a specialist agent: write its skill, subclass
:class:`~agent_kit.workflow.workflow.SkillWorkflow` in
:mod:`agent_kit.workflow.specialists`, and register it here.
"""

from __future__ import annotations

from collections.abc import Sequence

from agent_kit.routing import TaskRouter
from agent_kit.workflow.orchestration import OrchestrationWorkflow
from agent_kit.workflow.specialists import (
    CodeReviewWorkflow,
    RequirementAnalysisWorkflow,
    UnitTestGenerationWorkflow,
)
from agent_kit.workflow.workflow import Workflow, WorkflowError

WORKFLOW_REGISTRY: dict[str, type[Workflow]] = {
    RequirementAnalysisWorkflow.name: RequirementAnalysisWorkflow,
    CodeReviewWorkflow.name: CodeReviewWorkflow,
    UnitTestGenerationWorkflow.name: UnitTestGenerationWorkflow,
    OrchestrationWorkflow.name: OrchestrationWorkflow,
}


def available_workflows() -> list[str]:
    """Every registered workflow name, sorted."""
    return sorted(WORKFLOW_REGISTRY)


def create_workflow(name: str) -> Workflow:
    """Instantiate a workflow by name."""
    workflow_class = WORKFLOW_REGISTRY.get(name)
    if workflow_class is None:
        raise WorkflowError(
            f"Unknown workflow '{name}'. Available workflows: {', '.join(available_workflows())}."
        )
    return workflow_class()


def specialist_workflows() -> list[Workflow]:
    """Registered workflow instances that are *not* orchestrators."""
    return [
        create_workflow(name)
        for name in available_workflows()
        if not WORKFLOW_REGISTRY[name].is_orchestrator
    ]


def available_specialists() -> list[str]:
    """Names of the specialist agents (the orchestrator's candidates)."""
    return [workflow.name for workflow in specialist_workflows()]


def get_specialist(name: str) -> Workflow:
    """Return one specialist workflow or raise :class:`WorkflowError`."""
    workflow_class = WORKFLOW_REGISTRY.get(name)
    if workflow_class is None or workflow_class.is_orchestrator:
        raise WorkflowError(
            f"Unknown agent '{name}'. Available agents: {', '.join(available_specialists())}."
        )
    return workflow_class()


def sections_for_workflow(name: str) -> tuple[str, ...]:
    """Output contract of a workflow (used by ``agent-kit evaluate --workflow``)."""
    return create_workflow(name).required_sections


def build_router(candidates: Sequence[Workflow] | None = None) -> TaskRouter:
    """Router over the given workflows (defaults to every specialist)."""
    return TaskRouter(list(candidates) if candidates is not None else specialist_workflows())


__all__ = [
    "WORKFLOW_REGISTRY",
    "available_specialists",
    "available_workflows",
    "build_router",
    "create_workflow",
    "get_specialist",
    "sections_for_workflow",
    "specialist_workflows",
]
