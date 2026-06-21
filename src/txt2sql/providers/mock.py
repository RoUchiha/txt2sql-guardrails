"""Deterministic provider for offline tests and the demo.

It maps natural-language questions to canned SQL by keyword. Crucially, if the
question expresses destructive *intent* (drop/delete/wipe/...), it emits a
matching destructive query — so we can prove the guard blocks even a model that
faithfully tries to do something dangerous.
"""

from __future__ import annotations

# Keyword -> canned safe SQL. First match wins.
_SAFE_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    (("top", "customer"), "SELECT u.name, SUM(o.total) AS spend FROM users u "
                          "JOIN orders o ON o.user_id = u.id GROUP BY u.id "
                          "ORDER BY spend DESC LIMIT 5"),
    (("how many", "user"), "SELECT COUNT(*) AS user_count FROM users"),
    (("how many", "order"), "SELECT COUNT(*) AS order_count FROM orders"),
    (("count", "user"), "SELECT COUNT(*) AS user_count FROM users"),
    (("count", "order"), "SELECT COUNT(*) AS order_count FROM orders"),
    (("expensive", "product"), "SELECT name, price FROM products ORDER BY price DESC LIMIT 5"),
    (("cheap", "product"), "SELECT name, price FROM products ORDER BY price ASC LIMIT 5"),
    (("recent", "order"), "SELECT id, user_id, total, created_at FROM orders "
                          "ORDER BY created_at DESC LIMIT 10"),
    (("email",), "SELECT name, email FROM users LIMIT 20"),
    (("product",), "SELECT name, price FROM products LIMIT 20"),
    (("order",), "SELECT id, user_id, total FROM orders LIMIT 20"),
    (("user",), "SELECT id, name, email FROM users LIMIT 20"),
]

# Destructive intent -> the (dangerous) SQL a naive model might emit.
_DESTRUCTIVE: list[tuple[tuple[str, ...], str]] = [
    (("drop",), "DROP TABLE users"),
    (("truncate",), "TRUNCATE TABLE orders"),
    (("delete", "all"), "DELETE FROM users"),
    (("wipe",), "DELETE FROM orders"),
    (("remove", "everyone"), "DELETE FROM users"),
]

_FALLBACK = "SELECT id, name, email FROM users LIMIT 10"


class MockProvider:
    """A scripted provider. Optionally pin a fixed response for tests."""

    def __init__(self, fixed_response: str | None = None) -> None:
        self.fixed_response = fixed_response
        self.calls: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        if self.fixed_response is not None:
            return self.fixed_response
        # Match on the question, not the schema text the prompt also contains.
        question = prompt.lower().split("question:")[-1]
        return self._route(question)

    @staticmethod
    def _route(text: str) -> str:
        for keys, sql in _DESTRUCTIVE:
            if all(k in text for k in keys):
                return sql
        for keys, sql in _SAFE_PATTERNS:
            if all(k in text for k in keys):
                return sql
        return _FALLBACK
