"""Orchestrator workflow — the "big agent" that dispatches to specialists.

    request ──► TaskRouter (deterministic analysis)
                     │
                     ├─ selects specialist agents (0..n)
                     ▼
        for each agent: load its skill → run the agent → validate its output
                     ▼
        aggregated report (# Agent Orchestration Report) + per-agent status

Design notes:

* Selection is rule-based and explainable (see :mod:`agent_kit.routing`) so
  the orchestrator runs offline and its decisions can be asserted in tests. An
  LLM planner is a future seam: ``orchestrator.planner`` must stay ``rules``
  until one exists.
* The orchestrator never talks to the model itself; it owns *coordination*, each
  specialist owns its own prompt, skill and output contract.
* Sub-agents selected in Kiro/other IDEs are driven by the LLM there (via the MCP
  tools), this workflow is the deterministic equivalent for CLI, CI and hooks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_kit.workflow.workflow import (
    Workflow,
    WorkflowContext,
    WorkflowError,
    WorkflowResult,
)

if TYPE_CHECKING:  # pragma: no cover
    from agent_kit.agent.runtime import AgentRuntime

#: Sections the aggregated report must contain.
ORCHESTRATION_SECTIONS = ("Request Analysis", "Summary")

#: Default input for the orchestrator (a request that mixes two intents).
ORCHESTRATION_SAMPLE = "samples/orchestration/input/sample-orchestration.md"

#: Strategies understood by :class:`OrchestrationWorkflow`.
SUPPORTED_STRATEGIES = ("auto", "all")


def _normalise_strategy(raw: Any) -> str:
    strategy = str(raw or "auto").strip().lower()
    if strategy not in SUPPORTED_STRATEGIES:
        raise WorkflowError(
            f"Unknown orchestrator strategy '{raw}'. "
            f"Supported strategies: {', '.join(SUPPORTED_STRATEGIES)}."
        )
    return strategy


def _parse_agents(raw: Any) -> list[str]:
    """Accept ``"a,b"``, ``["a", "b"]`` or ``None``."""
    if raw is None:
        return []
    values = [raw] if isinstance(raw, str) else list(raw)
    names: list[str] = []
    for value in values:
        for part in str(value).split(","):
            name = part.strip()
            if name and name not in names:
                names.append(name)
    return names


def build_report(
    *,
    decision_description: str,
    strategy: str,
    signals: dict[str, list[str]],
    results: list[WorkflowResult],
    titles: dict[str, str],
) -> str:
    """Render the aggregated orchestration report."""
    lines: list[str] = ["# Agent Orchestration Report", "", "## Request Analysis", ""]
    lines.append(f"- strategy: {strategy}")
    lines.append(f"- selection: {decision_description}")
    for name, matched in signals.items():
        lines.append(f"- signals for {name}: {', '.join(matched)}")
    selected = ", ".join(result.workflow for result in results) or "(none)"
    lines.append(f"- selected agents: {selected}")

    for result in results:
        title = titles.get(result.workflow, result.workflow)
        lines += ["", f"## Agent: {title}", "", result.output.strip()]

    lines += ["", "## Summary", ""]
    if results:
        lines += [f"- {result.status_line()}" for result in results]
    else:
        lines.append("- no specialist agent was selected")
    return "\n".join(lines).strip() + "\n"


class OrchestrationWorkflow(Workflow):
    """Analyse a request, choose specialist agents and run them in order."""

    name = "orchestration"
    title = "Agent Orchestration"
    description = (
        "Analyse a request, select the specialist agents that fit it and run them, "
        "then aggregate their results into one report."
    )
    required_sections = ORCHESTRATION_SECTIONS
    routing_keywords = ()
    default_skill = None
    default_input = ORCHESTRATION_SAMPLE
    is_orchestrator = True

    def execute(self, context: WorkflowContext, runtime: AgentRuntime) -> WorkflowResult:
        # Deferred import keeps the module import graph acyclic (routing is a
        # top-level module that the registry also uses).
        from agent_kit.routing import RoutingDecision, TaskRouter

        settings = runtime.config.orchestrator
        strategy = _normalise_strategy(
            context.workflow_options.get("strategy") or settings.strategy
        )
        explicit = _parse_agents(context.workflow_options.get("agents"))

        candidates = runtime.specialist_workflows()
        available = {workflow.name for workflow in candidates}
        if not candidates:
            raise WorkflowError(
                "No specialist agents are enabled. List them under 'orchestrator.agents' "
                "in .agent/config.yaml."
            )

        if explicit:
            unknown = [name for name in explicit if name not in available]
            if unknown:
                raise WorkflowError(
                    f"Unknown agent(s): {', '.join(unknown)}. "
                    f"Available agents: {', '.join(sorted(available))}."
                )
            decision = RoutingDecision(
                selected=explicit,
                signals={},
                strategy="explicit",
                reason="explicit agent selection",
            )
        else:
            decision = TaskRouter(candidates).select(
                context.input_text,
                strategy=strategy,
                allowed=available,
                default=settings.default_agents,
            )

        if not decision.selected:
            raise WorkflowError(
                "The orchestrator selected no agent for this request. Add an agent to "
                "'orchestrator.agents' in .agent/config.yaml, or pass --agents <name>."
            )

        results = [
            runtime.run_specialist(name, context.input_text) for name in decision.selected
        ]
        titles = {workflow.name: workflow.display_title() for workflow in candidates}

        report = build_report(
            decision_description=decision.describe(),
            strategy=decision.strategy,
            signals=decision.signals,
            results=results,
            titles=titles,
        )

        issues = list(self.validate(report))
        for result in results:
            issues += [f"{result.workflow}: {issue}" for issue in result.issues]

        return WorkflowResult(
            workflow=self.name,
            output=report,
            valid=not issues,
            issues=issues,
            tool_invocations=[call for result in results for call in result.tool_invocations],
            required_sections=self.required_sections,
            metadata={
                "strategy": decision.strategy,
                "selected_agents": list(decision.selected),
                "signals": dict(decision.signals),
                "agent_results": {result.workflow: result.valid for result in results},
            },
        )


__all__ = [
    "ORCHESTRATION_SAMPLE",
    "ORCHESTRATION_SECTIONS",
    "SUPPORTED_STRATEGIES",
    "OrchestrationWorkflow",
    "build_report",
]
