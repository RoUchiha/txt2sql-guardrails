"""SQL parsing via sqlglot. Parsing is a security boundary: anything we cannot
parse into a known AST is rejected rather than guessed at."""

from __future__ import annotations

import sqlglot
from sqlglot import exp


class ParseError(Exception):
    """Raised when SQL cannot be parsed into a single, well-formed statement."""


def parse_statements(sql: str, dialect: str) -> list[exp.Expression]:
    """Parse SQL into a list of top-level statements.

    Returns one expression per statement so the caller can enforce a
    single-statement policy (the classic ``; DROP TABLE`` defense).
    """
    try:
        statements = sqlglot.parse(sql, dialect=dialect)
    except Exception as e:  # sqlglot raises several error subtypes
        raise ParseError(f"unparseable SQL: {e}") from e

    # sqlglot yields None entries for empty fragments (e.g. a trailing ';').
    real = [s for s in statements if s is not None]
    if not real:
        raise ParseError("no executable statement found")
    return real


def statement_type(expr: exp.Expression) -> str:
    """Classify the *root* statement type as an uppercase keyword.

    Unwraps CTEs/subqueries so ``WITH x AS (...) SELECT ...`` is a SELECT.
    Falls back to the node key (e.g. unmodelled commands -> 'COMMAND').
    """
    node = expr
    # `WITH ... SELECT` already parses to a Select; only parenthesised
    # subqueries need unwrapping to find the operative statement.
    while isinstance(node, exp.Subquery):
        node = node.this

    if isinstance(node, exp.Command):
        # e.g. VACUUM / ATTACH that sqlglot leaves as a generic command.
        return str(node.this).upper()

    mapping: dict[type, str] = {
        exp.Select: "SELECT",
        exp.Union: "SELECT",
        exp.Intersect: "SELECT",
        exp.Except: "SELECT",
        exp.Insert: "INSERT",
        exp.Update: "UPDATE",
        exp.Delete: "DELETE",
        exp.Drop: "DROP",
        exp.Create: "CREATE",
        exp.Alter: "ALTER",
        exp.Grant: "GRANT",
        exp.TruncateTable: "TRUNCATE",
    }
    for cls, name in mapping.items():
        if isinstance(node, cls):
            return name
    return node.key.upper()
