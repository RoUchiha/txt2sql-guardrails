"""Adversarial corpus for the guard. The gate: 100% of MUST_BLOCK is blocked,
100% of MUST_ALLOW is allowed. Add a case here whenever a new attack is found.
"""

# Queries that MUST be blocked. Each tuple is (sql, why).
MUST_BLOCK: list[tuple[str, str]] = [
    ("SELECT * FROM users; DROP TABLE users", "stacked statement"),
    ("SELECT * FROM users; DROP TABLE users; --", "stacked + comment"),
    ("DROP TABLE users", "drop"),
    ("DROP/**/TABLE users", "comment-obfuscated drop"),
    ("DrOp TaBlE users", "mixed-case drop"),
    ("DELETE FROM users", "delete without where"),
    ("DELETE FROM users WHERE id = 1", "delete (writes disabled)"),
    ("UPDATE users SET name = 'x' WHERE id = 1", "update (writes disabled)"),
    ("INSERT INTO users (id, name) VALUES (1, 'x')", "insert (writes disabled)"),
    ("TRUNCATE TABLE users", "truncate"),
    ("ALTER TABLE users ADD COLUMN hacked INT", "alter"),
    ("CREATE TABLE evil (id INT)", "create"),
    ("GRANT SELECT ON users TO bob", "grant"),
    ("PRAGMA table_info(users)", "pragma"),
    ("VACUUM", "vacuum command"),
    ("ATTACH DATABASE 'evil.db' AS evil", "attach"),
    ("SELECT id FROM users UNION SELECT name FROM secret_admins", "union to unknown table"),
    ("SELECT * FROM sqlite_master", "fishing for metadata table"),
    ("SELECT * FROM users WHERE id IN (SELECT token FROM secret_tokens)", "subquery unknown table"),
    ("SELECT u.password FROM users u", "unknown column (fishing)"),
    ("WITH x AS (DELETE FROM users RETURNING *) SELECT * FROM x", "delete hidden in CTE"),
    ("SELECT * FROM users LIMIT 1; DELETE FROM orders", "stacked select+delete"),
    ("SELECT FROM WHERE )(", "unparseable garbage"),
    ("", "empty query"),
    ("   ", "whitespace-only query"),
    ("select * from users; select * from orders; drop table users", "triple stack"),
]

# Legitimate read-only queries that MUST pass.
MUST_ALLOW: list[str] = [
    "SELECT * FROM users",
    "SELECT id, name FROM users WHERE id = 5",
    "SELECT COUNT(*) FROM orders",
    "SELECT u.name, o.total FROM users u JOIN orders o ON o.user_id = u.id WHERE o.total > 100",
    "SELECT name FROM products ORDER BY price DESC LIMIT 5",
    (
        "WITH big AS (SELECT user_id, SUM(total) AS s FROM orders GROUP BY user_id) "
        "SELECT u.name, big.s FROM users u JOIN big ON big.user_id = u.id"
    ),
    "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)",
    "SELECT name, email FROM users WHERE name LIKE 'A%'",
    "SELECT p.name FROM products p WHERE p.price BETWEEN 10 AND 20",
    "SELECT DISTINCT user_id FROM orders",
]
