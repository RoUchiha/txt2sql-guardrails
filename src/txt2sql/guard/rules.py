"""Individual guard rules, enforced against the sqlglot AST (never strings).

Each rule returns a list of ``(rule_id, reason)`` violations. An empty list
means the rule passed. Rules are pure functions so they're trivially testable.
"""

from __future__ import annotations

from sqlglot import exp

from txt2sql.config import Config
from txt2sql.guard.parser import statement_type
from txt2sql.models import SchemaInfo

Violation = tuple[str, str]

# AST node classes that represent a data/schema *action*, mapped to the
# statement-type keyword used in the allowlist. Anything here that is not in
# `allowed_statement_types` is blocked — at the root *or* nested (stacked) level.
ACTION_NODES: dict[type, str] = {
    exp.Select: "SELECT",
    exp.Insert: "INSERT",
    exp.Update: "UPDATE",
    exp.Delete: "DELETE",
    exp.Drop: "DROP",
    exp.Create: "CREATE",
    exp.Alter: "ALTER",
    exp.TruncateTable: "TRUNCATE",
    exp.Grant: "GRANT",
    exp.Command: "COMMAND",  # unmodelled: VACUUM, ATTACH, ...
    exp.Pragma: "PRAGMA",
}


def rule_statement_allowlist(
    expr: exp.Expression, schema: SchemaInfo, config: Config
) -> list[Violation]:
    """The root statement type must be in the allowlist (default: SELECT only)."""
    stype = statement_type(expr)
    if stype not in config.allowed_statement_types:
        return [("statement_allowlist", f"statement type {stype} is not allowed")]
    return []


def rule_no_disallowed_nodes(
    expr: exp.Expression, schema: SchemaInfo, config: Config
) -> list[Violation]:
    """Defense in depth: walk the whole tree and block any action node whose
    type is not allowed — catches stacked statements and nested DDL/DML that a
    root-only check would miss."""
    violations: list[Violation] = []
    for node in expr.walk():
        for cls, name in ACTION_NODES.items():
            if isinstance(node, cls) and name not in config.allowed_statement_types:
                violations.append(
                    ("no_disallowed_nodes", f"contains disallowed {name} operation")
                )
                break
    # De-duplicate identical reasons (a query may have several SELECT nodes).
    return list(dict.fromkeys(violations))


def rule_identifier_validation(
    expr: exp.Expression, schema: SchemaInfo, config: Config
) -> list[Violation]:
    """Every referenced table must exist in the schema (or be a CTE). Qualified
    columns referencing a *known* table must name a real column. This blocks
    fishing for tables that aren't in the schema (a common injection tell)."""
    if not schema.tables:
        return []  # no schema provided -> identifier validation disabled

    violations: list[Violation] = []
    known_tables = schema.table_names()
    cte_names = {c.alias_or_name.lower() for c in expr.find_all(exp.CTE)}

    # alias -> real table name, for column qualifier resolution.
    alias_map: dict[str, str] = {}
    for tbl in expr.find_all(exp.Table):
        real = tbl.name
        if tbl.alias:
            alias_map[tbl.alias.lower()] = real.lower()
        if real.lower() not in known_tables and real.lower() not in cte_names:
            violations.append(("identifier_validation", f"unknown table: {real}"))

    for col in expr.find_all(exp.Column):
        qualifier = col.table.lower() if col.table else ""
        if not qualifier:
            continue  # bare column: cannot attribute reliably, skip
        real = alias_map.get(qualifier, qualifier)
        if real in cte_names or real not in known_tables:
            continue  # CTE columns / unknown qualifiers are not validated here
        colname = col.name.lower()
        if colname and colname != "*" and colname not in schema.columns_of(real):
            violations.append(
                ("identifier_validation", f"unknown column: {real}.{col.name}")
            )

    return list(dict.fromkeys(violations))


def rule_no_unfiltered_mutation(
    expr: exp.Expression, schema: SchemaInfo, config: Config
) -> list[Violation]:
    """If writes are enabled, still block UPDATE/DELETE without a WHERE clause —
    a full-table mutation is almost never intended."""
    if not config.block_unfiltered_mutation:
        return []
    if isinstance(expr, (exp.Update, exp.Delete)) and expr.args.get("where") is None:
        return [("no_unfiltered_mutation", "UPDATE/DELETE without WHERE is blocked")]
    return []


# Order matters only for which reason surfaces first; all rules always run.
ALL_RULES = [
    rule_statement_allowlist,
    rule_no_disallowed_nodes,
    rule_identifier_validation,
    rule_no_unfiltered_mutation,
]
