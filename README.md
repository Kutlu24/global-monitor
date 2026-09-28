# Global Monitor

A public, SEO-optimized dashboard comparing major geopolitical/economic blocs — **BRICS+**,
the **EU**, the **US**, and **USMCA** — across economic, trade, social, and military data, kept
in sync with official sources (World Bank, OECD, IMF, UN Comtrade, WTO, UNDP, SIPRI).

No existing site combines all four dimensions at bloc level with regularly-refreshed data in one
place — the closest is [globalmilitary.net](https://globalmilitary.net) (military-only). This
project's real differentiation is putting them together.

A separate **Major Economies** module also compares the world's top 20 advanced economies
individually, country by country, for people who want to look past the bloc level.

## Status: Milestones 1-4 done, Milestone 5 (deployment) started early

**Publicly live** at https://global-monitor-render-relay.onrender.com (see "Deployment" below).

## Milestones 1-2 — done

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

## Milestone 3 — done

Consulted the `dataviz` skill before building any of this (see its own six-check color validator
output baked into the reasoning below) rather than guessing at a chart type or palette.

- **No radar/spider chart** - deliberately dropped from the original plan. Combining GDP (USD),
  military-%-GDP, HDI (0-1), and life expectancy (years) onto one normalized radar axis has the
  same "arbitrary scale alignment invents a correlation" flaw the dataviz skill explicitly bans
  for dual-axis charts, just generalized to N axes. Replaced with **small multiples of plain-SVG
  2-bar grouped columns** (`MetricCompareBars.tsx`, no charting library) - one tile per metric,
  each keeping its own real scale.
- **Bloc colors are fixed and validated**: `{brics/brics5: blue, eu: yellow, us: green, usmca:
  magenta}` - the one 4-color subset of the skill's reference palette that passes every CVD/
  contrast check **all-pairs, in both light and dark mode** (any two of the four can appear side
  by side - a comparison page, a 2-highlight map - safely). Every other 4-subset tried failed at
  least one check in at least one mode; this specific 8-hue reference palette only clears 3 slots
  for all-pairs comparisons in general. `brics5` deliberately reuses `brics`'s own color - same
  lineage at a different membership snapshot, never shown as a competing identity on the same page.
- **World map** (`WorldMap.tsx`, `react-simple-maps`, real SVG/topojson, no WebGL/canvas): uses the
  skill's "emphasis" form (1-2 highlight colors + neutral gray context), not a full categorical
  choropleth - sidesteps the all-pairs cap entirely on bloc/compare pages, and uses all 4 validated
  colors at once (safe, since that exact 4-set passed all-pairs) on the cross-bloc dimension pages.
- New pages: `/compare/{pair}/` (6 pairs), `/compare/{pair}/{dimension}/` (24 pages, real per-metric
  tables + bar-chart small multiples), `/dimension/{dimension}/` (4 cross-bloc pages with the full
  4-color map). 61 total static pages, all verified rendering real data inside the actual Docker
  image.

## Milestone 4 — done

schema.org/Dataset JSON-LD (with canonical `<link>`) on every bloc/compare/country page,
GLM-primary/Ollama-fallback synthesis text (`synthesis.py`) hash-diff cached per page so the LLM
is only called when a page's underlying numbers actually change, plus a chunked sitemap
(`sitemap-index.xml` → blocs/compare/dimensions) and `robots.txt` with real `lastmod` from
`/api/last-updated`. `SITE_URL`/`GLOBAL_MONITOR_DOMAIN` points at the live relay address
(`https://global-monitor-render-relay.onrender.com`) so these URLs are correct now, not just once
a domain is purchased.

Three real bugs surfaced only by a genuine fresh-container-boot test (not by build exit codes):
`list_blocs()` was missing the `synthesis` field the plural endpoint's callers actually use; no
`.dockerignore` existed, so a stale local `frontend/dist` could get baked into the image; and the
`StaticFiles` mount was gated on `dist/` existing at import time, which 404ed the whole site
forever on a truly fresh boot until fixed with `check_dir=False` (self-heals once the first build
finishes, no restart needed).

## Not yet built (see the project plan for the full build order)

Nothing outstanding in the original plan. **Milestone 5's one remaining item - purchasing a
domain - was consciously declined**: the Render relay's own `.onrender.com` address stays the
public identity, so `SITE_URL`/`GLOBAL_MONITOR_DOMAIN` stay pointed at it. Changing that later is
a one-line edit in `home-server-infra/Caddyfile` plus those two env vars, not a migration.

## Why BRICS is two bloc rows

`brics` (current membership, including the 2024-25 expansion) and `brics5` (the original five,
frozen) share the exact same generic bloc/bloc_membership mechanism — see
`backend/src/global_monitor/blocs.py`'s own module docstring. `brics` takes part in the derived
pair set, and `brics5` is the site's **primary comparison** — EU vs the original five. That
pairing is chosen deliberately: the 2024-25 expansion pulled in members whose overlap with the EU
muddies an economic comparison, so the founding five are what make "EU vs BRICS" unambiguous.
`brics5` still reuses `brics`'s own colour, and because the two never compete on the same page
that alias stays safe.

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

Runs as a service in `~/my-projects/home-server-infra`'s Docker Compose stack (port 7863) and is
**already publicly live** via that repo's `docs/RENDER_PROXY.md` relay mechanism - the first app
in that whole portfolio actually flipped over to it for real, since every other app there is
Tailscale-only by design. No custom domain, by decision rather than by omission - the relay's
own Render address (`global-monitor-render-relay.onrender.com`) is the public identity.
