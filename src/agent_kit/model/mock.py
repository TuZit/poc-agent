"""Deterministic mock model.

This is what makes ``pytest`` runnable without ``OPENAI_API_KEY`` and what the
end-to-end integration test uses. Default output is a fixed requirement
summary that satisfies the ``requirement-analysis`` evaluator; pass ``script``
to drive the agent tool loop deterministically.
"""

from __future__ import annotations

from typing import Any

from agent_kit.model.base import Message, Model, ModelResponse, ToolSpec

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
        return ModelResponse(content=MOCK_REQUIREMENT_SUMMARY)
