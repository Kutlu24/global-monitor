import { useState } from "react";
import { TENSION_DIVERGING } from "../lib/colors";
import type { CountryRef, TensionScore } from "../lib/tension";
import WorldMap from "./WorldMap";

// Country A/B identity colors for the map below - deliberately NOT blue/red
// (TENSION_DIVERGING's own cooperation/conflict poles, used on the gauge
// right above it on this same page) - reusing those here would wrongly
// suggest "this country IS the cooperative/conflictual one" rather than
// just "this is country A". Reuses eu/usmca's own validated (all-pairs
// CVD-safe together) categorical colors purely as neutral identity markers.
const ENTITY_A_COLOR = "#c98500"; // amber
const ENTITY_B_COLOR = "#d55181"; // magenta

// The ONE place in this project that fetches from the browser at runtime
// instead of at Astro build time - the ad-hoc two-country query (the
// counterpart to GFCA's own CLI, `analyze IR US`) needs a country pair the
// static build can't know about in advance. Same-origin fetch: this static
// site and the API are served by the same FastAPI process (see
// api/app.py's StaticFiles mount), so no CORS setup is needed.

const DOMAIN = 10;

function Gauge({ value }: { value: number | null }) {
  const clamped = value == null ? 0 : Math.max(-DOMAIN, Math.min(DOMAIN, value));
  const halfPct = (Math.abs(clamped) / DOMAIN) * 50;
  const isPositive = clamped >= 0;
  const color = isPositive ? TENSION_DIVERGING.cooperation.dark : TENSION_DIVERGING.conflict.dark;
  return (
    <div className="gm-tension-gauge">
      <div className="gm-tension-track">
        <div className="gm-tension-zero" />
        {value != null && (
          <div
            className="gm-tension-fill"
            style={{ left: isPositive ? "50%" : `${50 - halfPct}%`, width: `${halfPct}%`, background: color }}
          />
        )}
      </div>
      <div className="gm-tension-scale">
        <span>Conflict (&minus;10)</span>
        <span className="gm-tension-value">{value != null ? value.toFixed(2) : "N/A"}</span>
        <span>Cooperation (+10)</span>
      </div>
    </div>
  );
}

interface Props {
  countries: CountryRef[];
}

