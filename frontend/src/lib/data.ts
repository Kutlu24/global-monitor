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

export interface Bloc {
  bloc_id: string;
  name: string;
  slug: string;
  description: string;
  aggregates: Record<string, BlocAggregateValue>;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) {
    throw new Error(`Global Monitor API ${path} returned ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function getBlocs(): Promise<Bloc[]> {
  return getJSON<Bloc[]>("/api/blocs");
}

export function getBloc(blocId: string): Promise<Bloc> {
  return getJSON<Bloc>(`/api/blocs/${blocId}`);
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
