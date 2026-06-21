"""Pydantic v2 data models for the txt2sql pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SchemaInfo(BaseModel):
    """A snapshot of the database schema the guard validates identifiers against."""

    # table name -> {column name -> type}
    tables: dict[str, dict[str, str]] = Field(default_factory=dict)
    dialect: str = "sqlite"

    def table_names(self) -> set[str]:
        return {t.lower() for t in self.tables}

    def columns_of(self, table: str) -> set[str]:
        for name, cols in self.tables.items():
            if name.lower() == table.lower():
                return {c.lower() for c in cols}
        return set()


class GeneratedSQL(BaseModel):
    """Raw output of the NL->SQL generator (untrusted until guarded)."""

    raw_sql: str
    explanation: str = ""


class GuardResult(BaseModel):
    """Verdict from the guard. `allowed` is the only thing execution may trust."""

    allowed: bool
    reason: str = ""
    violated_rules: list[str] = Field(default_factory=list)
    normalized_sql: str | None = None


class QueryResult(BaseModel):
    """Result of a sandboxed execution."""

    columns: list[str] = Field(default_factory=list)
    rows: list[list] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    elapsed_ms: float = 0.0


class PipelineResult(BaseModel):
    """End-to-end record: question -> sql -> verdict -> (maybe) rows."""

    question: str
    generated: GeneratedSQL
    guard: GuardResult
    executed: bool = False
    result: QueryResult | None = None
