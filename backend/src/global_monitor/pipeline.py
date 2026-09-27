"""The actual ingest-all-sources-then-aggregate logic, shared by `cli.py`
(manual/scheduled invocation) and `api/app.py`'s admin_rebuild endpoint
(human-triggered) - kept in one place so neither can drift from the other.
"""
from __future__ import annotations

import logging

from . import aggregate, blocs, db, major_economies, metrics, synthesis
from .ingestion import comtrade, sipri, undp_hdi, worldbank

logger = logging.getLogger(__name__)

CURRENT_PERIOD = "2023"  # UN Comtrade's most recent generally-complete annual data year
SOURCES = ["worldbank", "comtrade", "undp_hdi", "sipri"]


def seed() -> None:
    blocs.seed()
    major_economies.seed()
    metrics.seed()


def all_tracked_iso3() -> list[str]:
    """Union of every bloc member and every major-economy country - the
    ingestion universe. Adding a country to either blocs.py or
    major_economies.py is the only change needed to also pull its data."""
    return sorted(set(blocs.all_tracked_iso3()) | set(major_economies.all_iso3()))


def run_source(source: str, iso3_list: list[str]) -> int:
    """Returns the number of observations/flows stored. Raises on an
    unknown source name; a real fetch failure is caught by the caller
    (run_all), not here, so a single source's error never blocks others."""
    if source == "worldbank":
        observations = worldbank.fetch(iso3_list)
        db.upsert_observations(observations)
        return len(observations)
    if source == "comtrade":
        comtrade.reset_breaker()
        observations = comtrade.fetch_world_totals(iso3_list, CURRENT_PERIOD)
        db.upsert_observations(observations)
        count = len(observations)
        for bloc in db.get_blocs():
            members = db.get_current_members(bloc.bloc_id)
            flows = comtrade.fetch_intra_bloc_flows(bloc.bloc_id, members, CURRENT_PERIOD)
            db.upsert_trade_flows(flows)
            count += len(flows)
        return count
    if source == "undp_hdi":
        observations = undp_hdi.fetch(iso3_list)
        db.upsert_observations(observations)
        return len(observations)
    if source == "sipri":
        observations = sipri.fetch(iso3_list)
        db.upsert_observations(observations)
        return len(observations)
    raise ValueError(
        f"Unknown source {source!r}. Implemented: {', '.join(SOURCES)} "
        f"(OECD/IMF DataMapper are not yet implemented - see README)."
    )


def run_all(sources: list[str] | None = None) -> dict[str, int]:
    """Each source's failure is isolated - one erroring source never blocks
    the others or crashes the whole run (matters most for sipri, the
    fragile one - see its own module docstring)."""
    seed()
    iso3_list = all_tracked_iso3()
    results: dict[str, int] = {}
    for source in sources or SOURCES:
        try:
            results[source] = run_source(source, iso3_list)
        except Exception:
            logger.exception("[%s] ingest failed, continuing with other sources", source)
            results[source] = -1
    aggregate.aggregate_all()
    try:
        synthesis.generate_all()
    except Exception:
        logger.exception("synthesis generation failed - leaving prior text in place, not crashing the ingest run")
    run_tension()
    return results


def run_tension() -> int:
    """Refreshes the real-time GDELT-derived tension module (tension.py) -
    called both from run_all() (so a fresh container boot has tension data
    immediately, not just after the first scheduled 2-hourly tick) AND from
    scheduler.py's own separate, more frequent job - hours-scale data needs
    a much shorter refresh cadence than the daily/weekly structural
    indicators above, so it isn't gated on SOURCES/run_source at all."""
    from . import tension

    try:
        count = tension.refresh_all()
    except Exception:
        logger.exception("tension refresh failed, leaving prior tension data in place")
        return 0
    if count == 0:
        return 0
    try:
        bloc_by_id = {b.bloc_id: b for b in db.get_blocs()}
        synthesis.generate_tension_synthesis(bloc_by_id)
    except Exception:
        logger.exception("tension synthesis failed - leaving prior text in place")
    return count
