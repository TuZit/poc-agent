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