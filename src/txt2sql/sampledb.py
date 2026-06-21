"""Create the demo SQLite database (users / orders / products) with seed data.

Run as a module:  python -m txt2sql.sampledb [path]
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL NOT NULL
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    total REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

USERS = [
    (1, "Alice Carter", "alice@example.com", "2026-01-05"),
    (2, "Bob Nguyen", "bob@example.com", "2026-01-11"),
    (3, "Aisha Khan", "aisha@example.com", "2026-02-02"),
    (4, "Diego Santos", "diego@example.com", "2026-02-19"),
    (5, "Mei Lin", "mei@example.com", "2026-03-08"),
]
PRODUCTS = [
    (1, "Standard Plan", 29.0),
    (2, "Pro Plan", 99.0),
    (3, "Enterprise Plan", 499.0),
    (4, "Add-on Seat", 12.0),
    (5, "Priority Support", 199.0),
]
ORDERS = [
    (1, 1, 99.0, "2026-03-01"),
    (2, 1, 12.0, "2026-03-15"),
    (3, 2, 29.0, "2026-03-02"),
    (4, 3, 499.0, "2026-03-21"),
    (5, 3, 199.0, "2026-04-01"),
    (6, 4, 29.0, "2026-04-05"),
    (7, 5, 99.0, "2026-04-09"),
    (8, 5, 499.0, "2026-04-20"),
]


def build(path: str | Path = "sample.db") -> str:
    path = str(path)
    Path(path).unlink(missing_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT INTO users VALUES (?,?,?,?)", USERS)
        conn.executemany("INSERT INTO products VALUES (?,?,?)", PRODUCTS)
        conn.executemany("INSERT INTO orders VALUES (?,?,?,?)", ORDERS)
        conn.commit()
    finally:
        conn.close()
    return path


if __name__ == "__main__":
    out = build(sys.argv[1] if len(sys.argv) > 1 else "sample.db")
    print(f"wrote {out}")
