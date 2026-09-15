from __future__ import annotations

import json

import click

from aus_gov_ingest import __version__
from aus_gov_ingest.pipeline import run_ingest
from aus_gov_ingest.sources import SOURCES


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """aus-gov-map ingest — fetch, parse, chunk, embed, upsert."""


@cli.command("run")
@click.option(
    "--source",
    "source_name",
    default="fixture",
    show_default=True,
    type=click.Choice(sorted(SOURCES), case_sensitive=False),
    help="Modular source adapter.",
)
@click.option("--limit", default=0, show_default=True, help="Cap records (0 = no cap).")
@click.option(
    "--path",
    "source_path",
    default=None,
    type=click.Path(exists=False),
    help="Local APH transcript JSON file or directory (aph_transcript_file).",
)
@click.option(
    "--incremental/--full",
    default=False,
    help="Skip hearings whose source_key already exists (Estimates “what's new”).",
)
@click.option("--no-graph", is_flag=True, help="Skip Neo4j upsert.")
@click.option("--dry-run", is_flag=True, help="Fetch/parse only — no database writes.")
def run_cmd(
    source_name: str,
    limit: int,
    source_path: str | None,
    incremental: bool,
    no_graph: bool,
    dry_run: bool,
) -> None:
    """Run an ingest pass. Example: ingest run --source estimates --limit 10"""
    try:
        result = run_ingest(
            source_name,
            limit=limit,
            incremental=incremental,
            write_graph=not no_graph,
            dry_run=dry_run,
            source_path=source_path,
        )
    except Exception as exc:
        click.echo(f"ingest failed: {exc}", err=True)
        raise SystemExit(1) from exc
    click.echo(json.dumps(result.__dict__, default=str, indent=2))


@cli.command("seed")
@click.option("--no-graph", is_flag=True)
def seed_cmd(no_graph: bool) -> None:
    """Load the offline fixture seed into Postgres (and Neo4j if available)."""
    result = run_ingest("fixture", write_graph=not no_graph)
    click.echo(json.dumps(result.__dict__, default=str, indent=2))


@cli.command("graph-init")
def graph_init_cmd() -> None:
    """Apply Neo4j constraints and indexes."""
    from aus_gov_ingest.db.neo4j_graph import Neo4jStore

    store = Neo4jStore()
    store.apply_constraints()
    click.echo("Neo4j constraints applied.")


@cli.command("cron")
@click.option("--limit", default=0)
def cron_cmd(limit: int) -> None:
    """Cron-friendly Estimates incremental pass."""
    from aus_gov_ingest.cron import main

    code = main(limit=limit)
    raise SystemExit(code)


@cli.command("sources")
def sources_cmd() -> None:
    """List source adapters."""
    for name in sorted(SOURCES):
        click.echo(name)


@cli.command("apply-schema")
def apply_schema_cmd() -> None:
    """Apply incremental SQL: analytics views, handbook stubs, demo board."""
    from pathlib import Path

    from aus_gov_ingest.config import settings
    from aus_gov_ingest.db.postgres import PostgresStore

    root = Path(__file__).resolve()
    sql_dir = None
    for parent in root.parents:
        candidate = parent / "infra" / "postgres"
        if candidate.is_dir():
            sql_dir = candidate
            break
    if sql_dir is None:
        raise SystemExit("Could not find infra/postgres")
    files = sorted(
        p
        for p in sql_dir.glob("*.sql")
        if p.name[:3].isdigit() and int(p.name[:3]) >= 4
    )
    files += sorted((sql_dir / "analytics").glob("*.sql")) if (sql_dir / "analytics").is_dir() else []
    store = PostgresStore(dsn=settings.database_url)
    applied = []
    for path in files:
        n = store.apply_sql(path.read_text())
        applied.append({"path": str(path), "statements": n})
    click.echo(json.dumps({"applied": applied}, indent=2))


@cli.command("merge-people")
def merge_people_cmd() -> None:
    """Collapse duplicate people whose core names match after honorifics."""
    from aus_gov_ingest.db.postgres import PostgresStore

    store = PostgresStore()
    click.echo(json.dumps(store.merge_duplicate_people(), indent=2))


@cli.command("seed-demo-board")
def seed_demo_board_cmd() -> None:
    """Pin FOI/procurement chunk hits onto the demo board (idempotent)."""
    from pathlib import Path

    from aus_gov_ingest.config import settings
    from aus_gov_ingest.db.postgres import PostgresStore

    root = Path(__file__).resolve()
    sql_path = None
    for parent in root.parents:
        candidate = parent / "infra" / "postgres" / "006_demo_board.sql"
        if candidate.is_file():
            sql_path = candidate
            break
    if sql_path is None:
        raise SystemExit("Could not find infra/postgres/006_demo_board.sql")
    store = PostgresStore(dsn=settings.database_url)
    n = store.apply_sql(sql_path.read_text())
    click.echo(json.dumps({"ok": True, "sql": str(sql_path), "statements": n}, indent=2))


def main(argv: list[str] | None = None) -> None:
    cli.main(args=argv, prog_name="ingest")


if __name__ == "__main__":
    cli()
