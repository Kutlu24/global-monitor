import { useState } from "react";
import { TENSION_DIVERGING } from "../lib/colors";
import type { CountryRef, TensionScore } from "../lib/tension";
import WorldMap from "./WorldMap";
import { t as tRaw, type Lang } from "../i18n/ui";

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

// Client-side twin of createI18n - the island can't call Astro's server
// helper, but ui.ts's raw t() is pure data lookup, safe in the browser.
function makeT(lang: Lang) {
  return (key: string, vars?: Record<string, string | number>) => tRaw(lang, key, vars);
}

// Renders the shared .gm-tension markup - the same class names
// TensionGauge.astro emits - so both gauges are styled by the single
// definition in global.css and cannot drift apart.
function Gauge({ value, lang }: { value: number | null; lang: Lang }) {
  const t = makeT(lang);
  const clamped = value == null ? 0 : Math.max(-DOMAIN, Math.min(DOMAIN, value));
  const halfPct = (Math.abs(clamped) / DOMAIN) * 50;
  const isPositive = clamped >= 0;
  const color = isPositive ? TENSION_DIVERGING.cooperation.dark : TENSION_DIVERGING.conflict.dark;
  const magnitude = Math.abs(clamped);
  const verdictKey =
    magnitude < 0.5 ? "tension.verdict.neutral" : magnitude < 3 ? "tension.verdict.mildly" : magnitude < 6.5 ? "tension.verdict.clearly" : "tension.verdict.strongly";
  const poleKey = isPositive ? "tension.pole.cooperative" : "tension.pole.conflictual";
  const ariaLabel =
    value == null
      ? t("tension.aria.noData")
      : t("tension.aria.score", {
          value: clamped.toFixed(2),
          verdict: t(verdictKey),
          pole: t(poleKey),
        });
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
        {[-10, -5, 5, 10].map((tick) => (
          <span key={tick} className="gm-tension__tick" style={{ left: `${((tick + DOMAIN) / (2 * DOMAIN)) * 100}%` }} aria-hidden="true"></span>
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
          <span>{t("tension.pole.conflict")}</span>
          <span>{t("tension.pole.cooperation")}</span>
        </span>
        <span>+10</span>
      </div>
      <div className="gm-tension__readout">
        <span className="gm-tension__value">
          {value != null ? (clamped > 0 ? "+" : "") + clamped.toFixed(2) : t("table.na")}
        </span>
      </div>
    </div>
  );
}

interface Props {
  countries: CountryRef[];
  lang?: Lang;
}

export default function CountryTensionQuery({ countries, lang = "en" }: Props) {
  const t = makeT(lang);
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
      setErrorMessage(t("tension.query.sameCountries"));
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
      setErrorMessage(err instanceof Error ? err.message : t("tension.query.error"));
    }
  }

  const conflictual = result?.examples.filter((e) => e.kind === "conflictual") ?? [];
  const cooperative = result?.examples.filter((e) => e.kind === "cooperative") ?? [];
  const nameFor = (iso3: string) => countries.find((c) => c.iso3 === iso3)?.name ?? iso3;

  return (
    <div className="gm-country-query">
      <div className="gm-country-query-form">
        <label className="gm-country-query-field">
          {t("tension.query.countryA")}
          <select value={a} onChange={(e) => setA(e.target.value)}>
            {countries.map((c) => <option key={c.iso3} value={c.iso3}>{c.name} ({c.iso3})</option>)}
          </select>
        </label>
        <label className="gm-country-query-field">
          {t("tension.query.countryB")}
          <select value={b} onChange={(e) => setB(e.target.value)}>
            {countries.map((c) => <option key={c.iso3} value={c.iso3}>{c.name} ({c.iso3})</option>)}
          </select>
        </label>
        <button onClick={run} disabled={status === "loading"}>
          {status === "loading" ? t("tension.query.analyzing") : t("tension.query.submit")}
        </button>
      </div>
      {status === "error" && <p className="gm-country-query-error">{errorMessage}</p>}

      {result && queriedPair && (
        <div className="gm-country-query-result">
          <div className="gm-panel">
            <div className="gm-panel__head">
              <h3 className="gm-panel__title">{t("tension.query.geography")}</h3>
            </div>
            <div className="gm-panel__body">
            <WorldMap
              highlights={[
                { iso3: [queriedPair[0]], color: ENTITY_A_COLOR, label: nameFor(queriedPair[0]) },
                { iso3: [queriedPair[1]], color: ENTITY_B_COLOR, label: nameFor(queriedPair[1]) },
              ]}
              lang={lang}
            />
            </div>
          </div>
          <Gauge value={result.mean_goldstein} lang={lang} />
          <p className="gm-stat-label">
            {t("tension.query.bilateralWindow", { n: result.n_events, h: result.window_hours })}
            {result.conflict_share != null && ` · ${t("tension.query.conflictShare", { pct: `${(result.conflict_share * 100).toFixed(0)}%` })}`}
          </p>

          {conflictual.length > 0 && (
            <>
              <h3>{t("tension.mostConflictual")}</h3>
              <ul>
                {conflictual.map((e, i) => (
                  <li key={i}>
                    [{e.date}] {e.actor1 ?? "?"} &rarr; {e.actor2 ?? "?"}
                    {e.location && ` at ${e.location}`}
                    {e.goldstein != null && ` (Goldstein ${e.goldstein.toFixed(1)})`}
                    {e.source_url && <> — <a href={e.source_url} target="_blank" rel="noopener noreferrer">{t("tension.source")}</a></>}
                  </li>
                ))}
              </ul>
            </>
          )}
          {cooperative.length > 0 && (
            <>
              <h3>{t("tension.mostCooperative")}</h3>
              <ul>
                {cooperative.map((e, i) => (
                  <li key={i}>
                    [{e.date}] {e.actor1 ?? "?"} &rarr; {e.actor2 ?? "?"}
                    {e.location && ` at ${e.location}`}
                    {e.goldstein != null && ` (Goldstein ${e.goldstein.toFixed(1)})`}
                    {e.source_url && <> — <a href={e.source_url} target="_blank" rel="noopener noreferrer">{t("tension.source")}</a></>}
                  </li>
                ))}
              </ul>
            </>
          )}
          {result.n_events === 0 && (
            <p>{t("tension.query.noEvents", { h: result.window_hours })}</p>
          )}
          <p className="gm-note">{t("tension.query.note")}</p>
        </div>
      )}
    </div>
  );
}
