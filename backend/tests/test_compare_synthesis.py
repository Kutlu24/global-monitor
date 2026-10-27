"""scripts/compare_synthesis.py: the failure handling around GLM calls. The
network call is replaced; no key and no LLM are needed."""
import importlib.util
import pathlib

import pytest

_path = pathlib.Path(__file__).parents[1] / "scripts" / "compare_synthesis.py"
_spec = importlib.util.spec_from_file_location("compare_synthesis", _path)
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(cs.time, "sleep", lambda s: None)


def test_transient_failure_is_retried_then_succeeds(monkeypatch):
    calls = []

    def flaky(prompt):
        calls.append(prompt)
        if len(calls) < 3:
            raise RuntimeError("429 rate limited")
        return "ok text"

    monkeypatch.setattr(cs, "_call_glm", flaky)
    assert cs._glm("p") == "ok text"
    assert len(calls) == 3


def test_persistent_failure_returns_none_instead_of_raising(monkeypatch):
    def down(prompt):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(cs, "_call_glm", down)
    assert cs._glm("p") is None


def test_empty_reply_counts_as_failure(monkeypatch):
    monkeypatch.setattr(cs, "_call_glm", lambda p: "")
    assert cs._glm("p") is None


def test_auth_error_stops_immediately(monkeypatch):
    calls = []

    def bad_key(prompt):
        calls.append(1)
        raise RuntimeError("401 invalid api key")

    monkeypatch.setattr(cs, "_call_glm", bad_key)
    with pytest.raises(SystemExit):
        cs._glm("p")
    assert len(calls) == 1
