# Global Monitor

A public, SEO-optimized dashboard comparing major geopolitical/economic blocs — **BRICS+**,
the **EU**, the **US**, and **USMCA** — across economic, trade, social, and military data, kept
in sync with official sources (World Bank, OECD, IMF, UN Comtrade, WTO, UNDP, SIPRI).

No existing site combines all four dimensions at bloc level with regularly-refreshed data in one
place — the closest is [globalmilitary.net](https://globalmilitary.net) (military-only). This
project's real differentiation is putting them together.

## Status: Milestone 1 (walking skeleton) — done

World Bank → SQLite → FastAPI JSON → Astro static build → real HTML, proven end to end:
GDP + population for all 5 tracked blocs (BRICS+, BRICS original-5, EU, US, USMCA), rendered as
real static text on the homepage and each bloc's own page.

Not yet built (see the project plan for the full build order):
- **Milestone 2**: remaining data sources (OECD, IMF, UN Comtrade — both world-totals and
  intra-bloc bilateral flows, WTO, UNDP HDI, SIPRI), weighted-mean aggregation, the in-process
  scheduler.
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
