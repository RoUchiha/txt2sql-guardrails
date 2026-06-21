"""Shared fixtures. The sample schema mirrors the demo SQLite database."""

from __future__ import annotations

import pytest

from txt2sql.config import Config
from txt2sql.guard import Guard
from txt2sql.models import SchemaInfo

SAMPLE_SCHEMA = SchemaInfo(
    dialect="sqlite",
    tables={
        "users": {"id": "INTEGER", "name": "TEXT", "email": "TEXT", "created_at": "TEXT"},
        "orders": {"id": "INTEGER", "user_id": "INTEGER", "total": "REAL", "created_at": "TEXT"},
        "products": {"id": "INTEGER", "name": "TEXT", "price": "REAL"},
    },
)


@pytest.fixture
def config() -> Config:
    return Config()  # strict defaults: read-only, SELECT-only


@pytest.fixture
def schema() -> SchemaInfo:
    return SAMPLE_SCHEMA


@pytest.fixture
def guard(config: Config, schema: SchemaInfo) -> Guard:
    return Guard(config=config, schema=schema)
