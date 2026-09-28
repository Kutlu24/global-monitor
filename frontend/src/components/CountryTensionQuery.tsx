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
// The same two validated hexes, reached through the theme-aware custom
// properties in global.css rather than frozen literals, so the map follows
// the active theme instead of the mode this file happened to be written in.
const ENTITY_A_COLOR = "var(--bloc-eu)"; // amber
const ENTITY_B_COLOR = "var(--bloc-usmca)"; // magenta

// The ONE place in this project that fetches from the browser at runtime
// instead of at Astro build time - the ad-hoc two-country query (the
// counterpart to GFCA's own CLI, `analyze IR US`) needs a country pair the
// static build can't know about in advance. Same-origin fetch: this static
// site and the API are served by the same FastAPI process (see
// api/app.py's StaticFiles mount), so no CORS setup is needed.

const DOMAIN = 10;

// Renders the shared .gm-tension markup - the same class names
// TensionGauge.astro emits - so both gauges are styled by the single
// definition in global.css and cannot drift apart.
function Gauge({ value }: { value: number | null }) {
  const clamped = value == null ? 0 : Math.max(-DOMAIN, Math.min(DOMAIN, value));
  const halfPct = (Math.abs(clamped) / DOMAIN) * 50;
  const isPositive = clamped >= 0;
  const color = isPositive ? TENSION_DIVERGING.cooperation.dark : TENSION_DIVERGING.conflict.dark;
  const magnitude = Math.abs(clamped);
  const verdict = magnitude < 0.5 ? "broadly neutral" : magnitude < 3 ? "mildly" : magnitude < 6.5 ? "clearly" : "strongly";
  const ariaLabel =
    value == null
      ? "No tension data"
      : `Mean Goldstein score ${clamped.toFixed(2)} out of a possible minus 10 to plus 10, i.e. ${verdict} ${isPositive ? "cooperative" : "conflictual"}`;
  return (
    <div
      className="gm-tension"
      role="meter"
      aria-label={ariaLabel}
      aria-valuenow={value ?? undefined}
      aria-valuemin={-DOMAIN}
      aria-valuemax={DOMAIN}
    >
      <div className="gm-tension__track">
        <span className="gm-tension__center" aria-hidden="true"></span>
        {[-10, -5, 5, 10].map((t) => (
          <span key={t} className="gm-tension__tick" style={{ left: `${((t + DOMAIN) / (2 * DOMAIN)) * 100}%` }} aria-hidden="true"></span>
        ))}
        {value != null && (
          <div
            className="gm-tension__fill"
            style={{
              left: isPositive ? "50%" : `${50 - halfPct}%`,
              /* A hairline minimum so a real score of exactly 0.0 still
                 reads as "measured, and it was zero", not as missing. */
              width: `${Math.max(halfPct, 0.6)}%`,
              background: color,
            }}
          />
        )}
      </div>
      <div className="gm-tension__scale">
        <span>&minus;10</span>
        <span className="gm-tension__poles" aria-hidden="true">
          <span>Conflict</span>
          <span>Cooperation</span>
        </span>
        <span>+10</span>
      </div>
      <div className="gm-tension__readout">
        <span className="gm-tension__value">
          {value != null ? (clamped > 0 ? "+" : "") + clamped.toFixed(2) : "N/A"}
        </span>
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
          <div className="gm-panel">
            <div className="gm-panel__head">
              <h3 className="gm-panel__title">Geography</h3>
            </div>
            <div className="gm-panel__body">
            <WorldMap
              highlights={[
                { iso3: [queriedPair[0]], color: ENTITY_A_COLOR, label: nameFor(queriedPair[0]) },
                { iso3: [queriedPair[1]], color: ENTITY_B_COLOR, label: nameFor(queriedPair[1]) },
              ]}
            />
            </div>
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
          <p className="gm-note">
            Computed on demand from real GDELT events - not a prediction or forecast, and not the
            sole basis for any decision.
          </p>
        </div>
      )}
    </div>
  );
}
