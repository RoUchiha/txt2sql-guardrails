"""Typer CLI: query / explain / audit."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from txt2sql.config import Config
from txt2sql.models import SchemaInfo
from txt2sql.pipeline import Pipeline
from txt2sql.schema.introspect import introspect_sqlite

app = typer.Typer(add_completion=False, help="Text-to-SQL with AST guardrails.")
console = Console()


@app.callback()
def _configure() -> None:
    """Configure logging at the CLI edge. Library code only emits via loguru;
    the level is controlled by TXT2SQL_LOG_LEVEL (default: WARNING)."""
    logger.remove()
    logger.add(sys.stderr, level=os.environ.get("TXT2SQL_LOG_LEVEL", "WARNING"))


def _load(db: str | None, config_path: str | None) -> tuple[SchemaInfo, Config, str | None]:
    config = Config.load(config_path)
    if db:
        schema = introspect_sqlite(db, dialect=config.dialect)
    else:
        schema = SchemaInfo(dialect=config.dialect)
    return schema, config, db


def _render(result, executed_label: bool = True) -> None:
    verdict = result.guard
    color = "green" if verdict.allowed else "red"
    console.print(f"[bold]Question:[/bold] {result.question}")
    console.print(f"[bold]SQL:[/bold] {result.generated.raw_sql}")
    console.print(f"[bold {color}]Guard: {'ALLOW' if verdict.allowed else 'BLOCK'}[/bold {color}]"
                  f" — {verdict.reason}")
    if verdict.violated_rules:
        console.print(f"[red]Violated rules:[/red] {', '.join(verdict.violated_rules)}")
    if result.result:
        table = Table(show_header=True, header_style="bold cyan")
        for col in result.result.columns:
            table.add_column(str(col))
        for row in result.result.rows:
            table.add_row(*[str(c) for c in row])
        console.print(table)
        if result.result.truncated:
            console.print("[yellow]results truncated to row limit[/yellow]")


@app.command()
def query(
    q: str = typer.Option(..., "--q", help="Natural-language question"),
    db: str = typer.Option(..., "--db", help="Path to SQLite database"),
    config: str = typer.Option(None, "--config", help="YAML config path"),
) -> None:
    """NL -> SQL -> guard -> execute (read-only, sandboxed)."""
    schema, cfg, db_path = _load(db, config)
    pipe = Pipeline(schema=schema, config=cfg, db_path=db_path)
    result = asyncio.run(pipe.run(q, execute=True))
    _render(result)


@app.command()
def explain(
    q: str = typer.Option(..., "--q", help="Natural-language question"),
    db: str = typer.Option(None, "--db", help="Optional DB for schema grounding"),
    config: str = typer.Option(None, "--config", help="YAML config path"),
) -> None:
    """Show generated SQL + guard verdict WITHOUT executing."""
    schema, cfg, _ = _load(db, config)
    pipe = Pipeline(schema=schema, config=cfg, db_path=None)
    result = asyncio.run(pipe.run(q, execute=False))
    _render(result)


@app.command()
def audit(
    path: str = typer.Option("audit.jsonl", "--path", help="Audit log path"),
    limit: int = typer.Option(10, "--limit"),
) -> None:
    """Show recent guard decisions from the audit log."""
    p = Path(path)
    if not p.exists():
        console.print("[yellow]no audit log yet[/yellow]")
        raise typer.Exit(0)
    lines = p.read_text(encoding="utf-8").strip().splitlines()[-limit:]
    table = Table(show_header=True, header_style="bold cyan")
    for col in ("ts", "allowed", "question", "reason"):
        table.add_column(col)
    for line in lines:
        rec = json.loads(line)
        verdict = "[green]ALLOW[/green]" if rec["allowed"] else "[red]BLOCK[/red]"
        table.add_row(rec["ts"], verdict, rec["question"][:40], rec["reason"][:50])
    console.print(table)


if __name__ == "__main__":
    app()
