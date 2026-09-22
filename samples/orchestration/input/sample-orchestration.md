We are about to merge the checkout refactor. Please review the change below, and
also generate the unit tests we are missing for the pricing helpers.

```diff
+def apply_discount(total, percent):
+    if not 0 <= percent <= 100:
+        raise ValueError("percent must be between 0 and 100")
+    return total * (1 - percent / 100)
+
+
+def total_price(items):
+    return sum(item["price"] * item["quantity"] for item in items)
```

Context:

- `total_price` does not validate negative prices, although the catalogue can contain them;
- no tests were added with the change;
- the project already uses pytest.
