// Types and presentation helpers for the risk module - NO hardcoded country
// data.
//
// This file used to contain the entire model: 19 countries, 11 criteria
// scored 0-10 by hand, six scenario weight tables, and a `calculateScores()`
// that did the arithmetic in the browser at build time. The only comment
// that mattered was its own admission that the numbers were "100%
// hardcoded illustrative estimates ... never fetched from a live source",
// which is why it was the one page on the site with no ETL behind it.
//
// Everything data-shaped now comes from the FastAPI backend
// (GET /api/risk/scenarios and GET /api/risk/{slug}), which reads the same
// SQLite database as every other module - World Bank WDI, IMF WEO and UNDP
// HDR, refreshed on a schedule, scoring 211 countries. What remains here is
// the part that genuinely belongs in the frontend: TypeScript mirrors of
// the API payload, and the classed-bucket / label decisions that are a
// rendering concern, not a data concern.
//
// The types below are hand-written mirrors of risk.py's payload rather than
// generated from an OpenAPI schema; the build would catch drift only if the
// API changed shape, so see data.ts's `getRiskScenario` for the seam where
// that would be validated.

// -- API payload -----------------------------------------------------------
//
// Verified field-by-field against a live /api/risk/{slug} response, which is
// how the first cut of these types got them wrong: it assumed the scenario's
// own fields sat at the top level, when in fact the detail endpoint nests
// them under `scenario` and the catalogue endpoint flattens them. Both shapes
// are mirrored below, separately, because they genuinely differ.

/** An epicentre, as the API serialises it: an object, not a [lat, lon] tuple. */
export interface RiskEpicentre {
  lat: number;
  lon: number;
  label: string;
}

/** One record of GET /api/risk/scenarios - flat, and no country data. */
export interface RiskScenarioMeta {
  slug: string;
  name: string;
  weights: Record<string, number>;
  epicentres: RiskEpicentre[];
  explanation: string;
  /** What the scenario deliberately does NOT model. Rendered, not hidden. */
  not_measured: string;
  belligerents: string[];
}

export interface RiskCountry {
  iso3: string;
  name: string;
  /** 0-100, higher = holds together better. Absent when unranked. */
  structural_score?: number;
  /** Distance in km to the nearest scenario epicentre. Always present. */
  exposure_km: number;
  /** 0-100 within the scenario; 100 = closest. Only on ranked countries,
   *  because a percentile is meaningless without a population to rank
   *  against - and unranked countries are ranked against nobody. */
  exposure_percentile?: number;
  nuclear_armed: boolean;
  belligerent: boolean;
  ida_credit: boolean;
  /** criterion id -> 0-100. A criterion with too few inputs to score is
   *  absent rather than zero, and `completeness` says by how much. */
  criteria?: Record<string, number>;
  /** 0-1 share of the weighted criteria total that had enough data. */
  completeness?: number;
  /** Ranked countries only: the criterion ids the data was too thin for. */
  missing?: string[];
}

export interface RiskFlagMeta {
  label: string;
  basis: string;
}

/**
 * GET /api/risk/{slug}. Note the nesting: the scenario's own fields live
 * under `scenario`, the model-wide fields (criteria labels, weights, flag
 * documentation, axis definitions) sit alongside it, and the countries are
 * split by whether they could be scored at all.
 */
export interface RiskScenario {
  scenario: RiskScenarioMeta;
  /** criterion id -> display label, for rendering the weights table. */
  criteria: Record<string, string>;
  flags: Record<string, RiskFlagMeta>;
  /** Which axes exist and what each one means, so the UI never has to
   *  hardcode the axis names the backend decided on. */
  axes: Record<string, string>;
  /** Size of the ranked population, i.e. `ranked.length`, kept explicit by
   *  the API. Used only to cross-check, never as a substitute. */
  countries_ranked: number;
  universe: number;
  /** Total indicators across all six criteria. Divided into a country's
   *  `completeness` to get "scored on 20 of 22", so that count is never
   *  written into the UI by hand. */
  indicator_total: number;
  ranked: RiskCountry[];
  unranked: RiskCountry[];
}

// -- Axis presentation -----------------------------------------------------

/**
 * Which number each map colors by. These are TWO AXES, not one score: the
 * backend refuses to combine them and so does the UI. Every visual that
 * shows a country (map, ranking, watchlist) shows both, separately.
 */
export type RiskAxis = "structural" | "exposure";

