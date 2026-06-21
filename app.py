"""Gradio live demo for txt2sql.

Two tabs:
  1. "Ask in English" — full pipeline: NL -> SQL -> guard -> sandboxed results.
  2. "Test the guard"  — paste raw SQL and watch the AST guardrail rule on it,
     independent of any model. This is the honest way to showcase the block rate:
     throw real attacks straight at the security core.

Runs the deterministic MockProvider — no API keys. Deployable to HF Spaces as-is.
"""

from __future__ import annotations

import os
import sys

# Make the package importable on Spaces without a build step.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import gradio as gr  # noqa: E402
import pandas as pd  # noqa: E402

from txt2sql.config import Config  # noqa: E402
from txt2sql.execute.sandbox import Sandbox, SandboxError  # noqa: E402
from txt2sql.pipeline import Pipeline  # noqa: E402
from txt2sql.sampledb import build  # noqa: E402
from txt2sql.schema.introspect import introspect_sqlite  # noqa: E402

DB_PATH = build("sample.db")
CONFIG = Config()
SCHEMA = introspect_sqlite(DB_PATH)
PIPELINE = Pipeline(schema=SCHEMA, config=CONFIG, db_path=DB_PATH, audit_path=None)

NL_LEGIT = ["top customers by spend", "how many users are there?",
            "most expensive products", "recent orders"]
NL_ATTACKS = ["drop the users table", "delete all users", "wipe the orders"]

SQL_LEGIT = [
    "SELECT name, email FROM users",
    "SELECT COUNT(*) FROM orders",
    "SELECT name, price FROM products ORDER BY price DESC LIMIT 3",
]
SQL_ATTACKS = [
    "SELECT * FROM users; DROP TABLE users",
    "DROP TABLE users",
    "DELETE FROM orders",
    "SELECT id FROM users UNION SELECT name FROM secret_admins",
    "SELECT * FROM sqlite_master",
    "SELECT u.password FROM users u",
    "PRAGMA table_info(users)",
]


def _verdict_md(allowed: bool, reason: str, rules: list[str]) -> str:
    if allowed:
        return f"### 🟢 ALLOWED\n`{reason}`"
    fired = ", ".join(rules)
    return f"### 🔴 BLOCKED\n**Reason:** {reason}\n\n**Rules fired:** `{fired}`"


def _rows_to_df(result) -> pd.DataFrame:
    if result and result.rows:
        return pd.DataFrame(result.rows, columns=result.columns)
    return pd.DataFrame()


async def ask(question: str):
    """Full pipeline path."""
    result = await PIPELINE.run(question)
    v = result.guard
    return result.generated.raw_sql, _verdict_md(v.allowed, v.reason, v.violated_rules), \
        _rows_to_df(result.result)


def check_sql(sql: str):
    """Guard-only path: rule on raw SQL, execute if (and only if) allowed."""
    v = PIPELINE.guard.check(sql)
    df = pd.DataFrame()
    if v.allowed:
        try:
            df = _rows_to_df(Sandbox(DB_PATH, CONFIG).execute(v.normalized_sql or sql))
        except SandboxError as e:
            return _verdict_md(False, str(e), ["sandbox"]), df
    return _verdict_md(v.allowed, v.reason, v.violated_rules), df


SCHEMA_MD = "\n".join(f"- **{t}**({', '.join(cols)})" for t, cols in SCHEMA.tables.items())

with gr.Blocks(title="Text-to-SQL with AST Guardrails", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# 🛡️ Text-to-SQL with AST Guardrails\n"
        "Natural language → SQL, with an **AST-level guard that statically blocks "
        "destructive queries before they execute** — read-only by default, sandboxed, "
        "row- and time-capped. The guard runs *independently of the model*: even a "
        "jailbroken generation cannot get a `DROP` past it.\n\n"
        f"**Demo schema:**\n{SCHEMA_MD}"
    )

    with gr.Tab("Ask in English"):
        with gr.Row():
            q = gr.Textbox(label="Question", placeholder="top customers by spend", scale=4)
            ask_btn = gr.Button("Run", variant="primary", scale=1)
        gr.Examples(NL_LEGIT, inputs=q, label="Legitimate questions")
        gr.Examples(NL_ATTACKS, inputs=q, label="Destructive intent (blocked)")
        sql_out = gr.Code(label="Generated SQL", language="sql")
        v1 = gr.Markdown()
        df1 = gr.Dataframe(label="Results (sandboxed, read-only, row-capped)")
        ask_btn.click(ask, q, [sql_out, v1, df1])
        q.submit(ask, q, [sql_out, v1, df1])

    with gr.Tab("Test the guard (raw SQL)"):
        gr.Markdown("Paste any SQL — including attacks — and watch the AST guard rule on it.")
        with gr.Row():
            raw = gr.Textbox(label="Raw SQL", placeholder="SELECT * FROM users; DROP TABLE users",
                             scale=4)
            chk_btn = gr.Button("Check", variant="primary", scale=1)
        gr.Examples(SQL_LEGIT, inputs=raw, label="Legitimate SQL")
        gr.Examples(SQL_ATTACKS, inputs=raw, label="Attacks (all blocked)")
        v2 = gr.Markdown()
        df2 = gr.Dataframe(label="Results (only if allowed)")
        chk_btn.click(check_sql, raw, [v2, df2])
        raw.submit(check_sql, raw, [v2, df2])


if __name__ == "__main__":
    demo.launch()
