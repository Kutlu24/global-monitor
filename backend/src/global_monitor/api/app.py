"""FastAPI backend for Global Monitor. Two jobs: (1) own the ETL/data
pipeline (see pipeline.py, ingestion/, aggregate.py, scheduler.py), (2)
expose the minimal JSON API the Astro frontend calls **at build time** (see
frontend/src/lib/data.ts) - not a client-facing API in the browser sense,
though nothing stops it from being read directly. The built Astro output
is mounted last, at "/", via StaticFiles - see the bottom of this file.
"""
from __future__ import annotations

import subprocess
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles

from .. import db, major_economies, pipeline, scheduler
from ..config import frontend_dir, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    sched = scheduler.start()
    yield
    sched.shutdown(wait=False)


app = FastAPI(title="Global Monitor", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/blocs")
def list_blocs() -> list[dict]:
    result = []
    for bloc in db.get_blocs():
        result.append({**asdict(bloc), "aggregates": _bloc_aggregates_payload(bloc.bloc_id),
                        "synthesis": _synthesis_payload(f"bloc:{bloc.bloc_id}")})
    return result


@app.get("/api/blocs/{bloc_id}")
def get_bloc(bloc_id: str) -> dict:
    bloc = db.get_bloc(bloc_id)
    if bloc is None:
        raise HTTPException(404, f"No such bloc: {bloc_id!r}")
    members = db.get_current_members(bloc_id)
    return {**asdict(bloc), "member_count": len(members), "members": sorted(members),
            "aggregates": _bloc_aggregates_payload(bloc_id),
            "synthesis": _synthesis_payload(f"bloc:{bloc_id}")}


@app.get("/api/metrics")
def list_metrics() -> list[dict]:
    return [asdict(m) for m in db.get_metrics()]


@app.get("/api/compare/{bloc_a}/{bloc_b}")
def compare_blocs(bloc_a: str, bloc_b: str) -> dict:
    """Convenience wrapper the frontend's compare pages use instead of two
    separate GET /api/blocs/{id} calls - same underlying data, one round
    trip. Also includes intra-bloc trade flow member_count so the frontend
    can render 'N/A (single-country bloc)' instead of guessing from a
    missing key."""
    a, b = db.get_bloc(bloc_a), db.get_bloc(bloc_b)
    if a is None:
        raise HTTPException(404, f"No such bloc: {bloc_a!r}")
    if b is None:
        raise HTTPException(404, f"No such bloc: {bloc_b!r}")
    return {
        "a": {**asdict(a), "members": sorted(db.get_current_members(bloc_a)),
              "aggregates": _bloc_aggregates_payload(bloc_a)},
        "b": {**asdict(b), "members": sorted(db.get_current_members(bloc_b)),
              "aggregates": _bloc_aggregates_payload(bloc_b)},
        "synthesis": _synthesis_payload(f"compare:{bloc_a}-vs-{bloc_b}"),
        "synthesis_by_dimension": {
            dimension: _synthesis_payload(f"compare:{bloc_a}-vs-{bloc_b}:{dimension}")
            for dimension in ("economic", "trade", "social", "military")
        },
    }


@app.get("/api/countries")
def list_countries() -> list[dict]:
    """The 'major economies' country-comparison module (see
    major_economies.py) - a SEPARATE concept from bloc comparison. Each
    country's OWN latest observations, not a bloc aggregate."""
    return [_country_payload(iso3) for iso3 in major_economies.all_iso3()]


@app.get("/api/countries/{iso3}")
def get_country(iso3: str) -> dict:
    iso3 = iso3.upper()
    if iso3 not in major_economies.all_iso3():
        raise HTTPException(404, f"No such tracked major economy: {iso3!r}")
    return _country_payload(iso3)


def _country_payload(iso3: str) -> dict:
    metrics_values: dict[str, dict] = {}
    for metric in db.get_metrics():
        obs = db.latest_observation(iso3, metric.metric_id)
        if obs is not None and obs.value is not None:
            metrics_values[metric.metric_id] = {"value": obs.value, "period": obs.period}
    return {"iso3": iso3, "name": major_economies.country_name(iso3), "metrics": metrics_values}


@app.get("/api/last-updated")
def last_updated() -> dict:
    """A single, real, site-wide 'data last refreshed' timestamp - used as
    the sitemap's lastmod (see frontend/src/pages/sitemap-*.xml.ts) instead
    of deploy time, per the project plan's SEO section."""
    return {"last_updated": db.latest_data_update()}


def _synthesis_payload(page_key: str) -> dict | None:
    s = db.get_synthesis(page_key)
    if s is None:
        return None
    return {"text": s.text, "provider": s.provider, "generated_at": s.generated_at}


def _bloc_aggregates_payload(bloc_id: str) -> dict[str, dict]:
    """Latest value per metric for one bloc - {metric_id: {value, period,
    member_count}} - the shape the frontend's build-time fetch consumes
    directly."""
    payload: dict[str, dict] = {}
    for metric in db.get_metrics():
        latest = db.latest_bloc_aggregate(bloc_id, metric.metric_id)
        if latest is not None:
            payload[metric.metric_id] = {
                "value": latest.value, "period": latest.period, "member_count": latest.member_count,
            }
    return payload


def _check_admin_token(authorization: str | None) -> None:
    if not settings.admin_token:
        raise HTTPException(503, "ADMIN_TOKEN is not configured")
    expected = f"Bearer {settings.admin_token}"
    if authorization != expected:
        raise HTTPException(401, "Invalid or missing admin token")


@app.post("/api/admin/rebuild")
def admin_rebuild(authorization: str | None = Header(default=None)) -> dict:
    """Manual trigger for 'run every ETL source, re-aggregate, rebuild the
    static site' - for forcing a rebuild after e.g. manually fixing a SIPRI
    parse issue. scheduler.py does this automatically on its own cadence;
    this exists for the human-in-the-loop case that doesn't wait for it."""
    _check_admin_token(authorization)
    results = pipeline.run_all()
    build = subprocess.run(["npm", "run", "build"], cwd=frontend_dir(), capture_output=True, text=True)
    if build.returncode != 0:
        raise HTTPException(500, f"astro build failed:\n{build.stderr[-2000:]}")
    return {"status": "rebuilt", "ingest_results": results}


_FRONTEND_DIST_DIR = frontend_dir() / "dist"
# check_dir=False: on a fresh boot uvicorn starts (and this module is
# imported) BEFORE the entrypoint's ingest+build step has created dist/ -
# gating the mount on dist.exists() at import time meant the mount was
# silently skipped forever for that process's lifetime, 404ing every page
# until someone noticed and restarted the container (confirmed live
# 2026-09-27 on a truly fresh boot). StaticFiles with check_dir=False does
# its directory/file lookup per-request instead of once at construction, so
# requests start succeeding as soon as the build finishes - no restart
# needed.
app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST_DIR), html=True, check_dir=False), name="frontend")
