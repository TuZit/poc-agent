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