"""Thin SQLite layer, no ORM - same convention as every other persistence
layer in this portfolio (ottoman-rag, fundraising-assistant, dhra). Data
volume here is tiny (a handful of blocs, ~30 countries, ~20 metrics, yearly/
quarterly periods) - plain sqlite3 with GROUP BY is entirely sufficient."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import json

from .config import db_path
from .models import (
    Bloc, BlocAggregate, BlocMembership, BlocTradeFlow, Country, Metric, Observation,
    SynthesisText, TensionScore,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS blocs (
    bloc_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS countries (
    iso3 TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bloc_membership (
    bloc_id TEXT NOT NULL REFERENCES blocs(bloc_id),
    iso3 TEXT NOT NULL REFERENCES countries(iso3),
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    PRIMARY KEY (bloc_id, iso3, effective_from)
);
CREATE TABLE IF NOT EXISTS metrics (
    metric_id TEXT PRIMARY KEY,
    dimension TEXT NOT NULL CHECK (dimension IN ('economic','trade','social','military')),
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    source TEXT NOT NULL,
    source_dataset_code TEXT,
    license TEXT,
    update_cadence TEXT NOT NULL CHECK (update_cadence IN ('continuous','quarterly','annual')),
    default_aggregation TEXT NOT NULL CHECK (default_aggregation IN ('sum','mean','weighted_mean')),
    weight_metric_id TEXT REFERENCES metrics(metric_id)
);
CREATE TABLE IF NOT EXISTS observations (
    iso3 TEXT NOT NULL REFERENCES countries(iso3),
    metric_id TEXT NOT NULL REFERENCES metrics(metric_id),
    period TEXT NOT NULL,
    value REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (iso3, metric_id, period)
);
CREATE TABLE IF NOT EXISTS bloc_trade_flows (
    bloc_id TEXT NOT NULL REFERENCES blocs(bloc_id),
    reporter_iso3 TEXT NOT NULL,
    partner_iso3 TEXT NOT NULL,
    metric_id TEXT NOT NULL REFERENCES metrics(metric_id),
    period TEXT NOT NULL,
    value REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (bloc_id, reporter_iso3, partner_iso3, metric_id, period)
);
CREATE TABLE IF NOT EXISTS bloc_aggregates (
    bloc_id TEXT NOT NULL REFERENCES blocs(bloc_id),
    metric_id TEXT NOT NULL REFERENCES metrics(metric_id),
    period TEXT NOT NULL,
    value REAL,
    member_count INTEGER NOT NULL,
    computed_at TEXT NOT NULL,
    PRIMARY KEY (bloc_id, metric_id, period)
);
CREATE TABLE IF NOT EXISTS synthesis_text (
    page_key TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    data_hash TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tension_scores (
    scope TEXT PRIMARY KEY,
    window_hours REAL NOT NULL,
    n_events INTEGER NOT NULL,
    mean_goldstein REAL,
    mean_tone REAL,
    verbal_cooperation INTEGER NOT NULL,
    material_cooperation INTEGER NOT NULL,
    verbal_conflict INTEGER NOT NULL,
    material_conflict INTEGER NOT NULL,
    conflict_share REAL,
    goldstein_delta REAL,
    examples_json TEXT NOT NULL DEFAULT '[]',
    computed_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_bloc(bloc: Bloc) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO blocs (bloc_id, name, slug, description) VALUES (?, ?, ?, ?)
               ON CONFLICT(bloc_id) DO UPDATE SET name=excluded.name, slug=excluded.slug,
                   description=excluded.description""",
            (bloc.bloc_id, bloc.name, bloc.slug, bloc.description),
        )


def upsert_country(country: Country) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO countries (iso3, name) VALUES (?, ?)
               ON CONFLICT(iso3) DO UPDATE SET name=excluded.name""",
            (country.iso3, country.name),
        )


def upsert_membership(m: BlocMembership) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO bloc_membership (bloc_id, iso3, effective_from, effective_to)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(bloc_id, iso3, effective_from) DO UPDATE SET effective_to=excluded.effective_to""",
            (m.bloc_id, m.iso3, m.effective_from, m.effective_to),
        )


