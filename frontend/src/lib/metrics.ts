export type FormatType = "usd" | "people" | "pct" | "years" | "index";

// The full spec, for .astro frontmatter (build-time only, where a real
// `format` function is fine to call directly). MetricCompareBars.tsx (a
// client island) defines its own narrower IslandMetricSpec
// ({metric_id, label, formatType}, all serializable) instead of importing
// this - see that file's own comment for why `format` itself can never
// cross the island boundary.
export interface MetricSpec {
  metric_id: string;
  label: string;
  format: (v: number) => string;
  formatType: FormatType;
}

const usd = (v: number) => (Math.abs(v) >= 1e12 ? `$${(v / 1e12).toFixed(2)}T` : `$${(v / 1e9).toFixed(1)}B`);
const people = (v: number) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : `${v.toFixed(0)}`);
const pct = (v: number) => `${v.toFixed(1)}%`;
const years = (v: number) => `${v.toFixed(1)}y`;
const index01 = (v: number) => v.toFixed(3);

// NOTE: `format` (a function) is only usable from .astro frontmatter, which
// runs entirely at build time - it can NEVER be passed as a prop into a
// client-hydrated island (MetricCompareBars.tsx): Astro serializes island
// props to JSON to embed in the page, and functions don't survive that
// (confirmed live: "TypeError: a.format is not a function" the first time
// this shipped, because a MetricSpec[] with real functions was passed
// straight into an island prop). `formatType` is the serializable
// (string) equivalent the island itself resolves via FORMATTERS below -
// always pass `formatType` to MetricCompareBars, never rely on `format`
// surviving the trip.
export const FORMATTERS: Record<FormatType, (v: number) => string> = { usd, people, pct, years, index: index01 };

export const DIMENSIONS = ["economic", "trade", "social", "military"] as const;
export type Dimension = (typeof DIMENSIONS)[number];

export const DIMENSION_LABELS: Record<Dimension, string> = {
  economic: "Economic",
  trade: "Trade",
  social: "Social",
  military: "Military",
};

// One headline metric per dimension - used on /compare/[pair].astro's
// 4-dimension overview and anywhere else a single representative number
// is wanted per dimension.
export const HEADLINE_METRIC: Record<Dimension, MetricSpec> = {
  economic: { metric_id: "gdp_current_usd", label: "GDP", format: usd, formatType: "usd" },
  trade: { metric_id: "trade_exports_world_usd", label: "Exports to the world", format: usd, formatType: "usd" },
  social: { metric_id: "population_total", label: "Population", format: people, formatType: "people" },
  military: { metric_id: "military_exp_usd", label: "Military expenditure", format: usd, formatType: "usd" },
};

// Every metric belonging to each dimension - used on
// /compare/[pair]/[dimension].astro and /dimension/[dimension].astro.
export const DIMENSION_METRICS: Record<Dimension, MetricSpec[]> = {
  economic: [{ metric_id: "gdp_current_usd", label: "GDP (current US$)", format: usd, formatType: "usd" }],
  trade: [
    { metric_id: "trade_exports_world_usd", label: "Exports to the world", format: usd, formatType: "usd" },
    { metric_id: "trade_imports_world_usd", label: "Imports from the world", format: usd, formatType: "usd" },
    { metric_id: "trade_pct_gdp", label: "Trade (% of GDP)", format: pct, formatType: "pct" },
    { metric_id: "trade_intra_bloc_exports_usd", label: "Intra-bloc exports", format: usd, formatType: "usd" },
  ],
  social: [
    { metric_id: "population_total", label: "Population", format: people, formatType: "people" },
    { metric_id: "life_expectancy_years", label: "Life expectancy at birth", format: years, formatType: "years" },
    { metric_id: "secondary_enrollment_pct", label: "Secondary school enrollment", format: pct, formatType: "pct" },
    { metric_id: "hdi", label: "Human Development Index", format: index01, formatType: "index" },
  ],
  military: [
    { metric_id: "military_exp_usd", label: "Military expenditure (current US$)", format: usd, formatType: "usd" },
    { metric_id: "military_exp_pct_gdp", label: "Military expenditure (% of GDP)", format: pct, formatType: "pct" },
  ],
};

export const ALL_METRICS: MetricSpec[] = DIMENSIONS.flatMap((d) => DIMENSION_METRICS[d]);
