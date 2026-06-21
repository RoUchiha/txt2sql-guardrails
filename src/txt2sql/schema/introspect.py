"""Reflect a real database into a SchemaInfo the guard can validate against."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect

from txt2sql.models import SchemaInfo


def introspect_sqlite(db_path: str, dialect: str = "sqlite") -> SchemaInfo:
    """Read tables/columns/types from a SQLite database file."""
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    tables: dict[str, dict[str, str]] = {}
    for table in inspector.get_table_names():
        cols = {c["name"]: str(c["type"]) for c in inspector.get_columns(table)}
        tables[table] = cols
    engine.dispose()
    return SchemaInfo(tables=tables, dialect=dialect)
