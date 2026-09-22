# Agent Orchestration Report

## Request Analysis

- strategy: auto
- selection: 2 intent(s) detected: code-review, unit-test-generation
- signals for code-review: diff, refactor, diff code block
- signals for unit-test-generation: unit test, unit tests, pytest
- selected agents: code-review, unit-test-generation

## Agent: Code Review

# Code Review

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

## Agent: Unit Test Generation

# Unit Test Plan

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

## Summary

- code-review: PASS (0 tool call(s))
- unit-test-generation: PASS (0 tool call(s))
