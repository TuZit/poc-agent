Generate the unit tests we are missing for this pricing module.

```python
def total_price(items):
    """Return the summed price of a cart. Raises ValueError for negative prices."""
    if any(item["price"] < 0 for item in items):
        raise ValueError("price must be >= 0")
    return sum(item["price"] * item["quantity"] for item in items)


def apply_discount(total, percent):
    """Apply a percentage discount. Raises ValueError outside 0..100."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    return total * (1 - percent / 100)
```

Notes:

- quantities and prices are integers coming from the product catalogue;
- the project already uses pytest.
