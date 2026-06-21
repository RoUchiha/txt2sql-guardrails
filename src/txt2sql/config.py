"""Configuration models and YAML loading.

Security defaults are intentionally strict: read-only, SELECT-only, row + time
capped. Loosening any of these is an explicit, auditable choice.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    """Runtime policy for generation, guarding, and sandboxed execution."""

    read_only: bool = True
    # Allowlist of statement *types* permitted by the guard. SELECT only by default.
    allowed_statement_types: list[str] = Field(default_factory=lambda: ["SELECT"])
    dialect: str = "sqlite"

    # Sandbox limits.
    row_limit: int = 100
    timeout_seconds: float = 5.0
    max_query_length: int = 10_000

    # Defense-in-depth: if writes are ever enabled, still block unqualified mutations.
    block_unfiltered_mutation: bool = True

    @field_validator("allowed_statement_types", mode="before")
    @classmethod
    def _upper(cls, v: list[str]) -> list[str]:
        return [s.upper() for s in v]

    @classmethod
    def load(cls, path: str | Path | None) -> Config:
        """Load config from a YAML file, or return strict defaults if path is None."""
        if path is None:
            return cls()
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(**data)
