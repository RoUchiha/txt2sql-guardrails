"""Schema-grounded NL->SQL prompt construction."""

from __future__ import annotations

from txt2sql.models import SchemaInfo


def render_schema(schema: SchemaInfo) -> str:
    lines = []
    for table, cols in schema.tables.items():
        col_str = ", ".join(f"{c} {t}" for c, t in cols.items())
        lines.append(f"  {table}({col_str})")
    return "\n".join(lines)


def build_prompt(question: str, schema: SchemaInfo) -> str:
    """Build a prompt that constrains the model to read-only SQL over the schema.

    The `QUESTION:` sentinel lets the MockProvider locate the user's question;
    real providers simply receive the whole instruction.
    """
    return (
        f"You are a SQL assistant for a {schema.dialect} database.\n"
        "Generate a single read-only SELECT query. Do not modify data.\n"
        "Only reference these tables and columns:\n"
        f"{render_schema(schema)}\n\n"
        f"QUESTION: {question}"
    )