def upsert_metric(metric: Metric) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO metrics (metric_id, dimension, name, unit, source, source_dataset_code,
                   license, update_cadence, default_aggregation, weight_metric_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(metric_id) DO UPDATE SET dimension=excluded.dimension, name=excluded.name,
                   unit=excluded.unit, source=excluded.source,
                   source_dataset_code=excluded.source_dataset_code, license=excluded.license,
                   update_cadence=excluded.update_cadence,
                   default_aggregation=excluded.default_aggregation,
                   weight_metric_id=excluded.weight_metric_id""",
            (
                metric.metric_id, metric.dimension, metric.name, metric.unit, metric.source,
                metric.source_dataset_code, metric.license, metric.update_cadence,
                metric.default_aggregation, metric.weight_metric_id,
            ),
        )


def upsert_observations(observations: list[Observation]) -> None:
    if not observations:
        return
    with _conn() as conn:
        conn.executemany(
            """INSERT INTO observations (iso3, metric_id, period, value, fetched_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(iso3, metric_id, period) DO UPDATE SET value=excluded.value,
                   fetched_at=excluded.fetched_at""",
            [(o.iso3, o.metric_id, o.period, o.value, o.fetched_at) for o in observations],
        )


def upsert_trade_flows(flows: list[BlocTradeFlow]) -> None:
    if not flows:
        return
    with _conn() as conn:
        conn.executemany(
            """INSERT INTO bloc_trade_flows
                   (bloc_id, reporter_iso3, partner_iso3, metric_id, period, value, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(bloc_id, reporter_iso3, partner_iso3, metric_id, period)
                   DO UPDATE SET value=excluded.value, fetched_at=excluded.fetched_at""",
            [(f.bloc_id, f.reporter_iso3, f.partner_iso3, f.metric_id, f.period, f.value, f.fetched_at)
             for f in flows],
        )


def upsert_bloc_aggregate(agg: BlocAggregate) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO bloc_aggregates (bloc_id, metric_id, period, value, member_count, computed_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(bloc_id, metric_id, period) DO UPDATE SET value=excluded.value,
                   member_count=excluded.member_count, computed_at=excluded.computed_at""",
            (agg.bloc_id, agg.metric_id, agg.period, agg.value, agg.member_count, agg.computed_at),
        )


def get_blocs() -> list[Bloc]:
    with _conn() as conn:
        rows = conn.execute("SELECT bloc_id, name, slug, description FROM blocs ORDER BY bloc_id").fetchall()
        return [Bloc(**dict(r)) for r in rows]


def get_all_countries() -> list[Country]:
    """Every tracked country (bloc members + major economies) with a real
    name - the reference list for the Tension module's ad-hoc two-country
    query picker (tension.py's `query_pair`), not a bloc-scoped list."""
    with _conn() as conn:
        rows = conn.execute("SELECT iso3, name FROM countries ORDER BY name").fetchall()
        return [Country(**dict(r)) for r in rows]


def get_bloc(bloc_id: str) -> Bloc | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT bloc_id, name, slug, description FROM blocs WHERE bloc_id = ?", (bloc_id,)
        ).fetchone()
        return Bloc(**dict(row)) if row else None


def get_current_members(bloc_id: str, as_of: str | None = None) -> list[str]:
    """ISO3 codes of a bloc's members as of a given date (default: today) -
    respects effective_from/effective_to so historical periods can use
    historical membership (see aggregate.py)."""
    as_of = as_of or now()[:10]
    with _conn() as conn:
        rows = conn.execute(
            """SELECT iso3 FROM bloc_membership
               WHERE bloc_id = ? AND effective_from <= ? AND (effective_to IS NULL OR effective_to > ?)""",
            (bloc_id, as_of, as_of),
        ).fetchall()
        return [r["iso3"] for r in rows]


def get_metrics() -> list[Metric]:
    with _conn() as conn:
        rows = conn.execute(
            """SELECT metric_id, dimension, name, unit, source, source_dataset_code, license,
                      update_cadence, default_aggregation, weight_metric_id
               FROM metrics ORDER BY dimension, metric_id"""
        ).fetchall()
        return [Metric(**dict(r)) for r in rows]


def get_observations(metric_id: str, iso3_list: list[str], period: str | None = None) -> list[Observation]:
    if not iso3_list:
        return []
    placeholders = ",".join("?" * len(iso3_list))
    query = f"""SELECT iso3, metric_id, period, value, fetched_at FROM observations
                WHERE metric_id = ? AND iso3 IN ({placeholders})"""
    params: list[str] = [metric_id, *iso3_list]
    if period:
        query += " AND period = ?"
        params.append(period)
    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [Observation(**dict(r)) for r in rows]


def get_trade_flows(bloc_id: str, metric_id: str) -> list[BlocTradeFlow]:
    with _conn() as conn:
        rows = conn.execute(
            """SELECT bloc_id, reporter_iso3, partner_iso3, metric_id, period, value, fetched_at
               FROM bloc_trade_flows WHERE bloc_id = ? AND metric_id = ?""",
            (bloc_id, metric_id),
        ).fetchall()
        return [BlocTradeFlow(**dict(r)) for r in rows]


def latest_observation(iso3: str, metric_id: str) -> Observation | None:
    with _conn() as conn:
        row = conn.execute(
            """SELECT iso3, metric_id, period, value, fetched_at FROM observations
               WHERE iso3 = ? AND metric_id = ? ORDER BY period DESC LIMIT 1""",
            (iso3, metric_id),
        ).fetchone()
        return Observation(**dict(row)) if row else None


def get_synthesis(page_key: str) -> SynthesisText | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT page_key, text, data_hash, generated_at, provider, model "
            "FROM synthesis_text WHERE page_key = ?",
            (page_key,),
        ).fetchone()
        return SynthesisText(**dict(row)) if row else None


