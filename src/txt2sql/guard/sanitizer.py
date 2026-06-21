"""The Guard: turns raw SQL into an allow/block verdict.

This runs *independently of the LLM*. Even a fully jailbroken generation must
pass through `Guard.check()` before anything touches the database, so a
malicious model cannot bypass it.
"""

from __future__ import annotations

from loguru import logger

from txt2sql.config import Config
from txt2sql.guard.parser import ParseError, parse_statements
from txt2sql.guard.rules import ALL_RULES, Violation
from txt2sql.models import GuardResult, SchemaInfo


class Guard:
    def __init__(self, config: Config, schema: SchemaInfo | None = None) -> None:
        self.config = config
        self.schema = schema or SchemaInfo(dialect=config.dialect)

    def check(self, sql: str) -> GuardResult:
        """Return a verdict. `allowed=True` only if every layer passes."""
        sql = (sql or "").strip()

        if not sql:
            return self._block(["empty"], "empty query", None)

        if len(sql) > self.config.max_query_length:
            return self._block(["max_length"], "query exceeds max length", None)

        # Layer 1: parse or reject.
        try:
            statements = parse_statements(sql, self.config.dialect)
        except ParseError as e:
            return self._block(["parse"], str(e), None)

        # Layer 2: single statement only (kills `; DROP TABLE` stacking).
        if len(statements) > 1:
            return self._block(
                ["single_statement"],
                f"multiple statements not allowed ({len(statements)} found)",
                None,
            )

        expr = statements[0]

        # Layers 3-6: run every rule against the AST.
        violations: list[Violation] = []
        for rule in ALL_RULES:
            violations.extend(rule(expr, self.schema, self.config))

        if violations:
            rule_ids = list(dict.fromkeys(v[0] for v in violations))
            reason = "; ".join(dict.fromkeys(v[1] for v in violations))
            logger.warning("guard blocked query: {}", reason)
            return GuardResult(
                allowed=False, reason=reason, violated_rules=rule_ids, normalized_sql=None
            )

        normalized = expr.sql(dialect=self.config.dialect)
        logger.debug("guard allowed query: {}", normalized)
        return GuardResult(allowed=True, reason="ok", normalized_sql=normalized)

    def _block(self, rules: list[str], reason: str, normalized: str | None) -> GuardResult:
        logger.warning("guard blocked query: {}", reason)
        return GuardResult(
            allowed=False, reason=reason, violated_rules=rules, normalized_sql=normalized
        )
