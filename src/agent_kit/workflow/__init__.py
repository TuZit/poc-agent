"""Workflow layer.

* :mod:`agent_kit.workflow.workflow` — base classes and result types
* :mod:`agent_kit.workflow.specialists` — one skill + one output contract each
* :mod:`agent_kit.workflow.orchestration` — the orchestrator that dispatches
* :mod:`agent_kit.workflow.registry` — the single place workflows are registered

Import order: base types first, so tools that only need the contracts (and any
partially initialised import) see them immediately.
"""

from agent_kit.workflow.orchestration import (
    ORCHESTRATION_SAMPLE,
    ORCHESTRATION_SECTIONS,
    SUPPORTED_STRATEGIES,
    OrchestrationWorkflow,
)
from agent_kit.workflow.registry import (
    WORKFLOW_REGISTRY,
    available_specialists,
    available_workflows,
    build_router,
    create_workflow,
    get_specialist,
    sections_for_workflow,
    specialist_workflows,
)
from agent_kit.workflow.specialists import (
    CodeReviewWorkflow,
    RequirementAnalysisWorkflow,
    UnitTestGenerationWorkflow,
)
from agent_kit.workflow.workflow import (
    SkillWorkflow,
    Workflow,
    WorkflowContext,
    WorkflowError,
    WorkflowResult,
)

__all__ = [
    "ORCHESTRATION_SAMPLE",
    "ORCHESTRATION_SECTIONS",
    "SUPPORTED_STRATEGIES",
    "WORKFLOW_REGISTRY",
    "CodeReviewWorkflow",
    "OrchestrationWorkflow",
    "RequirementAnalysisWorkflow",
    "SkillWorkflow",
    "UnitTestGenerationWorkflow",
    "Workflow",
    "WorkflowContext",
    "WorkflowError",
    "WorkflowResult",
    "available_specialists",
    "available_workflows",
    "build_router",
    "create_workflow",
    "get_specialist",
    "sections_for_workflow",
    "specialist_workflows",
]