def upsert_synthesis(s: SynthesisText) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO synthesis_text (page_key, text, data_hash, generated_at, provider, model)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(page_key) DO UPDATE SET text=excluded.text, data_hash=excluded.data_hash,
                   generated_at=excluded.generated_at, provider=excluded.provider, model=excluded.model""",
            (s.page_key, s.text, s.data_hash, s.generated_at, s.provider, s.model),
        )


_TENSION_COLUMNS = (
    "scope, window_hours, n_events, mean_goldstein, mean_tone, verbal_cooperation, "
    "material_cooperation, verbal_conflict, material_conflict, conflict_share, "
    "goldstein_delta, examples_json, computed_at"
)


def _row_to_tension_score(row: sqlite3.Row) -> TensionScore:
    data = dict(row)
    examples = json.loads(data.pop("examples_json"))
    return TensionScore(**data, examples=examples)


def get_tension_score(scope: str) -> TensionScore | None:
    with _conn() as conn:
        row = conn.execute(
            f"SELECT {_TENSION_COLUMNS} FROM tension_scores WHERE scope = ?", (scope,)
        ).fetchone()
        return _row_to_tension_score(row) if row else None


def get_all_tension_scores() -> list[TensionScore]:
    with _conn() as conn:
        rows = conn.execute(f"SELECT {_TENSION_COLUMNS} FROM tension_scores").fetchall()
        return [_row_to_tension_score(r) for r in rows]


def upsert_tension_score(s: TensionScore) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO tension_scores
                   (scope, window_hours, n_events, mean_goldstein, mean_tone, verbal_cooperation,
                    material_cooperation, verbal_conflict, material_conflict, conflict_share,
                    goldstein_delta, examples_json, computed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(scope) DO UPDATE SET
                   window_hours=excluded.window_hours, n_events=excluded.n_events,
                   mean_goldstein=excluded.mean_goldstein, mean_tone=excluded.mean_tone,
                   verbal_cooperation=excluded.verbal_cooperation,
                   material_cooperation=excluded.material_cooperation,
                   verbal_conflict=excluded.verbal_conflict,
                   material_conflict=excluded.material_conflict,
                   conflict_share=excluded.conflict_share, goldstein_delta=excluded.goldstein_delta,
                   examples_json=excluded.examples_json, computed_at=excluded.computed_at""",
            (s.scope, s.window_hours, s.n_events, s.mean_goldstein, s.mean_tone,
             s.verbal_cooperation, s.material_cooperation, s.verbal_conflict, s.material_conflict,
             s.conflict_share, s.goldstein_delta, json.dumps(s.examples), s.computed_at),
        )


def latest_data_update() -> str | None:
    """The most recent computed_at across every bloc_aggregate AND every
    tension_score - used as a single, real, site-wide sitemap `lastmod`.
    Since tension.py refreshes every ~2h (see scheduler.py) while
    bloc_aggregates only changes daily/weekly, this value will usually
    reflect the tension refresh - an honest reading of "the site's data was
    genuinely updated at this time," even for pages whose own numbers
    didn't move that particular cycle."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT MAX(m) AS m FROM ("
            "  SELECT MAX(computed_at) AS m FROM bloc_aggregates"
            "  UNION ALL SELECT MAX(computed_at) FROM tension_scores"
            ")"
        ).fetchone()
        return row["m"] if row else None


def get_bloc_aggregates(bloc_id: str) -> list[BlocAggregate]:
    with _conn() as conn:
        rows = conn.execute(
            """SELECT bloc_id, metric_id, period, value, member_count, computed_at
               FROM bloc_aggregates WHERE bloc_id = ? ORDER BY metric_id, period""",
            (bloc_id,),
        ).fetchall()
        return [BlocAggregate(**dict(r)) for r in rows]


def latest_bloc_aggregate(bloc_id: str, metric_id: str) -> BlocAggregate | None:
    with _conn() as conn:
        row = conn.execute(
            """SELECT bloc_id, metric_id, period, value, member_count, computed_at
               FROM bloc_aggregates WHERE bloc_id = ? AND metric_id = ?
               ORDER BY period DESC LIMIT 1""",
            (bloc_id, metric_id),
        ).fetchone()
        return BlocAggregate(**dict(row)) if row else None
