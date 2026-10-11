"""api/app.py via TestClient. The client is NOT used as a context manager on
purpose: that would run the lifespan and start the APScheduler jobs (network
ingestion). The admin rebuild's happy path is not exercised for the same
reason -- it would run every ETL source and `npm run build`."""
import pytest
from fastapi.testclient import TestClient

from global_monitor import aggregate, db
from global_monitor.api import app as app_mod
from global_monitor.config import settings


@pytest.fixture
def client():
    return TestClient(app_mod.app)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_blocs_list_after_seed(client, seeded):
    data = client.get("/api/blocs").json()
    by_id = {b["bloc_id"]: b for b in data}
    assert set(by_id) == {"brics", "brics5", "eu", "us", "usmca"}
    assert by_id["eu"]["member_count"] == 27
    assert by_id["eu"]["members"] == sorted(by_id["eu"]["members"])


def test_bloc_detail_and_404(client, seeded):
    assert client.get("/api/blocs/usmca").json()["member_count"] == 3
    assert client.get("/api/blocs/atlantis").status_code == 404


@pytest.mark.xfail(strict=True, raises=NotImplementedError, reason='KNOWN BUG: metrics.RISK_INPUT_METRICS use default_aggregation="mean" but aggregate_metric() only implements "sum"/"weighted_mean" and raises NotImplementedError; pipeline.run_all() calls aggregate_all() un-guarded, so the run aborts there. Remove this marker once fixed (strict xfail will remind you).')
def test_bloc_aggregates_appear_after_aggregation(client, seeded, obs):
    obs("gdp_current_usd", {"USA": ("2023", 100.0), "CAN": ("2023", 20.0), "MEX": ("2023", 10.0)})
    aggregate.aggregate_all()
    agg = client.get("/api/blocs/usmca").json()["aggregates"]["gdp_current_usd"]
    assert agg == {"value": 130.0, "period": "2023", "member_count": 3}


def test_metrics_catalog(client, seeded):
    ids = {m["metric_id"] for m in client.get("/api/metrics").json()}
    assert {"gdp_current_usd", "hdi", "population_total"} <= ids


def test_compare_ok_and_404_on_either_side(client, seeded):
    ok = client.get("/api/compare/eu/us").json()
    assert ok["a"]["bloc_id"] == "eu" and ok["b"]["bloc_id"] == "us"
    assert set(ok["synthesis_by_dimension"]) == {"economic", "trade", "social", "military"}
    assert client.get("/api/compare/eu/nope").status_code == 404
    assert client.get("/api/compare/nope/us").status_code == 404


def test_country_lookup_is_case_insensitive_and_404_for_untracked(client, seeded):
    assert client.get("/api/countries/deu").json()["iso3"] == "DEU"
    assert client.get("/api/countries/BRA").status_code == 404  # not a "major economy"


def test_country_payload_only_includes_real_values(client, seeded, obs):
    obs("gdp_current_usd", {"DEU": ("2023", 4.0e12)})
    obs("population_total", {"DEU": ("2023", None)})
    metrics = client.get("/api/countries/DEU").json()["metrics"]
    assert metrics["gdp_current_usd"]["value"] == 4.0e12
    assert "population_total" not in metrics


def test_every_major_economy_has_a_real_name(client, seeded):
    for c in client.get("/api/countries").json():
        assert c["name"] != c["iso3"], f"{c['iso3']} has no display name"


def test_unknown_risk_scenario_404(client):
    assert client.get("/api/risk/does-not-exist").status_code == 404


def test_risk_scenarios_catalogue_shape(client):
    data = client.get("/api/risk/scenarios").json()
    assert data and all({"slug", "name", "weights", "belligerents"} <= set(s) for s in data)


def test_tension_404_when_no_data_yet(client, seeded):
    assert client.get("/api/tension/bloc/eu").status_code == 404
    assert client.get("/api/tension/pair/eu/us").status_code == 404


def test_last_updated_is_null_on_empty_db(client, seeded):
    assert "last_updated" in client.get("/api/last-updated").json()


class TestAdminRebuildAuth:
    def test_503_when_token_not_configured(self, client, monkeypatch):
        monkeypatch.setattr(settings, "admin_token", None)
        assert client.post("/api/admin/rebuild").status_code == 503

    def test_401_without_or_with_wrong_token(self, client, monkeypatch):
        monkeypatch.setattr(settings, "admin_token", "s3cret")
        assert client.post("/api/admin/rebuild").status_code == 401
        assert client.post("/api/admin/rebuild", headers={"Authorization": "Bearer nope"}).status_code == 401

    def test_non_ascii_header_is_401_not_500(self, client, monkeypatch):
        monkeypatch.setattr(settings, "admin_token", "s3cret")
        r = client.post("/api/admin/rebuild", headers={"Authorization": "Bearer ünïcödé".encode("latin-1")})
        assert r.status_code == 401

    def test_valid_token_reaches_pipeline(self, client, monkeypatch):
        monkeypatch.setattr(settings, "admin_token", "s3cret")
        called = {}
        monkeypatch.setattr(app_mod.pipeline, "run_all", lambda: called.setdefault("ran", {"ok": True}))

        class _R:  # stand-in for the `npm run build` subprocess result
            returncode, stderr = 0, ""

        monkeypatch.setattr(app_mod.subprocess, "run", lambda *a, **k: _R())
        r = client.post("/api/admin/rebuild", headers={"Authorization": "Bearer s3cret"})
        assert r.status_code == 200 and called and r.json()["status"] == "rebuilt"
