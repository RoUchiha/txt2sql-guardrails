"""Sandbox tests: schema introspection, LIMIT injection, read-only enforcement."""

from __future__ import annotations

import pytest

from txt2sql.config import Config
from txt2sql.execute.sandbox import Sandbox, SandboxError, inject_limit
from txt2sql.sampledb import build
from txt2sql.schema.introspect import introspect_sqlite


@pytest.fixture
def db(tmp_path):
    return build(tmp_path / "sample.db")


def test_introspection_matches_sample(db):
    schema = introspect_sqlite(db)
    assert set(schema.tables) == {"users", "orders", "products"}
    assert "email" in schema.columns_of("users")


def test_inject_limit_adds_when_absent():
    out = inject_limit("SELECT * FROM users", "sqlite", 50).upper()
    assert "LIMIT 51" in out


def test_inject_limit_respects_existing():
    out = inject_limit("SELECT * FROM users LIMIT 3", "sqlite", 50).upper()
    assert "LIMIT 3" in out and "LIMIT 51" not in out


def test_select_executes_and_caps(db):
    cfg = Config(row_limit=3)
    res = Sandbox(db, cfg).execute("SELECT id FROM orders")
    assert res.row_count == 3 and res.truncated  # 8 orders seeded


def test_readonly_connection_rejects_write(db):
    """Belt-and-suspenders: even if the guard were bypassed, the connection is RO."""
    with pytest.raises(SandboxError):
        Sandbox(db, Config()).execute("DELETE FROM users")
