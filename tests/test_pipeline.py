"""End-to-end pipeline tests, including the security invariant that a malicious
generation never reaches execution."""

from __future__ import annotations

import pytest

from txt2sql.config import Config
from txt2sql.pipeline import Pipeline
from txt2sql.providers.mock import MockProvider
from txt2sql.sampledb import build
from txt2sql.schema.introspect import introspect_sqlite


@pytest.fixture
def db(tmp_path):
    return build(tmp_path / "sample.db")


@pytest.fixture
def schema(db):
    return introspect_sqlite(db)


@pytest.mark.asyncio
async def test_e2e_legit_question_returns_rows(db, schema, tmp_path):
    pipe = Pipeline(schema=schema, config=Config(), db_path=db,
                    audit_path=str(tmp_path / "audit.jsonl"))
    result = await pipe.run("top customers by spend")
    assert result.guard.allowed and result.executed
    assert result.result and result.result.row_count > 0


@pytest.mark.asyncio
async def test_malicious_generation_never_executes(db, schema, tmp_path):
    """A model that emits DROP must be blocked at the guard and NOT executed.

    We spy on the Sandbox to assert zero execution calls.
    """
    calls = {"n": 0}

    pipe = Pipeline(
        schema=schema,
        config=Config(),
        provider=MockProvider(fixed_response="DROP TABLE users"),
        db_path=db,
        audit_path=str(tmp_path / "audit.jsonl"),
    )

    # Monkeypatch Sandbox.execute via the module the pipeline imports lazily.
    from txt2sql.execute import sandbox as sandbox_mod

    orig = sandbox_mod.Sandbox.execute

    def spy(self, sql):  # noqa: ANN001
        calls["n"] += 1
        return orig(self, sql)

    sandbox_mod.Sandbox.execute = spy
    try:
        result = await pipe.run("please drop everything")
    finally:
        sandbox_mod.Sandbox.execute = orig

    assert not result.guard.allowed
    assert result.executed is False
    assert calls["n"] == 0  # execution spy proves it never ran


@pytest.mark.asyncio
async def test_explain_does_not_execute(schema, tmp_path):
    pipe = Pipeline(schema=schema, config=Config(), db_path=None,
                    audit_path=str(tmp_path / "audit.jsonl"))
    result = await pipe.run("show me all users", execute=False)
    assert result.guard.allowed and not result.executed


@pytest.mark.asyncio
async def test_audit_log_written(db, schema, tmp_path):
    audit = tmp_path / "audit.jsonl"
    pipe = Pipeline(schema=schema, config=Config(), db_path=db, audit_path=str(audit))
    await pipe.run("count users")
    await pipe.run("drop the users")
    assert audit.exists()
    assert len(audit.read_text(encoding="utf-8").strip().splitlines()) == 2
