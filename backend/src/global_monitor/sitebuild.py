"""One place that rebuilds the static site, used by the scheduler, the admin endpoint and the container entrypoint.

Two problems this solves (both seen in practice):
  * builds could overlap (boot-time build + the tension refresh that fires at boot + a manual rebuild), each emptying
    and writing the same dist/ folder, which ends in a failed build and a half-written site;
  * Astro empties dist/ when a build starts, so for the length of every build visitors got missing pages, and a failed
    build left the site broken until the next good one.

So builds are serialised with a file lock (it also holds across processes), each build writes to dist.next/, and only a
build that succeeded replaces dist/. A failed build leaves the site that was there.
"""
from __future__ import annotations

import fcntl
import logging
import os
import shutil
import subprocess

from .config import frontend_dir

logger = logging.getLogger(__name__)
STAGING, LIVE, OLD = "dist.next", "dist", "dist.old"


def build(api_url: str | None = None, timeout: int = 1800) -> tuple[bool, str]:
    """(succeeded, last part of the build's error output). Blocks while another build is running."""
    root = frontend_dir()
    env = {**os.environ, **({"API_URL": api_url} if api_url else {})}
    with open(root / ".build.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        staging, live, old = root / STAGING, root / LIVE, root / OLD
        shutil.rmtree(staging, ignore_errors=True)
        try:
            r = subprocess.run(["npm", "run", "build", "--", "--outDir", STAGING], cwd=root, env=env, capture_output=True, text=True, timeout=timeout)
            ok, err = r.returncode == 0 and (staging / "index.html").is_file(), (r.stderr or r.stdout)[-2000:]
        except (OSError, subprocess.TimeoutExpired) as e:
            ok, err = False, str(e)
        if not ok:
            shutil.rmtree(staging, ignore_errors=True)
            logger.error("site build failed; the previous site stays in place:\n%s", err)
            return False, err
        shutil.rmtree(old, ignore_errors=True)
        if live.exists():
            live.rename(old)
        staging.rename(live)
        shutil.rmtree(old, ignore_errors=True)
        logger.info("site build completed")
        return True, ""
