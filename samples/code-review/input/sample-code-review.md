Review this change before we merge it.

```diff
+def add_item(items=[], price=0, quantity=1):
+    try:
+        items.append({"price": price, "quantity": quantity})
+        return items
+    except:
+        return None
+
+
+def total(items):
+    return sum(item["price"] * item["quantity"] for item in items)
```

Context:

- this is part of the checkout service;
- no tests were added with the change;
- `price` comes from the product catalogue, which currently allows 0.
