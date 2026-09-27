"""CLI entry points - mirrors GFCA's `cli.py` shape (click-based). Milestone
1 scope: `ingest worldbank` (and `ingest all`, currently equivalent) plus
the seeding step every ingest run needs. `ingest sipri`/etc. and
`rebuild-frontend`/`synthesize` land in later milestones."""
from __future__ import annotations

import click

from . import aggregate, blocs, db, metrics
from .ingestion import worldbank


def _seed() -> None:
    blocs.seed()
    metrics.seed()


@click.group()
def cli() -> None:
    pass


@cli.command("ingest")
@click.argument("source", default="all")
def ingest(source: str) -> None:
    """Fetch fresh data from one source (or `all`), then re-run bloc-level
    aggregation. Idempotent - safe to run repeatedly."""
    _seed()
    iso3_list = blocs.all_tracked_iso3()

    if source in ("all", "worldbank"):
        click.echo(f"[worldbank] fetching {len(iso3_list)} countries...")
        observations = worldbank.fetch(iso3_list)
        db.upsert_observations(observations)
        click.echo(f"[worldbank] stored {len(observations)} observations")
    elif source != "all":
        raise click.ClickException(
            f"Unknown source {source!r}. Only 'worldbank' is implemented in Milestone 1."
        )

    click.echo("aggregating...")
    aggregate.aggregate_all()
    click.echo("done")


@cli.command("seed")
def seed_cmd() -> None:
    """Seed blocs/countries/membership/metrics only, no network calls -
    useful for a fast local smoke test of the schema."""
    _seed()
    click.echo("seeded blocs, countries, membership, metrics")


if __name__ == "__main__":
    cli()
