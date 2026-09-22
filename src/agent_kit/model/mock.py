"""Deterministic mock model.

This is what makes ``pytest`` runnable without ``OPENAI_API_KEY`` and what the
end-to-end integration test uses. Default output is a fixed requirement
summary that satisfies the ``requirement-analysis`` evaluator; pass ``script``
to drive the agent tool loop deterministically.
"""

from __future__ import annotations

import re
from typing import Any

from agent_kit.model.base import Message, Model, ModelResponse, ToolSpec

#: Matches the skill banner the agent puts in the system message.
_LOADED_SKILL_RE = re.compile(r"^# Loaded skill:\s*(?P<name>\S+)\s*$", re.MULTILINE)

#: Deterministic answer returned when no explicit script is provided.
MOCK_REQUIREMENT_SUMMARY = """# Requirement Summary

## Objective

Provide an e-commerce product management API so that products can be created,
updated, deleted and searched through a REST interface.

## Actors

- API consumer (authenticated end user or client system)
- Product manager (maintains the product catalogue)
- System administrator (manages authentication and access)

## Functional Requirements

1. Create product
2. Update product
3. Delete product
4. Search product
5. Authenticate every API request

## Product Attributes

- id
- name
- description
- price
- stock

## Non-Functional Requirements

- REST-style API with standard HTTP semantics
- Authentication required on every endpoint
- Input validation for product attributes (price >= 0, stock >= 0)

## Assumptions

- A single product catalogue is shared by all API consumers.
- Authentication is provided by an existing identity mechanism.
- Search covers product name and description.

## Open Questions

- Which pagination and sorting semantics should search support?
- Are soft deletes acceptable, or must deletion be permanent?
"""


#: Deterministic answer per specialist agent, so MockModel can drive every
#: workflow offline (the agent tags the system message with the loaded skill).
MOCK_CODE_REVIEW = """# Code Review

## Summary

The change adds an item helper and a cart total. The logic is mostly sound, but
it mutates a default argument, swallows every exception and trusts unvalidated
input from the catalogue.

## Findings

1. `add_item` uses a mutable default argument (`items=[]`), so items leak between
   calls that pass no argument.
2. A bare `except:` hides programming errors (including `KeyboardInterrupt`) and
   turns them into `None`.
3. `total` does not validate `price` or `quantity`: a negative price silently
   produces a negative total.
4. No test covers the empty cart, a negative price or a quantity of zero.

## Recommendations

1. Replace `items=[]` with `items=None` and create the list inside the function.
2. Catch `ValueError`/`TypeError` explicitly and re-raise a wrapped error.
3. Validate `price >= 0` and `quantity > 0`, raising `ValueError` with a clear message.
4. Add unit tests for the empty cart, negative price, zero quantity and large totals.

## Open Questions

- Is a price of exactly 0 a valid free item, or should it be rejected?
- Must `quantity` be a positive integer, or are fractional quantities allowed?
"""

MOCK_UNIT_TEST_PLAN = """# Unit Test Plan

## Summary

Unit tests for the pricing helpers `total_price` and `apply_discount`, covering
the happy path plus the validation each function claims to enforce.

## Test Scope

- `total_price(items)` — sum of price x quantity, with negative-price validation.
- `apply_discount(total, percent)` — percentage discount with 0..100 bounds.
- Out of scope: persistence, HTTP layer, currency formatting.

## Test Cases

1. Single item → total equals `price * quantity`.
2. Several items → totals are summed.
3. Empty cart → `0`.
4. `apply_discount(100, 10)` → `90`.
5. `apply_discount(100, 0)` → `100`.

## Edge Cases

1. Quantity `0` → contributes `0`, not an error.
2. Negative price → `ValueError`.
3. `apply_discount(total, -1)` and `(total, 101)` → `ValueError`.
4. Very large totals → exact result, no overflow.
5. `None` instead of a list → `TypeError`.

## Open Questions

- Should discounts round to two decimals, and with which rounding mode?
- Is a quantity of `0` a valid order line, or should it be rejected?
"""

#: Fallback answer per skill name. Unknown skills get the requirement summary.
MOCK_OUTPUTS_BY_SKILL: dict[str, str] = {
    "requirement-analysis": MOCK_REQUIREMENT_SUMMARY,
    "code-review": MOCK_CODE_REVIEW,
    "unit-test-generation": MOCK_UNIT_TEST_PLAN,
}


def loaded_skill(messages: list[Message]) -> str | None:
    """Skill name the agent announced in its system message, if any."""
    for message in messages:
        if message.role == "system" and message.content:
            match = _LOADED_SKILL_RE.search(message.content)
            if match:
                return match.group("name")
    return None


class MockModel(Model):
    """Returns deterministic, offline output.

    Args:
        name: Model name recorded in logs/doctor output.
        script: Optional list of :class:`ModelResponse` replayed in order. The
            last response repeats if the agent asks for more turns. Useful for
            unit-testing the tool loop.
    """

    provider = "mock"
    required_env_vars: tuple[str, ...] = ()

    def __init__(
        self,
        name: str = "mock-model",
        script: list[ModelResponse] | None = None,
        **options: Any,
    ) -> None:
        super().__init__(name, **options)
        self._script = list(script) if script else None
        #: Every prompt the model received, for assertions in tests.
        self.calls: list[list[Message]] = []

    @property
    def invocation_count(self) -> int:
        return len(self.calls)

    def generate(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> ModelResponse:
        self.calls.append(list(messages))
        if self._script:
            index = min(len(self.calls) - 1, len(self._script) - 1)
            return self._script[index]
        skill = loaded_skill(messages) or ""
        return ModelResponse(
            content=MOCK_OUTPUTS_BY_SKILL.get(skill, MOCK_REQUIREMENT_SUMMARY)
        )
