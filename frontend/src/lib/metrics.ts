import type { MetricSpec } from "../components/MetricCompareBars";

const usd = (v: number) => (Math.abs(v) >= 1e12 ? `$${(v / 1e12).toFixed(2)}T` : `$${(v / 1e9).toFixed(1)}B`);
const people = (v: number) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : `${v.toFixed(0)}`);
const pct = (v: number) => `${v.toFixed(1)}%`;
const years = (v: number) => `${v.toFixed(1)}y`;
const index01 = (v: number) => v.toFixed(3);

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
  economic: { metric_id: "gdp_current_usd", label: "GDP", format: usd },
  trade: { metric_id: "trade_exports_world_usd", label: "Exports to the world", format: usd },
  social: { metric_id: "population_total", label: "Population", format: people },
  military: { metric_id: "military_exp_usd", label: "Military expenditure", format: usd },
};

// Every metric belonging to each dimension - used on
// /compare/[pair]/[dimension].astro and /dimension/[dimension].astro.
export const DIMENSION_METRICS: Record<Dimension, MetricSpec[]> = {
  economic: [{ metric_id: "gdp_current_usd", label: "GDP (current US$)", format: usd }],
  trade: [
    { metric_id: "trade_exports_world_usd", label: "Exports to the world", format: usd },
    { metric_id: "trade_imports_world_usd", label: "Imports from the world", format: usd },
    { metric_id: "trade_pct_gdp", label: "Trade (% of GDP)", format: pct },
    { metric_id: "trade_intra_bloc_exports_usd", label: "Intra-bloc exports", format: usd },
  ],
  social: [
    { metric_id: "population_total", label: "Population", format: people },
    { metric_id: "life_expectancy_years", label: "Life expectancy at birth", format: years },
    { metric_id: "secondary_enrollment_pct", label: "Secondary school enrollment", format: pct },
    { metric_id: "hdi", label: "Human Development Index", format: index01 },
  ],
  military: [
    { metric_id: "military_exp_usd", label: "Military expenditure (current US$)", format: usd },
    { metric_id: "military_exp_pct_gdp", label: "Military expenditure (% of GDP)", format: pct },
  ],
};

export const ALL_METRICS: MetricSpec[] = DIMENSIONS.flatMap((d) => DIMENSION_METRICS[d]);
