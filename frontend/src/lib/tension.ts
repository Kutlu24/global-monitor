// Build-time data access for the Tension module (ported from the
// standalone `GFCA` tool - see backend/src/global_monitor/tension.py's own
// docstring). Same build-time-fetch pattern as lib/data.ts, talking to the
// FastAPI backend in the same container/process group.
const API_URL = process.env.API_URL || "http://127.0.0.1:7860";

export interface TensionExample {
  kind: "conflictual" | "cooperative";
  date: string;
  actor1: string | null;
  actor2: string | null;
  location: string | null;
  goldstein: number | null;
  source_url: string | null;
}

export interface TensionSynthesis {
  text: string;
  provider: string;
  generated_at: string;
}

export interface TensionScore {
  scope: string;
  window_hours: number;
  n_events: number;
  mean_goldstein: number | null;
  mean_tone: number | null;
  verbal_cooperation: number;
  material_cooperation: number;
  verbal_conflict: number;
  material_conflict: number;
  conflict_share: number | null;
  goldstein_delta: number | null;
  examples: TensionExample[];
  computed_at: string;
  synthesis: TensionSynthesis | null;
}

async function getJSON<T>(path: string): Promise<T | null> {
  const res = await fetch(`${API_URL}${path}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Global Monitor API ${path} returned ${res.status}`);
  return res.json() as Promise<T>;
}

export function getAllTensionScores(): Promise<TensionScore[]> {
  return getJSON<TensionScore[]>("/api/tension").then((r) => r ?? []);
}

export function getTensionBloc(blocId: string): Promise<TensionScore | null> {
  return getJSON<TensionScore>(`/api/tension/bloc/${blocId}`);
}

export function getTensionPair(blocA: string, blocB: string): Promise<TensionScore | null> {
  return getJSON<TensionScore>(`/api/tension/pair/${blocA}/${blocB}`);
}

export interface CountryRef {
  iso3: string;
  name: string;
}

export function getTensionCountries(): Promise<CountryRef[]> {
  return getJSON<CountryRef[]>("/api/tension/countries").then((r) => r ?? []);
}
