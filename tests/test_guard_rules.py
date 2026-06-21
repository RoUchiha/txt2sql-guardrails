"""Unit tests for individual guard rules and verdict structure."""

from __future__ import annotations

from txt2sql.config import Config
from txt2sql.guard import Guard
from txt2sql.models import SchemaInfo


def test_allow_simple_select(guard):
    v = guard.check("SELECT id FROM users WHERE id = 1")
    assert v.allowed and v.normalized_sql


def test_parse_failure_blocks(guard):
    v = guard.check("SELECT FROM WHERE )(")
    assert not v.allowed and "parse" in v.violated_rules


def test_stacked_statement_blocks(guard):
    v = guard.check("SELECT 1; DROP TABLE users")
    assert not v.allowed and "single_statement" in v.violated_rules


def test_statement_type_blocks_delete(guard):
    v = guard.check("DELETE FROM users WHERE id = 1")
    assert not v.allowed and "statement_allowlist" in v.violated_rules


def test_unknown_table_blocks(guard):
    v = guard.check("SELECT * FROM secret_admins")
    assert not v.allowed and "identifier_validation" in v.violated_rules


def test_unknown_column_blocks(guard):
    v = guard.check("SELECT u.password FROM users u")
    assert not v.allowed and "identifier_validation" in v.violated_rules


def test_no_schema_disables_identifier_check():
    # With no schema, identifier validation is skipped, but type rules still apply.
    g = Guard(Config(), SchemaInfo())
    assert g.check("SELECT * FROM anything").allowed
    assert not g.check("DROP TABLE anything").allowed


def test_writes_enabled_still_blocks_unfiltered(schema):
    cfg = Config(read_only=False, allowed_statement_types=["SELECT", "DELETE"])
    g = Guard(cfg, schema)
    assert not g.check("DELETE FROM users").allowed  # no WHERE
    assert g.check("DELETE FROM users WHERE id = 1").allowed  # has WHERE


def test_block_names_rules(guard):
    v = guard.check("DROP TABLE users")
    assert v.violated_rules and not v.allowed
