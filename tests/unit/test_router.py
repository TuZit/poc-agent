"""Unit tests for the deterministic task router."""

from __future__ import annotations

import pytest

from agent_kit.routing import RoutingDecision, TaskRouter, keyword_matches, structural_signals
from agent_kit.workflow import specialist_workflows

CODE_REVIEW_REQUEST = """Review this diff before we merge it.

```diff
+def total(items):
+    return sum(item["price"] for item in items)
```
"""

TEST_REQUEST = "Please write unit tests for the pricing module. The project uses pytest."

REQUIREMENT_REQUEST = (
    "We need a requirement for the new checkout feature: user story, actors and "
    "acceptance criteria."
)

MIXED_REQUEST = """We are about to merge the checkout refactor: review the change below and
generate the unit tests we are missing.
"""


@pytest.fixture
def router() -> TaskRouter:
    return TaskRouter(specialist_workflows())


@pytest.fixture
def candidates():
    return {workflow.name: workflow for workflow in specialist_workflows()}


# --- keyword matching -----------------------------------------------------
@pytest.mark.parametrize(
    ("text", "keyword", "expected"),
    [
        ("review this code", "review", True),
        ("code review please", "code review", True),
        ("review the output", "review the output", True),
        ("no match here", "review", False),
    ],
)
def test_keyword_matches_long_keywords(text: str, keyword: str, expected: bool) -> None:
    assert keyword_matches(text, keyword) is expected


def test_short_keywords_require_a_word_boundary() -> None:
    # "pr" must not fire inside "product", "ut" must not fire inside "output".
    assert keyword_matches("update the product", "pr") is False
    assert keyword_matches("write the output", "ut") is False
    assert keyword_matches("open a pr please", "pr") is True


def test_structural_signals_detect_a_diff_and_existing_tests() -> None:
    assert "unified diff hunk" in structural_signals("@@ -1,3 +1,4 @@", "code-review")
    assert "unified diff header" in structural_signals("+++ b/app.py", "code-review")
    assert "existing test function" in structural_signals(
        "def test_total():", "unit-test-generation"
    )
    assert structural_signals("nothing to see", "code-review") == []


# --- scoring --------------------------------------------------------------
def test_signals_report_matched_keywords_per_agent(router: TaskRouter) -> None:
    signals = router.signals(CODE_REVIEW_REQUEST)

    assert "code-review" in signals
    assert "review this" in signals["code-review"]
    assert "diff code block" in signals["code-review"]
    assert "unit-test-generation" not in signals


def test_rank_orders_by_signal_count(router: TaskRouter) -> None:
    ranked = router.rank(MIXED_REQUEST)

    names = [name for name, _ in ranked]
    assert set(names) == {"code-review", "unit-test-generation"}
    assert len(ranked[0][1]) >= len(ranked[1][1])


# --- selection ------------------------------------------------------------
def test_auto_selects_the_code_review_agent(router: TaskRouter) -> None:
    decision = router.select(CODE_REVIEW_REQUEST)

    assert decision.selected == ["code-review"]
    assert decision.strategy == "auto"
    assert not decision.is_empty


def test_auto_selects_the_unit_test_agent(router: TaskRouter) -> None:
    assert router.select(TEST_REQUEST).selected == ["unit-test-generation"]


def test_auto_selects_the_requirement_agent(router: TaskRouter) -> None:
    assert router.select(REQUIREMENT_REQUEST).selected == ["requirement-analysis"]


def test_auto_selects_both_agents_for_a_mixed_request(router: TaskRouter) -> None:
    decision = router.select(MIXED_REQUEST)

    assert set(decision.selected) == {"code-review", "unit-test-generation"}
    assert "2 intent" in decision.reason


def test_auto_falls_back_to_default_agents(router: TaskRouter) -> None:
    decision = router.select("hello there", default=["requirement-analysis"])

    assert decision.selected == ["requirement-analysis"]
    assert "no signal matched" in decision.reason


def test_auto_without_default_agents_selects_nothing(router: TaskRouter) -> None:
    decision = router.select("hello there")

    assert decision.selected == []
    assert decision.is_empty
    assert "no specialist agent selected" in decision.describe()


def test_all_strategy_runs_every_candidate(router: TaskRouter) -> None:
    decision = router.select("hello there", strategy="all")

    assert set(decision.selected) == {
        "requirement-analysis",
        "code-review",
        "unit-test-generation",
    }
    assert decision.reason == "strategy=all"


def test_allowed_list_restricts_selection(router: TaskRouter) -> None:
    decision = router.select(MIXED_REQUEST, allowed={"unit-test-generation"})

    assert decision.selected == ["unit-test-generation"]

    fallback = router.select(
        "hello there", allowed={"unit-test-generation"}, default=["code-review"]
    )
    assert fallback.selected == []  # default outside the allow-list is ignored


def test_decision_serialises_for_reports(router: TaskRouter) -> None:
    decision = router.select(TEST_REQUEST)

    assert isinstance(decision, RoutingDecision)
    assert "unit-test-generation" in decision.describe()
