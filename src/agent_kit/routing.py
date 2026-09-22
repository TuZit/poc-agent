"""Deterministic task router used by the orchestrator.

The router answers one question: *which specialist agents should handle this
request?* It is deliberately rule-based — no model call — so routing is
reproducible, testable offline, free, and explainable in the generated report.

Matching rules:

* keywords shorter than 4 characters match whole words only (so ``pr`` does not
  match "product", and ``ut`` does not match "output");
* longer keywords match case-insensitively as substrings;
* structural signals add evidence: unified-diff markers point at code review,
  existing assertions/test functions point at unit-test generation;
* a workflow is selected when it has at least one signal; selected workflows are
  ordered by signal count (strongest first), ties keep configuration order;
* when nothing matches, the caller's default agents are used (``auto`` strategy).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# Layering note: this module lives outside the ``agent`` and ``workflow``
# packages and imports neither of them at runtime. It only reads workflow
# *metadata*, so the type import is type-checking-only. That keeps the import
# graph acyclic: workflow.registry -> agent_kit.routing -> (stdlib).
if TYPE_CHECKING:  # pragma: no cover
    from agent_kit.workflow.workflow import Workflow

#: Keywords this short (or shorter) must match a whole word.
SHORT_KEYWORD_MAX_LENGTH = 3

#: Structural evidence that a request is about a given kind of work.
STRUCTURAL_RULES: dict[str, tuple[tuple[str, str], ...]] = {
    "code-review": (
        ("@@", "unified diff hunk"),
        ("+++ ", "unified diff header"),
        ("--- a/", "unified diff header"),
        ("diff --git", "git diff"),
        ("```diff", "diff code block"),
    ),
    "unit-test-generation": (
        ("def test_", "existing test function"),
        ("assert ", "existing assertion"),
        ("pytest.mark", "pytest marker"),
        ("describe(", "test suite block"),
        ("it(", "test case block"),
    ),
}

_WORD_BOUNDARY_TEMPLATE = r"(?<![a-z0-9_]){keyword}(?![a-z0-9_])"


@dataclass(frozen=True)
class RoutingDecision:
    """Outcome of routing one request."""

    selected: list[str] = field(default_factory=list)
    signals: dict[str, list[str]] = field(default_factory=dict)
    strategy: str = "auto"
    reason: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.selected

    def describe(self) -> str:
        if not self.selected:
            return "no specialist agent selected"
        return f"{self.reason}: {', '.join(self.selected)}"


def keyword_matches(text: str, keyword: str) -> bool:
    """True when ``keyword`` appears in the already-lowercased ``text``."""
    if len(keyword) <= SHORT_KEYWORD_MAX_LENGTH and " " not in keyword:
        pattern = _WORD_BOUNDARY_TEMPLATE.format(keyword=re.escape(keyword))
        return re.search(pattern, text) is not None
    return keyword in text


def structural_signals(text: str, workflow_name: str) -> list[str]:
    """Structural evidence for ``workflow_name`` found in the lowered ``text``."""
    return [
        label for marker, label in STRUCTURAL_RULES.get(workflow_name, ()) if marker in text
    ]


class TaskRouter:
    """Scores a request against a fixed set of candidate workflows."""

    def __init__(self, candidates: Sequence[Workflow]) -> None:
        self.candidates = list(candidates)

    # -- scoring -----------------------------------------------------------
    def signals(self, text: str) -> dict[str, list[str]]:
        """Matched signals per workflow name."""
        lowered = text.casefold()
        found: dict[str, list[str]] = {}
        for workflow in self.candidates:
            matched = [
                keyword
                for keyword in workflow.routing_keywords
                if keyword_matches(lowered, keyword.casefold())
            ]
            matched += structural_signals(lowered, workflow.name)
            if matched:
                found[workflow.name] = matched
        return found

    def rank(self, text: str) -> list[tuple[str, list[str]]]:
        """``(workflow_name, signals)`` ordered by signal count, then config order."""
        found = self.signals(text)
        order = {workflow.name: index for index, workflow in enumerate(self.candidates)}
        return sorted(found.items(), key=lambda item: (-len(item[1]), order[item[0]]))

    # -- selection ---------------------------------------------------------
    def select(
        self,
        text: str,
        strategy: str = "auto",
        allowed: Iterable[str] | None = None,
        default: Sequence[str] = (),
    ) -> RoutingDecision:
        """Choose the workflows that should handle ``text``."""
        pool = [
            workflow
            for workflow in self.candidates
            if allowed is None or workflow.name in set(allowed)
        ]
        pool_names = {workflow.name for workflow in pool}

        if strategy == "all":
            return RoutingDecision(
                selected=[workflow.name for workflow in pool],
                signals=self.signals(text),
                strategy=strategy,
                reason="strategy=all",
            )

        ranked = [
            (name, signals)
            for name, signals in self.rank(text)
            if name in pool_names
        ]
        if ranked:
            return RoutingDecision(
                selected=[name for name, _ in ranked],
                signals=dict(ranked),
                strategy=strategy,
                reason=f"{len(ranked)} intent(s) detected",
            )

        fallback = [name for name in default if name in pool_names]
        return RoutingDecision(
            selected=fallback,
            signals={},
            strategy=strategy,
            reason="no signal matched, using default agents" if fallback else "no signal matched",
        )


__all__ = [
    "SHORT_KEYWORD_MAX_LENGTH",
    "STRUCTURAL_RULES",
    "RoutingDecision",
    "TaskRouter",
    "keyword_matches",
    "structural_signals",
]
