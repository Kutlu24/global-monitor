# Two stages, but NOT the same shape as ottoman-rag/mutercim's Dockerfiles:
# those discard Node after building a one-shot Vite SPA. Astro's SSG output
# must be REGENERATED every time the underlying data changes (that's the
# whole SEO point - real per-route static HTML, not client-rendered
# content) - so Node + the Astro project stay installed in the runtime
# image, and scheduler.py calls `npm run build` in place after each ETL
# run that actually changes values. See backend/src/global_monitor/api/app.py's
# admin_rebuild() for the manual-trigger equivalent.

FROM node:20-slim AS frontend-deps
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

FROM python:3.11-slim

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1

# Node stays in the final image (see comment above) - installed via
# NodeSource's setup script since Debian's own `nodejs` package on
# python:3.11-slim's Debian release is too old for Astro 5.
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

RUN pip install --no-cache-dir --upgrade pip

COPY --chown=user backend ./backend
RUN pip install --no-cache-dir --user -e ./backend

COPY --chown=user frontend ./frontend
COPY --chown=user --from=frontend-deps /app/frontend/node_modules ./frontend/node_modules
# No `astro build` here - real data doesn't exist at image-build time
# (the ETL hasn't run yet). docker-entrypoint.sh runs the first real
# ingest+build after uvicorn is already accepting connections.

EXPOSE 7860

# Root only to let the entrypoint chown the mounted data volume (see
# docker-entrypoint.sh) before it execs the real server as "user" - never
# runs application code as root.
USER root
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