export default function CountryTensionQuery({ countries }: Props) {
  const [a, setA] = useState(countries[0]?.iso3 ?? "");
  const [b, setB] = useState(countries[1]?.iso3 ?? "");
  const [result, setResult] = useState<TensionScore | null>(null);
  // The pair actually queried, frozen at fetch time - `a`/`b` above track
  // the LIVE dropdown selection, which the user can change again before
  // clicking Analyze; using them directly for the map/labels below would
  // then show a country pair that doesn't match the still-displayed
  // (stale) result.
  const [queriedPair, setQueriedPair] = useState<[string, string] | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function run() {
    if (!a || !b || a === b) {
      setStatus("error");
      setErrorMessage("Pick two different countries.");
      return;
    }
    setStatus("loading");
    setResult(null);
    try {
      const res = await fetch(`/api/tension/query/${a}/${b}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${res.status})`);
      }
      setResult(await res.json());
      setQueriedPair([a, b]);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setErrorMessage(err instanceof Error ? err.message : "Something went wrong.");
    }
  }

  const conflictual = result?.examples.filter((e) => e.kind === "conflictual") ?? [];
  const cooperative = result?.examples.filter((e) => e.kind === "cooperative") ?? [];
  const nameFor = (iso3: string) => countries.find((c) => c.iso3 === iso3)?.name ?? iso3;

  return (
    <div className="gm-country-query">
      <style>{`
        .gm-country-query-form { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: end; }
        .gm-country-query-field { display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.85rem; color: var(--ink-secondary); }
        .gm-country-query select {
          background: var(--surface); color: var(--ink); border: 1px solid var(--hairline);
          border-radius: var(--radius-sm); padding: 0.5rem 0.6rem; font-size: 0.92rem; min-width: 200px;
        }
        .gm-country-query button {
          background: var(--accent); color: #fff; border: none; border-radius: var(--radius-sm);
          padding: 0.55rem 1.1rem; font-size: 0.92rem; font-weight: 600; cursor: pointer;
        }
        .gm-country-query button:disabled { opacity: 0.6; cursor: default; }
        .gm-country-query-error { color: ${TENSION_DIVERGING.conflict.dark}; font-size: 0.85rem; margin-top: 0.5rem; }
        .gm-country-query-result { margin-top: var(--space-6); }
        .gm-tension-gauge { margin: var(--space-3) 0; }
        .gm-tension-track { position: relative; height: 10px; background: var(--hairline); border-radius: 999px; overflow: hidden; }
        .gm-tension-zero { position: absolute; left: 50%; top: 0; bottom: 0; width: 2px; background: var(--ink-muted); transform: translateX(-1px); z-index: 1; }
        .gm-tension-fill { position: absolute; top: 0; bottom: 0; border-radius: 999px; }
        .gm-tension-scale { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--ink-muted); margin-top: var(--space-2); }
        .gm-tension-value { font-family: var(--font-mono); font-weight: 700; color: var(--ink); }
      `}</style>
      <div className="gm-country-query-form">
        <label className="gm-country-query-field">
          Country A
          <select value={a} onChange={(e) => setA(e.target.value)}>
            {countries.map((c) => <option key={c.iso3} value={c.iso3}>{c.name} ({c.iso3})</option>)}
          </select>
        </label>
        <label className="gm-country-query-field">
          Country B
          <select value={b} onChange={(e) => setB(e.target.value)}>
            {countries.map((c) => <option key={c.iso3} value={c.iso3}>{c.name} ({c.iso3})</option>)}
          </select>
        </label>
        <button onClick={run} disabled={status === "loading"}>
          {status === "loading" ? "Analyzing…" : "Analyze"}
        </button>
      </div>
      {status === "error" && <p className="gm-country-query-error">{errorMessage}</p>}

      {result && queriedPair && (
        <div className="gm-country-query-result">
          <div className="gm-viz-block">
            <WorldMap
              highlights={[
                { iso3: [queriedPair[0]], color: ENTITY_A_COLOR, label: nameFor(queriedPair[0]) },
                { iso3: [queriedPair[1]], color: ENTITY_B_COLOR, label: nameFor(queriedPair[1]) },
              ]}
            />
          </div>
          <Gauge value={result.mean_goldstein} />
          <p className="gm-stat-label">
            {result.n_events} bilateral events in the last {result.window_hours}h
            {result.conflict_share != null && ` · conflict share: ${(result.conflict_share * 100).toFixed(0)}%`}
          </p>

          {conflictual.length > 0 && (
            <>
              <h3>Most conflictual real events</h3>
              <ul>
                {conflictual.map((e, i) => (
                  <li key={i}>
                    [{e.date}] {e.actor1 ?? "?"} &rarr; {e.actor2 ?? "?"}
                    {e.location && ` at ${e.location}`}
                    {e.goldstein != null && ` (Goldstein ${e.goldstein.toFixed(1)})`}
                    {e.source_url && <> — <a href={e.source_url} target="_blank" rel="noopener noreferrer">source</a></>}
                  </li>
                ))}
              </ul>
            </>
          )}
          {cooperative.length > 0 && (
            <>
              <h3>Most cooperative real events</h3>
              <ul>
                {cooperative.map((e, i) => (
                  <li key={i}>
                    [{e.date}] {e.actor1 ?? "?"} &rarr; {e.actor2 ?? "?"}
                    {e.location && ` at ${e.location}`}
                    {e.goldstein != null && ` (Goldstein ${e.goldstein.toFixed(1)})`}
                    {e.source_url && <> — <a href={e.source_url} target="_blank" rel="noopener noreferrer">source</a></>}
                  </li>
                ))}
              </ul>
            </>
          )}
          {result.n_events === 0 && <p>No bilateral events found between these two countries in the last {result.window_hours}h.</p>}
          <p style={{ fontSize: "0.85rem", color: "var(--ink-muted)" }}>
            Computed on demand from real GDELT events - not a prediction or forecast, and not the
            sole basis for any decision.
          </p>
        </div>
      )}
    </div>
  );
}
