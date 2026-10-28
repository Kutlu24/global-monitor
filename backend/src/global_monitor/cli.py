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


@cli.command("verify-translations")
@click.option("--json", "as_json", is_flag=True, help="Emit the full per-row report as JSON.")
def verify_translations_cmd(as_json: bool) -> None:
    """Audit every translated paragraph against its English row: are all figures kept,
    is the text in the right script, is it complete? Read-only."""
    import dataclasses
    import json

    from . import verify_translations as vt

    reports = vt.verify_all()
    summary = vt.summarize(reports)
    if as_json:
        click.echo(json.dumps({"summary": summary, "rows": [dataclasses.asdict(r) for r in reports]}, indent=2,
                              ensure_ascii=False))
        return
    for r in reports:
        if r.clean:
            continue
        issues = [name for name, on in (("same_as_en", r.same_as_en), ("wrong_script", r.wrong_script),
                                         ("truncated", r.truncated)) if on]
        for name, vals in (("scale_diff", r.scale_diff), ("changed", r.changed), ("dropped", r.dropped)):
            if vals:
                issues.append(f"{name}={vals}")
        click.echo(f"[BAD] {r.page_key} [{r.model}] " + " ".join(issues))
    click.echo(json.dumps(summary, ensure_ascii=False))


@cli.command("verify-synthesis")
@click.option("--json", "as_json", is_flag=True, help="Emit the full per-number report as JSON.")
def verify_synthesis_cmd(as_json: bool) -> None:
    """Audit every stored bloc/compare paragraph: does each number in the
    LLM text appear in the figures its prompt was built from? Read-only."""
    import dataclasses
    import json

    from . import verify_synthesis as vs

    reports = vs.verify_all()
    summary = vs.summarize(reports)
    if as_json:
        click.echo(json.dumps({"summary": summary, "pages": [dataclasses.asdict(r) for r in reports]}, indent=2))
        return
    for r in reports:
        bad = [n for n in r.numbers if n.verdict in ("ungrounded", "wrong_metric", "magnitude_error")]
        flag = "ok " if r.clean else "BAD"
        stale = " (stale: data changed since generation)" if r.stale else ""
        click.echo(f"[{flag}] {r.page_key} [{r.model}] {len(r.numbers)} numbers, {len(bad)} unverified{stale}")
        for n in bad:
            click.echo(f"        {n.verdict}: {n.text} {n.detail}")
    click.echo(json.dumps(summary))


@cli.command("tension")
def tension_cmd() -> None:
    """Manually trigger the GDELT-derived tension refresh (tension.py) -
    normally runs on its own 2-hourly schedule (scheduler.py); this is for
    testing/debugging without waiting for the next tick."""
    pipeline.seed()
    count = pipeline.run_tension()
    click.echo(f"tension: {count} scope(s) updated" if count else "tension: no scopes updated (GDELT fetch returned nothing?)")


if __name__ == "__main__":
    cli()
