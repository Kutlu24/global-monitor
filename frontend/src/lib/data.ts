import type { RiskScenario, RiskScenarioMeta } from "./risk";

// Build-time data access - Astro calls these from page frontmatter, which
// runs in Node during `astro build`, not in the browser. This talks to the
// FastAPI backend running in the SAME container/process group (see
// docker-entrypoint.sh - `npm run build` only runs after uvicorn is
// already accepting connections), never to a public URL.
const API_URL = process.env.API_URL || "http://127.0.0.1:7860";

export interface BlocAggregateValue {
  value: number | null;
  period: string;
  member_count: number;
}

export interface Synthesis {
  text: string;
  provider: string;
  generated_at: string;
}

export interface Bloc {
  bloc_id: string;
  name: string;
  slug: string;
  description: string;
  members?: string[];
  aggregates: Record<string, BlocAggregateValue>;
  synthesis?: Synthesis | null;
}

export interface ComparePair {
  a: Bloc;
  b: Bloc;
  synthesis?: Synthesis | null;
  synthesis_by_dimension?: Record<string, Synthesis | null>;
}

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) {
    throw new Error(`Global Monitor API ${path} returned ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// One in-flight promise per path, shared for the whole `astro build`.
//
// `getStaticPaths` and page frontmatter are separate module invocations
// across ~76 pages, so a bloc list or a scenario list is re-requested
// dozens of times per build. The API is in-process and cheap, but the
// risk payload is not small (211 countries x 6 criteria), and BaseLayout -
// used by every single page - needs the scenario count for its nav badge.
// Caching the promise rather than the resolved value also collapses
// concurrent requests instead of only repeat ones.
//
// Safe because every path here is a pure read: no build step mutates the
// database, so a value cannot go stale within one build. A failed request
// caches its rejection too, which is the behaviour we want - if the ETL
// never ran, failing all 76 pages loudly beats quietly rendering zeros.
const inflight = new Map<string, Promise<unknown>>();

function getJSON<T>(path: string): Promise<T> {
  const cached = inflight.get(path);
  if (cached) return cached as Promise<T>;
  const p = fetchJSON<T>(path).catch((err) => {
    inflight.delete(path); // don't cache a failure forever within a build
    throw err;
  });
  inflight.set(path, p);
  return p;
}

export function getBlocs(): Promise<Bloc[]> {
  return getJSON<Bloc[]>("/api/blocs");
}

export function getBloc(blocId: string): Promise<Bloc> {
  return getJSON<Bloc>(`/api/blocs/${blocId}`);
}

export function getComparePair(blocA: string, blocB: string): Promise<ComparePair> {
  return getJSON<ComparePair>(`/api/compare/${blocA}/${blocB}`);
}

export interface CountryMetricValue {
  value: number;
  period: string;
}

export interface Country {
  iso3: string;
  name: string;
  metrics: Record<string, CountryMetricValue>;
}

// The "major economies" country-comparison module - a SEPARATE concept
// from bloc comparison (see backend/src/global_monitor/major_economies.py).
export function getCountries(): Promise<Country[]> {
  return getJSON<Country[]>("/api/countries");
}

export function getCountry(iso3: string): Promise<Country> {
  return getJSON<Country>(`/api/countries/${iso3}`);
}

// -- Risk simulator --------------------------------------------------------
// The risk module used to be the site's only page with no backend at all
// (see lib/risk.ts's replacement of the hardcoded 19-country model). These
// two calls are its entire data dependency.

export function getRiskScenarios(): Promise<RiskScenarioMeta[]> {
  return getJSON<RiskScenarioMeta[]>("/api/risk/scenarios");
}

export function getRiskScenario(slug: string): Promise<RiskScenario> {
  return getJSON<RiskScenario>(`/api/risk/${slug}`);
}
