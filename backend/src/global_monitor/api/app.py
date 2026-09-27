"""FastAPI backend for Global Monitor. Two jobs: (1) own the ETL/data
pipeline (see ingestion/, aggregate.py, cli.py), (2) expose the minimal
JSON API the Astro frontend calls **at build time** (see
frontend/src/lib/data.ts) - not a client-facing API in the browser sense,
though nothing stops it from being read directly. The built Astro output
is mounted last, at "/", via StaticFiles - see the bottom of this file.
"""
from __future__ import annotations

import subprocess
from dataclasses import asdict

from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles

from .. import aggregate, blocs, db, metrics
from ..config import frontend_dir, settings
from ..ingestion import worldbank

app = FastAPI(title="Global Monitor")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/blocs")
def list_blocs() -> list[dict]:
    result = []
    for bloc in db.get_blocs():
        result.append({**asdict(bloc), "aggregates": _bloc_aggregates_payload(bloc.bloc_id)})
    return result


@app.get("/api/blocs/{bloc_id}")
def get_bloc(bloc_id: str) -> dict:
    bloc = db.get_bloc(bloc_id)
    if bloc is None:
        raise HTTPException(404, f"No such bloc: {bloc_id!r}")
    members = db.get_current_members(bloc_id)
    return {**asdict(bloc), "member_count": len(members),
            "aggregates": _bloc_aggregates_payload(bloc_id)}


@app.get("/api/metrics")
def list_metrics() -> list[dict]:
    return [asdict(m) for m in db.get_metrics()]


def _bloc_aggregates_payload(bloc_id: str) -> dict[str, dict]:
    """Latest value per metric for one bloc - {metric_id: {value, period,
    member_count}} - the shape the frontend's build-time fetch consumes
    directly for the walking-skeleton homepage."""
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
        raise HTTPException(503, "GLOBAL_MONITOR_ADMIN_TOKEN is not configured")
    expected = f"Bearer {settings.admin_token}"
    if authorization != expected:
        raise HTTPException(401, "Invalid or missing admin token")


@app.post("/api/admin/rebuild")
def admin_rebuild(authorization: str | None = Header(default=None)) -> dict:
    """Manual trigger for 'run ETL, re-aggregate, rebuild the static site' -
    for forcing a rebuild after e.g. manually fixing a SIPRI parse issue
    (`cli.py ingest sipri`). The scheduler (Milestone 2) does this
    automatically after any run that actually changes values; this exists
    for the human-in-the-loop case that doesn't wait for the schedule."""
    _check_admin_token(authorization)
    blocs.seed()
    metrics.seed()
    observations = worldbank.fetch(blocs.all_tracked_iso3())
    db.upsert_observations(observations)
    aggregate.aggregate_all()
    result = subprocess.run(["npm", "run", "build"], cwd=frontend_dir(), capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(500, f"astro build failed:\n{result.stderr[-2000:]}")
    return {"status": "rebuilt", "observations_ingested": len(observations)}


_FRONTEND_DIST_DIR = frontend_dir() / "dist"
if _FRONTEND_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST_DIR), html=True), name="frontend")
