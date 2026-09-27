#!/bin/sh
# Same volume-permission fix as dhra/ottoman-rag/job-suche/mutercim/gfca's
# entrypoint.sh - a Docker named volume's mount point is created root:root
# regardless of the image's own directory ownership.
#
# Unlike those simpler `exec`-only entrypoints, this one backgrounds
# uvicorn so it can run the initial ingest+Astro-build *after* the API is
# already up (the build needs to call the API - see
# frontend/src/lib/data.ts). A plain `wait` on a backgrounded child does
# NOT forward Docker's SIGTERM on `docker compose stop`/`restart:
# unless-stopped` cycles - the trap below is what makes shutdown clean.
set -e

mkdir -p "$HOME/app/data"
chown -R user:user "$HOME/app/data"
# frontend/ is NOT chowned here - it was already copied in with --chown=user
# at build time (no volume is ever mounted over it), and a recursive chown
# over frontend/node_modules (thousands of files) would needlessly stall
# every container start for no benefit.

su -s /bin/sh user -c "python -m uvicorn global_monitor.api.app:app --host 0.0.0.0 --port ${PORT:-7860}" &
UVICORN_PID=$!
trap 'kill -TERM "$UVICORN_PID" 2>/dev/null; wait "$UVICORN_PID"' TERM INT

for i in $(seq 1 60); do
  curl -sf "http://127.0.0.1:${PORT:-7860}/api/health" >/dev/null 2>&1 && break
  sleep 1
done

# Always rebuild after this, unconditionally - NOT "only if dist/ doesn't
# exist yet". That guard was fine before tension.py existed: every
# scheduled job used a cron trigger that couldn't possibly fire before
# this line ran. tension-refresh (scheduler.py) deliberately fires
# IMMEDIATELY on every boot too (in-process, to populate its own in-memory
# GDELT cache - see that file's own comment) - it can finish and trigger
# its own rebuild well before this slower "ingest all" (worldbank +
# comtrade + undp + sipri, with real rate-limit delays) completes,
# creating dist/index.html early with only partial/stale data. The old
# guard would then skip rebuilding here even though "ingest all" just
# finished with the actually-complete, fresh dataset - confirmed live
# (2026-09-27) as a real race, not a hypothetical one.
su -s /bin/sh user -c "python -m global_monitor.cli ingest all" || true
su -s /bin/sh user -c "cd $HOME/app/frontend && API_URL=http://127.0.0.1:${PORT:-7860} npm run build"

wait "$UVICORN_PID"
