"""sitebuild.build(): builds are serialised, and only a build that succeeded replaces the live site."""
import subprocess
import threading
import time
from types import SimpleNamespace

import pytest

from global_monitor import sitebuild


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setattr(sitebuild, "frontend_dir", lambda: tmp_path)
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "index.html").write_text("old site")
    return tmp_path


def fake_npm(monkeypatch, behaviour):
    calls = []

    def run(cmd, cwd, env, **kw):
        calls.append((cmd, env.get("API_URL")))
        return behaviour(cwd)

    monkeypatch.setattr(sitebuild.subprocess, "run", run)
    return calls


def good(cwd):
    (cwd / "dist.next").mkdir()
    (cwd / "dist.next" / "index.html").write_text("new site")
    return SimpleNamespace(returncode=0, stderr="", stdout="")


def test_a_good_build_replaces_the_site(site, monkeypatch):
    calls = fake_npm(monkeypatch, good)
    assert sitebuild.build("http://api") == (True, "")
    assert (site / "dist" / "index.html").read_text() == "new site"
    assert not (site / "dist.next").exists() and not (site / "dist.old").exists()
    assert calls == [(["npm", "run", "build", "--", "--outDir", "dist.next"], "http://api")]


@pytest.mark.parametrize("behaviour", [
    lambda cwd: SimpleNamespace(returncode=1, stderr="boom", stdout=""),                                          # the build failed
    lambda cwd: ((cwd / "dist.next").mkdir(), SimpleNamespace(returncode=0, stderr="", stdout="no pages"))[1],   # "succeeded" without a home page
    lambda cwd: (_ for _ in ()).throw(subprocess.TimeoutExpired("npm", 1)),                                      # hung
    lambda cwd: (_ for _ in ()).throw(FileNotFoundError("npm")),                                                 # npm missing
])
def test_a_failed_build_keeps_the_old_site(site, monkeypatch, behaviour):
    fake_npm(monkeypatch, behaviour)
    ok, err = sitebuild.build()
    assert not ok and err
    assert (site / "dist" / "index.html").read_text() == "old site"
    assert not (site / "dist.next").exists()


def test_builds_never_overlap(site, monkeypatch):
    running, overlaps = [0], []

    def slow(cwd):
        running[0] += 1
        overlaps.append(running[0])
        time.sleep(0.15)
        out = good(cwd)
        running[0] -= 1
        return out

    fake_npm(monkeypatch, slow)
    threads = [threading.Thread(target=sitebuild.build) for _ in range(4)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert overlaps == [1, 1, 1, 1]
    assert (site / "dist" / "index.html").read_text() == "new site"
