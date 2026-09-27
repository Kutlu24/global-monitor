"""CLI entry points - mirrors GFCA's `cli.py` shape (click-based). Actual
ingest/aggregate logic lives in pipeline.py, shared with api/app.py's
admin_rebuild endpoint."""
from __future__ import annotations

import click

from . import pipeline


@click.group()
def cli() -> None:
    pass


@cli.command("ingest")
@click.argument("source", default="all")
def ingest(source: str) -> None:
    """Fetch fresh data from one source (or `all`), then re-run bloc-level
    aggregation. Idempotent - safe to run repeatedly."""
    sources = None if source == "all" else [source]
    results = pipeline.run_all(sources)
    for src, count in results.items():
        if count < 0:
            click.echo(f"[{src}] FAILED (see logs)", err=True)
        else:
            click.echo(f"[{src}] stored {count} row(s)")
    click.echo("done")


@cli.command("seed")
def seed_cmd() -> None:
    """Seed blocs/countries/membership/metrics only, no network calls -
    useful for a fast local smoke test of the schema."""
    pipeline.seed()
    click.echo("seeded blocs, countries, membership, metrics")


if __name__ == "__main__":
    cli()
