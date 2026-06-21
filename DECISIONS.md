# DECISIONS

Assumptions and deviations made during autonomous execution, dated.

## 2026-06-20

- **sqlglot 30.x** is installed (spec pinned `>=25`). AST node names verified against the
  installed version: `exp.Alter` (not `AlterTable`), `exp.TruncateTable`, `exp.Grant`,
  `exp.Pragma` all exist. `WITH … SELECT` parses directly to `exp.Select`.
- **Identifier validation is asymmetric.** Table references are validated strictly (unknown
  table → block). Bare (unqualified) columns are *not* validated, because attributing them
  to a table reliably across joins/subqueries/derived tables is error-prone and would cause
  false blocks on legitimate SELECTs. Qualified columns are validated only when their
  qualifier resolves to a known real table. Rationale: a false *block* is a UX bug; a false
  *allow on an unknown table* is a security hole — so strictness is spent on tables.
- **Allowlist + destructive-node walk are unified** through `ACTION_NODES`: instead of a
  denylist of "bad verbs", any action node whose keyword is not explicitly allowed is
  blocked, at the root and nested. This is why stacked/obfuscated DDL is caught redundantly.
- **Default dialect: sqlite**, matching the default sandbox DB. The guard is dialect-aware
  via sqlglot; Postgres is supported by setting `dialect: postgres` in config.
- **MockProvider is the default** generator so the CLI and tests run offline with no keys.
  A keyword-driven mock maps common NL questions to canned SELECTs and, for demonstrating
  the guard, can be asked to emit a malicious query.
- **Sandbox uses a SQLite read-only URI connection** (`file:...?mode=ro`) plus a
  `LIMIT`-injection and a statement-progress timeout — independent of the guard, so a guard
  bypass still cannot write.
