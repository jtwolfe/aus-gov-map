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
    "--incremental/--full",
    default=False,
    help="Skip hearings whose source_key already exists (Estimates “what's new”).",
)
@click.option("--no-graph", is_flag=True, help="Skip Neo4j upsert.")
@click.option("--dry-run", is_flag=True, help="Fetch/parse only — no database writes.")
def run_cmd(
    source_name: str, limit: int, incremental: bool, no_graph: bool, dry_run: bool
) -> None:
    """Run an ingest pass. Example: ingest run --source estimates --limit 10"""
    try:
        result = run_ingest(
            source_name,
            limit=limit,
            incremental=incremental,
            write_graph=not no_graph,
            dry_run=dry_run,
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


def main(argv: list[str] | None = None) -> None:
    cli.main(args=argv, prog_name="ingest")


if __name__ == "__main__":
    cli()
