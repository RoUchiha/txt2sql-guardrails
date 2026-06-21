"""Generator + MockProvider tests (no network)."""

from __future__ import annotations

import pytest

from txt2sql.generate.generator import Generator, _strip_fences
from txt2sql.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_mock_routes_question_not_schema(schema):
    gen = Generator(MockProvider())
    out = await gen.generate("how many users are there?", schema)
    assert "count" in out.raw_sql.lower() and "users" in out.raw_sql.lower()


@pytest.mark.asyncio
async def test_mock_emits_destructive_on_destructive_intent(schema):
    gen = Generator(MockProvider())
    out = await gen.generate("drop the users table", schema)
    assert "drop" in out.raw_sql.lower()


def test_strip_fences():
    assert _strip_fences("```sql\nSELECT 1\n```") == "SELECT 1"
    assert _strip_fences("SELECT 1") == "SELECT 1"


@pytest.mark.asyncio
async def test_fixed_response(schema):
    gen = Generator(MockProvider(fixed_response="SELECT 1"))
    out = await gen.generate("anything", schema)
    assert out.raw_sql == "SELECT 1"
