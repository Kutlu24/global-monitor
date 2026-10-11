"""Every test runs against its own throwaway sqlite file. config.db_path()
reads settings.data_dir on each call, so patching it is enough -- the real
data/global_monitor.sqlite3 is never touched, and nothing here hits a
network (no ingestion module is imported by these tests)."""
from __future__ import annotations

import pytest

from global_monitor import blocs, db, metrics
from global_monitor.config import settings
from global_monitor.models import Observation


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    yield tmp_path


@pytest.fixture
def seeded():
    """Blocs, countries, memberships and the metric catalog -- exactly what
    docker-entrypoint.sh's boot-time seeding produces."""
    blocs.seed()
    metrics.seed()


@pytest.fixture
def obs():
    """Insert observations: obs("gdp_current_usd", {"DEU": ("2023", 4.0e12)})"""

    def _insert(metric_id: str, rows: dict[str, tuple[str, float | None]]):
        db.upsert_observations(
            [Observation(iso3, metric_id, period, value, db.now()) for iso3, (period, value) in rows.items()]
        )

    return _insert
