"""Sandboxed execution: the last line of defense, independent of the guard.

- Read-only SQLite connection (`mode=ro`) so a write cannot succeed even if the
  guard were bypassed.
- LIMIT injection so an unbounded SELECT cannot return the whole table.
- Statement timeout via `Connection.interrupt()` from a watchdog thread.
"""

from __future__ import annotations

import sqlite3
import threading
import time

import sqlglot
from loguru import logger
from sqlglot import exp

from txt2sql.config import Config
from txt2sql.models import QueryResult


class SandboxError(Exception):
    """Raised when execution is rejected or fails inside the sandbox."""


def inject_limit(sql: str, dialect: str, row_limit: int) -> str:
    """Add `LIMIT row_limit+1` if the query has no limit. The +1 lets us detect
    truncation. Existing (smaller) limits are respected."""
    parsed = sqlglot.parse_one(sql, dialect=dialect)
    # Only query-shaped statements support LIMIT. Anything else (e.g. a write
    # that reached the sandbox via a hypothetical guard bypass) is passed through
    # unchanged so the read-only connection can reject it.
    if not isinstance(parsed, exp.Query):
        return sql
    if parsed.args.get("limit") is None:
        parsed = parsed.limit(row_limit + 1)
    return parsed.sql(dialect=dialect)


class Sandbox:
    def __init__(self, db_path: str, config: Config) -> None:
        self.db_path = db_path
        self.config = config

    def _connect_ro(self) -> sqlite3.Connection:
        # mode=ro: open existing DB read-only. A write raises OperationalError.
        return sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)

    def execute(self, sql: str) -> QueryResult:
        limited = inject_limit(sql, self.config.dialect, self.config.row_limit)
        conn = self._connect_ro()
        timed_out = threading.Event()

        def _watchdog() -> None:
            time.sleep(self.config.timeout_seconds)
            timed_out.set()
            conn.interrupt()

        timer = threading.Thread(target=_watchdog, daemon=True)
        timer.start()
        start = time.perf_counter()
        try:
            cur = conn.execute(limited)
            fetched = cur.fetchall()
            columns = [d[0] for d in cur.description] if cur.description else []
        except sqlite3.OperationalError as e:
            if timed_out.is_set():
                raise SandboxError(f"query timed out after {self.config.timeout_seconds}s") from e
            # Read-only violation lands here too — belt-and-suspenders.
            raise SandboxError(f"execution rejected: {e}") from e
        finally:
            conn.close()

        elapsed_ms = (time.perf_counter() - start) * 1000
        truncated = len(fetched) > self.config.row_limit
        rows = [list(r) for r in fetched[: self.config.row_limit]]
        logger.debug("sandbox returned {} rows (truncated={})", len(rows), truncated)
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            elapsed_ms=round(elapsed_ms, 2),
        )