export const RISK_AXES: Record<RiskAxis, {
  title: string;
  /** The one sentence that stops a reader combining the two axes. */
  caption: string;
  /** The scale's CSS custom-property prefix in global.css. */
  ramp: string;
  /** "Higher = stronger" vs "Higher = worse" - the legends must say which. */
  direction: string;
  /** Which end of the ramp is the "strong" end. False for exposure, where
   *  a small distance is the emphasised end. */
  higherIsStronger: boolean;
}> = {
  structural: {
    title: "Structural score",
    caption:
      "How well the country holds together on six socio-economic criteria. Excludes proximity to conflict and nuclear posture, which are reported separately and never folded in.",
    ramp: "--risk-struct",
    direction: "Higher = stronger",
    higherIsStronger: true,
  },
  exposure: {
    title: "Conflict exposure",
    caption:
      "Distance to the nearest scenario epicentre, in five equal-count bands. Purely geographic - it is not a prediction of who would be attacked.",
    ramp: "--risk-expo",
    // Not "darker". The emphasised end is the near end, but which end *looks*
    // heavier depends on the theme: in dark mode --risk-expo-1 is a dark
    // slate, in light mode it is a pale wash. Describing the ramp by its
    // lightness described one theme and contradicted the other, so say what
    // the number means instead.
    direction: "Closer = more exposed",
    higherIsStronger: false,
  },
};

/**
 * Five classes, and NOT at fixed 20-point intervals.
 *
 * The first cut used 0-20/20-40/.../80-100 for both axes, which is wrong for
 * the structural score and measurably so: because each criterion is itself a
 * percentile across 211 countries, percentiles bunch around 50, and the
 * weighted mean of six of them spans only about 18-73 in practice. Across
 * all six scenarios the top class (>=80) came back EMPTY every time and the
 * bottom class was empty in five of six - so the ramp was using three of its
 * five steps and the strongest countries on the page were never emphasised.
 *
 * Quantile classification fixes it by cutting the ramp at the data's own
 * quintiles, which is the standard treatment for percentile-derived values:
 * every class holds the same number of countries, so the strongest fifth is
 * always visibly distinct from the weakest fifth. The consequence is that the
 * legend has to print the real cut points rather than round numbers, and it
 * does - a legend that claimed "80-100" while nothing could reach 80 was
 * simply wrong, and quietly so.
 *
 * Exposure does not need this (a percentile already spans 0-100 by
 * definition, and the cuts land on 20/40/60/80 as expected), but the same
 * function serves both so there is one rule to reason about, not two.
 */
export type QuintileBreaks = [number, number, number, number];

/** The four cut points separating five equal-count classes. */
export function quintileBreaks(values: number[]): QuintileBreaks {
  const sorted = [...values].sort((a, b) => a - b);
  if (!sorted.length) return [20, 40, 60, 80];
  const at = (q: number) => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))];
  return [at(0.2), at(0.4), at(0.6), at(0.8)];
}

/**
 * 1..5 for a value, ascending - the 5th quintile gets the strongest colour.
 * `higherIsStronger: false` inverts it, which is what exposure needs: there
 * a small distance is the "strong" end of the ramp, because the ramp's
 * meaning is "closer to the conflict", not "more of something good".
 */
export function bucketFor(value: number, breaks: QuintileBreaks, higherIsStronger = true): 1 | 2 | 3 | 4 | 5 {
  const base: 1 | 2 | 3 | 4 | 5 =
    value >= breaks[3] ? 5 : value >= breaks[2] ? 4 : value >= breaks[1] ? 3 : value >= breaks[0] ? 2 : 1;
  return higherIsStronger ? base : ((6 - base) as 1 | 2 | 3 | 4 | 5);
}

/** Legend labels for a set of breaks, phrased as the real class edges. */
export function breakLabels(breaks: QuintileBreaks): string[] {
  const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));
  return [
    `<${fmt(breaks[0])}`,
    `${fmt(breaks[0])}-${fmt(breaks[1])}`,
    `${fmt(breaks[1])}-${fmt(breaks[2])}`,
    `${fmt(breaks[2])}-${fmt(breaks[3])}`,
    `${fmt(breaks[3])}+`,
  ];
}

export function rampVar(axis: RiskAxis, bucket: number): string {
  return `var(${RISK_AXES[axis].ramp}-${bucket})`;
}

// -- Formatting ------------------------------------------------------------

const NUM = new Intl.NumberFormat("en-US");

export function fmtKm(km: number): string {
  // Under 1,000 km a decimal is noise at choropleth scale, and rounding to
  // whole km keeps the column narrow enough to fit the flags beside it.
  return `${NUM.format(Math.round(km))} km`;
}

export function fmtScore(score: number | undefined): string {
  return score === undefined ? "—" : score.toFixed(1);
}

export function fmtPct(v: number): string {
  return `${Math.round(v * 100)}%`;
}
