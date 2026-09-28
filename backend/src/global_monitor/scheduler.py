"""In-process job scheduler - a NEW pattern for this portfolio (no other
app in ~/my-projects has one; every other app is pure request/response).
Started from FastAPI's lifespan (see api/app.py), not a separate
container/cron - keeps Global Monitor a single docker-compose service like
every sibling app.

Cadences (see the project plan): daily for the sources that can genuinely
change often (World Bank, Comtrade); weekly for the ones that only update
a few times a year at most (UNDP HDI, SIPRI) - checking them daily would
just be wasted network calls against a source that hasn't changed.

After any run that stores at least one row, rebuilds the Astro frontend so
the static site actually reflects the new numbers - see api/app.py's
admin_rebuild for the same rebuild step, human-triggered instead of
scheduled.
"""
from __future__ import annotations

import logging
import subprocess
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import pipeline
from .config import frontend_dir

logger = logging.getLogger(__name__)


def _rebuild_frontend() -> None:
    result = subprocess.run(["npm", "run", "build"], cwd=frontend_dir(), capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("astro build failed after scheduled ingest:\n%s", result.stderr[-2000:])
    else:
        logger.info("astro build completed after scheduled ingest")


def _run_and_maybe_rebuild(sources: list[str]) -> None:
    results = pipeline.run_all(sources)
    total_stored = sum(count for count in results.values() if count > 0)
    logger.info("scheduled ingest %s -> %s", sources, results)
    if total_stored > 0:
        _rebuild_frontend()


def _run_tension_and_maybe_rebuild() -> None:
    """Separate, much more frequent job than the structural-indicator ones
    above - tension.py's GDELT data is hours-scale, not annual/quarterly
    (see its own module docstring). The ongoing refresh needs its own
    cadence, independent of the daily/weekly World Bank/Comtrade/UNDP/SIPRI
    cycle - see start()'s own comment on why this ALSO needs to fire
    immediately on every boot, not just every 2 hours."""
    count = pipeline.run_tension()
    logger.info("scheduled tension refresh -> %s scope(s) updated", count)
    if count > 0:
        _rebuild_frontend()


def start(scheduler: AsyncIOScheduler | None = None) -> AsyncIOScheduler:
    scheduler = scheduler or AsyncIOScheduler()
    scheduler.add_job(_run_and_maybe_rebuild, "cron", hour=3, kwargs={"sources": ["worldbank", "comtrade"]},
                       id="daily-ingest", replace_existing=True)
    scheduler.add_job(_run_and_maybe_rebuild, "cron", day_of_week="mon", hour=4,
                       kwargs={"sources": ["undp_hdi", "sipri"]}, id="weekly-ingest", replace_existing=True)
    # worldbank_risk is the widest and slowest source - 211 countries x 20
    # indicators, ~120 paginated requests. All three of its publishers (WDI,
    # IMF WEO, UNDP HDR) update annually or semi-annually, so monthly is far
    # more often than the data can have changed.
    #
    # It used to be reachable ONLY from the entrypoint's unconditional
    # `ingest all` on every container start, which meant it re-pulled the
    # world on every restart. worldbank.risk_inputs_fresh() now makes those
    # restarts a no-op, and this job is what actually keeps it current.
    scheduler.add_job(_run_and_maybe_rebuild, "cron", day=1, hour=5,
                       kwargs={"sources": ["worldbank_risk"]}, id="monthly-risk-ingest",
                       replace_existing=True)
    # next_run_time=now: an interval trigger's default first run is
    # now+interval, not immediate - confirmed live (2026-09-27), this left
    # tension.py's in-memory `_last_events` cache (needed by the ad-hoc
    # two-country query endpoint) empty for up to 2 hours after every
    # container boot/restart. pipeline.run_all() at the entrypoint's own
    # "ingest all" call does populate the DB-persisted bloc/pair scores
    # immediately, but that runs as a SEPARATE CLI subprocess - it can
    # never reach this server process's own in-memory cache. Firing this
    # job immediately, in-process, on every start is the only way to fix
    # that gap, not just widen it.
    scheduler.add_job(_run_tension_and_maybe_rebuild, "interval", hours=2,
                       id="tension-refresh", replace_existing=True, next_run_time=datetime.now())
    scheduler.start()
    return scheduler
