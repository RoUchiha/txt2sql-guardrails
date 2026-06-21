# txt2sql — Text-to-SQL with AST Guardrails

**🔴 [Live demo on Hugging Face Spaces](https://huggingface.co/spaces/rosingh/txt2sql-guardrails)** — paste an attack and watch it get blocked.

Natural-language → SQL with a **hard guardrail layer that statically blocks destructive
or unsafe SQL before it can execute**. The guard works on the **sqlglot AST** (never regex),
runs **independently of the LLM**, and is read-only by default with sandboxed execution
(row + time limits).

> **Headline guarantee:** 100% block rate on an adversarial corpus of stacked statements,
> obfuscated DDL, fishing/injection, and full-table mutations — enforced by a test that
> fails the build if a single attack slips through.

## Why this design

A jailbroken or malicious LLM generation **cannot bypass the guard** — every query passes
through `Guard.check()` before anything touches the database. Defense is layered:

| Layer | Rule | Stops |
|-------|------|-------|
| 1 | Parse or reject | unparseable / malformed SQL |
| 2 | Single statement only | `; DROP TABLE` stacking |
| 3 | Statement-type allowlist (SELECT only) | INSERT/UPDATE/DELETE/DDL at the root |
| 4 | No disallowed action nodes (full AST walk) | nested / stacked DDL & DML |
| 5 | Identifier validation vs real schema | fishing for tables that don't exist (`sqlite_master`, `secret_*`) |
| 6 | No unfiltered mutation (if writes enabled) | `DELETE`/`UPDATE` without `WHERE` |
| 7 | Sandbox | read-only connection, injected `LIMIT`, statement timeout |

## Quickstart

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -e ".[dev]"

# Build the demo database
python -m txt2sql.sampledb            # writes sample.db

# Ask a question (NL -> SQL -> guard -> execute)
txt2sql query --db sample.db --q "top 5 customers by total spend"

# See the SQL + guard verdict WITHOUT executing
txt2sql explain --q "delete everything from users"

# Recent audit decisions
txt2sql audit
```

The default provider is a deterministic **MockProvider**, so the CLI and the whole test
suite run **offline with no API keys**. Plug in a real model via the provider abstraction.

## Run the tests / security gate

```bash
pytest                         # full suite
pytest tests/attacks -q        # the 100%-block-rate security gate
pytest --cov=txt2sql           # coverage (≥90% on guard/)
```

## Live demo

A Gradio app (`app.py`) exposes the pipeline in the browser: type a question, watch the
generated SQL, the guard verdict (allow/block + reason), and results. Try an attack and
watch it get blocked. Deployable to Hugging Face Spaces (`requirements.txt` included).

```bash
pip install -e ".[demo]"
python app.py
```

## Enabling writes (carefully)

Writes are off by default. To allow them, set in your config YAML:

```yaml
read_only: false
allowed_statement_types: [SELECT, INSERT, UPDATE]
block_unfiltered_mutation: true   # still blocks WHERE-less mutations
```

Even then, the read-only sandbox connection is a separate belt-and-suspenders layer.

## Project layout

```
src/txt2sql/
  config.py       # strict-by-default policy (YAML -> Pydantic)
  models.py       # SchemaInfo, GeneratedSQL, GuardResult, QueryResult
  schema/         # DB introspection -> SchemaInfo
  generate/       # schema-grounded NL->SQL (mockable provider)
  guard/          # parser + rules + sanitizer  <-- security core
  execute/        # read-only sandbox w/ LIMIT + timeout
  pipeline.py     # NL -> SQL -> guard -> execute, with audit log
  cli.py          # query / explain / audit
tests/attacks/    # adversarial corpus (the gate)
```

See [DECISIONS.md](DECISIONS.md) for assumptions and trade-offs.
