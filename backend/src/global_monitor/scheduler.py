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


def start(scheduler: AsyncIOScheduler | None = None) -> AsyncIOScheduler:
    scheduler = scheduler or AsyncIOScheduler()
    scheduler.add_job(_run_and_maybe_rebuild, "cron", hour=3, kwargs={"sources": ["worldbank", "comtrade"]},
                       id="daily-ingest", replace_existing=True)
    scheduler.add_job(_run_and_maybe_rebuild, "cron", day_of_week="mon", hour=4,
                       kwargs={"sources": ["undp_hdi", "sipri"]}, id="weekly-ingest", replace_existing=True)
    scheduler.start()
    return scheduler
