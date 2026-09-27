# Global Monitor

A public, SEO-optimized dashboard comparing major geopolitical/economic blocs — **BRICS+**,
the **EU**, the **US**, and **USMCA** — across economic, trade, social, and military data, kept
in sync with official sources (World Bank, OECD, IMF, UN Comtrade, WTO, UNDP, SIPRI).

No existing site combines all four dimensions at bloc level with regularly-refreshed data in one
place — the closest is [globalmilitary.net](https://globalmilitary.net) (military-only). This
project's real differentiation is putting them together.

A separate **Major Economies** module also compares the world's top 20 advanced economies
individually, country by country, for people who want to look past the bloc level.

## Status: Milestones 1-2 — done

World Bank → SQLite → FastAPI JSON → Astro static build → real HTML, proven end to end, inside
the real Docker image (not just locally). All bloc pages and country pages render real numbers as
static text.

**Data sources implemented and verified live (2026-09-27):**
- **World Bank** (no key): GDP, population, military expenditure % GDP, trade % GDP, life
  expectancy, secondary enrollment — all 48 tracked countries, every run.
- **UN Comtrade**, via the official `comtradeapicall` package: world-total exports/imports, and
  intra-bloc bilateral trade flows. Runs key-less by default, which has a real, tight quota (~50
  calls before a ~45-90 min cooldown, confirmed live) - a circuit breaker stops the whole comtrade
  run after 4 consecutive failures instead of burning through the rest of the list. Set
  `COMTRADE_API_KEY` to raise the limit.
- **UNDP HDI**: downloads UNDP's own published composite-indices CSV directly (no self-serve API
  key exists yet) - all 48 countries.
- **SIPRI military expenditure**: downloads and parses SIPRI's own yearly Excel file (no API at
  all) - all 48 countries. Deliberately fragile-tolerant: a parse failure logs loudly and keeps
  the last-known-good data rather than crashing.
- **Not implemented**: OECD SDMX and IMF DataMapper - their real dataflow/API shapes need proper
  documentation research rather than guessed endpoints, and World Bank already covers the core
  indicators well enough for v1. Revisit if a specific gap they'd fill actually shows up.

**Major Economies module** (`/countries`, `/country/{iso3}`) - a country-vs-country comparison,
separate from bloc comparison: the top 20 advanced economies (IMF classification, by nominal
GDP, sovereign states only). See `backend/src/global_monitor/major_economies.py`.

**In-process scheduler** (`scheduler.py`, APScheduler via FastAPI's lifespan) - daily for World
Bank/Comtrade, weekly for UNDP HDI/SIPRI, rebuilding the Astro site after any run that actually
changes data. A `POST /api/admin/rebuild` (bearer-token gated) triggers the same thing manually.

Not yet built (see the project plan for the full build order):
- **Milestone 3**: `/compare/{pair}/{dimension}` pages, the world map (`react-simple-maps`) and
  radar chart (`Apache ECharts`) components.
- **Milestone 4**: schema.org/Dataset markup, GLM/Ollama-generated comparison text, canonical
  tags, chunked sitemap.
- **Milestone 5**: wiring into `home-server-infra`'s `docker-compose.yml`/`Caddyfile`, a new
  Render relay (reusing `home-server-infra/render-proxy/`), and the real domain once purchased.

## Why BRICS is two bloc rows

`brics` (current membership, including the 2024-25 expansion) and `brics5` (the original five,
frozen) share the exact same generic bloc/bloc_membership mechanism — see
`backend/src/global_monitor/blocs.py`'s own module docstring. Only `brics` appears in the main
comparison structure; `brics5` is a secondary historical view.

## Local development

```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -e .
DATA_DIR=./data .venv/bin/python -m global_monitor.cli ingest all   # seeds + pulls real World Bank data
DATA_DIR=./data .venv/bin/python -m uvicorn global_monitor.api.app:app --port 7860 &

# Frontend (in another terminal)
cd frontend
npm install
API_URL=http://127.0.0.1:7860 npm run build
npx astro preview   # serves frontend/dist/
```

## Deployment

Runs as one more service in `~/my-projects/home-server-infra`'s Docker Compose stack (see that
repo's own `docs/DEPLOYMENT.md`), reachable publicly via its `docs/RENDER_PROXY.md` relay
mechanism once a domain is purchased (Milestone 5) — unlike this portfolio's other apps, Global
Monitor is meant to be genuinely public and crawlable, not Tailscale-only.
