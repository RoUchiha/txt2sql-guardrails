"""CLI smoke tests via Typer's CliRunner (runs offline, mock provider)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from txt2sql.cli import app
from txt2sql.sampledb import build

runner = CliRunner()


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # isolate audit.jsonl writes
    return build(tmp_path / "sample.db")


def test_query_allows_and_executes(db):
    result = runner.invoke(app, ["query", "--db", db, "--q", "top customers by spend"])
    assert result.exit_code == 0
    assert "ALLOW" in result.stdout


def test_explain_blocks_destructive(db):
    result = runner.invoke(app, ["explain", "--db", db, "--q", "drop the users table"])
    assert result.exit_code == 0
    assert "BLOCK" in result.stdout


def test_audit_lists_decisions(db):
    runner.invoke(app, ["query", "--db", db, "--q", "count users"])
    result = runner.invoke(app, ["audit"])
    assert result.exit_code == 0
    assert "count users" in result.stdout


def test_audit_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["audit"])
    assert result.exit_code == 0
    assert "no audit log" in result.stdout
