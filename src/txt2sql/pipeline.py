"""End-to-end pipeline: NL question -> SQL -> guard -> (maybe) execute.

The ordering is the security invariant: nothing executes until the guard allows
it. Every decision is appended to an audit log.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from txt2sql.config import Config
from txt2sql.generate.generator import Generator
from txt2sql.guard import Guard
from txt2sql.models import PipelineResult, SchemaInfo
from txt2sql.providers.base import LLMProvider
from txt2sql.providers.mock import MockProvider


class Pipeline:
    def __init__(
        self,
        schema: SchemaInfo,
        config: Config | None = None,
        provider: LLMProvider | None = None,
        db_path: str | None = None,
        audit_path: str | None = "audit.jsonl",
    ) -> None:
        self.config = config or Config(dialect=schema.dialect)
        self.schema = schema
        self.generator = Generator(provider or MockProvider())
        self.guard = Guard(self.config, schema)
        self.db_path = db_path
        self.audit_path = audit_path

    async def run(self, question: str, execute: bool = True) -> PipelineResult:
        generated = await self.generator.generate(question, self.schema)
        verdict = self.guard.check(generated.raw_sql)

        result = PipelineResult(question=question, generated=generated, guard=verdict)

        if verdict.allowed and execute and self.db_path:
            # Imported lazily so `explain` works without a DB present.
            from txt2sql.execute.sandbox import Sandbox, SandboxError

            try:
                result.result = Sandbox(self.db_path, self.config).execute(
                    verdict.normalized_sql or generated.raw_sql
                )
                result.executed = True
            except SandboxError as e:
                logger.error("sandbox error: {}", e)
                result.guard = verdict.model_copy(update={"reason": f"{verdict.reason}; {e}"})

        self._audit(result)
        return result

    def _audit(self, result: PipelineResult) -> None:
        if not self.audit_path:
            return
        record = {
            "ts": datetime.now(UTC).isoformat(),
            "question": result.question,
            "sql": result.generated.raw_sql,
            "allowed": result.guard.allowed,
            "reason": result.guard.reason,
            "violated_rules": result.guard.violated_rules,
            "executed": result.executed,
            "row_count": result.result.row_count if result.result else 0,
        }
        with Path(self.audit_path).open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
