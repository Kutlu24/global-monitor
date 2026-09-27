// Global Risk Simulator - ported from the standalone `risk-simulator-pro`
// Streamlit app (same author, same project family) into Global Monitor as
// a static module rather than a separate deployment. This data is 100%
// hardcoded illustrative estimates (11 resilience criteria, scored 0-10 by
// hand), never fetched from a live source - unlike every other page on
// this site, there is no ETL/API backing it, so unlike bloc/compare pages
// this lives as a plain TS module (unchanging reference data), not routed
// through the FastAPI backend. See the original repo's own README: "The
// country scores are illustrative estimates for scenario exploration, not
// a rigorous geopolitical risk model" - that caveat is preserved verbatim
// on every page that renders this data.

export interface RiskCountry {
  name: string;
  iso3: string;
  criteria: Record<string, number>;
}

export const CRITERIA = [
  "Geographic Isolation",
  "Nuclear Risk",
  "Political Neutrality",
  "Economic Resilience",
  "Domestic Social Stability",
  "Infrastructure & Health",
  "Public Preparedness",
  "Climate Resilience",
  "Energy Independence",
  "Cybersecurity",
  "Demographic Resilience",
] as const;

export const RISK_COUNTRIES: RiskCountry[] = [
  { name: "New Zealand", iso3: "NZL", criteria: { "Geographic Isolation": 9, "Nuclear Risk": 10, "Political Neutrality": 10, "Economic Resilience": 8, "Domestic Social Stability": 9, "Infrastructure & Health": 9, "Public Preparedness": 6, "Climate Resilience": 8, "Energy Independence": 6, "Cybersecurity": 8, "Demographic Resilience": 8 } },
  { name: "Iceland", iso3: "ISL", criteria: { "Geographic Isolation": 10, "Nuclear Risk": 10, "Political Neutrality": 9, "Economic Resilience": 7, "Domestic Social Stability": 10, "Infrastructure & Health": 9, "Public Preparedness": 6, "Climate Resilience": 6, "Energy Independence": 10, "Cybersecurity": 8, "Demographic Resilience": 7 } },
  { name: "Switzerland", iso3: "CHE", criteria: { "Geographic Isolation": 5, "Nuclear Risk": 10, "Political Neutrality": 10, "Economic Resilience": 10, "Domestic Social Stability": 10, "Infrastructure & Health": 10, "Public Preparedness": 10, "Climate Resilience": 7, "Energy Independence": 7, "Cybersecurity": 9, "Demographic Resilience": 6 } },
  { name: "Uruguay", iso3: "URY", criteria: { "Geographic Isolation": 7, "Nuclear Risk": 10, "Political Neutrality": 10, "Economic Resilience": 7, "Domestic Social Stability": 9, "Infrastructure & Health": 8, "Public Preparedness": 5, "Climate Resilience": 9, "Energy Independence": 8, "Cybersecurity": 6, "Demographic Resilience": 7 } },
  { name: "Ireland", iso3: "IRL", criteria: { "Geographic Isolation": 8, "Nuclear Risk": 10, "Political Neutrality": 10, "Economic Resilience": 8, "Domestic Social Stability": 9, "Infrastructure & Health": 9, "Public Preparedness": 5, "Climate Resilience": 7, "Energy Independence": 5, "Cybersecurity": 8, "Demographic Resilience": 8 } },
  { name: "Costa Rica", iso3: "CRI", criteria: { "Geographic Isolation": 7, "Nuclear Risk": 10, "Political Neutrality": 10, "Economic Resilience": 6, "Domestic Social Stability": 9, "Infrastructure & Health": 7, "Public Preparedness": 4, "Climate Resilience": 8, "Energy Independence": 8, "Cybersecurity": 5, "Demographic Resilience": 8 } },
  { name: "Chile", iso3: "CHL", criteria: { "Geographic Isolation": 9, "Nuclear Risk": 10, "Political Neutrality": 8, "Economic Resilience": 7, "Domestic Social Stability": 6, "Infrastructure & Health": 7, "Public Preparedness": 5, "Climate Resilience": 8, "Energy Independence": 6, "Cybersecurity": 6, "Demographic Resilience": 7 } },
  { name: "Australia", iso3: "AUS", criteria: { "Geographic Isolation": 9, "Nuclear Risk": 9, "Political Neutrality": 6, "Economic Resilience": 9, "Domestic Social Stability": 8, "Infrastructure & Health": 9, "Public Preparedness": 7, "Climate Resilience": 7, "Energy Independence": 9, "Cybersecurity": 9, "Demographic Resilience": 9 } },
  { name: "Canada", iso3: "CAN", criteria: { "Geographic Isolation": 7, "Nuclear Risk": 6, "Political Neutrality": 4, "Economic Resilience": 9, "Domestic Social Stability": 9, "Infrastructure & Health": 9, "Public Preparedness": 6, "Climate Resilience": 9, "Energy Independence": 10, "Cybersecurity": 9, "Demographic Resilience": 9 } },
  { name: "Finland", iso3: "FIN", criteria: { "Geographic Isolation": 4, "Nuclear Risk": 5, "Political Neutrality": 3, "Economic Resilience": 8, "Domestic Social Stability": 10, "Infrastructure & Health": 10, "Public Preparedness": 10, "Climate Resilience": 7, "Energy Independence": 7, "Cybersecurity": 9, "Demographic Resilience": 5 } },
  { name: "Portugal", iso3: "PRT", criteria: { "Geographic Isolation": 7, "Nuclear Risk": 6, "Political Neutrality": 5, "Economic Resilience": 7, "Domestic Social Stability": 8, "Infrastructure & Health": 8, "Public Preparedness": 5, "Climate Resilience": 6, "Energy Independence": 3, "Cybersecurity": 7, "Demographic Resilience": 4 } },
  { name: "Malaysia", iso3: "MYS", criteria: { "Geographic Isolation": 6, "Nuclear Risk": 7, "Political Neutrality": 7, "Economic Resilience": 8, "Domestic Social Stability": 7, "Infrastructure & Health": 8, "Public Preparedness": 4, "Climate Resilience": 7, "Energy Independence": 8, "Cybersecurity": 7, "Demographic Resilience": 7 } },
  { name: "Botswana", iso3: "BWA", criteria: { "Geographic Isolation": 8, "Nuclear Risk": 10, "Political Neutrality": 9, "Economic Resilience": 5, "Domestic Social Stability": 8, "Infrastructure & Health": 5, "Public Preparedness": 3, "Climate Resilience": 6, "Energy Independence": 4, "Cybersecurity": 3, "Demographic Resilience": 8 } },
  { name: "Argentina", iso3: "ARG", criteria: { "Geographic Isolation": 9, "Nuclear Risk": 10, "Political Neutrality": 8, "Economic Resilience": 3, "Domestic Social Stability": 4, "Infrastructure & Health": 6, "Public Preparedness": 4, "Climate Resilience": 9, "Energy Independence": 7, "Cybersecurity": 5, "Demographic Resilience": 6 } },
  { name: "Japan", iso3: "JPN", criteria: { "Geographic Isolation": 8, "Nuclear Risk": 7, "Political Neutrality": 5, "Economic Resilience": 9, "Domestic Social Stability": 9, "Infrastructure & Health": 10, "Public Preparedness": 8, "Climate Resilience": 5, "Energy Independence": 3, "Cybersecurity": 9, "Demographic Resilience": 2 } },
  { name: "Italy", iso3: "ITA", criteria: { "Geographic Isolation": 6, "Nuclear Risk": 6, "Political Neutrality": 5, "Economic Resilience": 7, "Domestic Social Stability": 7, "Infrastructure & Health": 9, "Public Preparedness": 6, "Climate Resilience": 5, "Energy Independence": 2, "Cybersecurity": 8, "Demographic Resilience": 2 } },
  { name: "China", iso3: "CHN", criteria: { "Geographic Isolation": 4, "Nuclear Risk": 5, "Political Neutrality": 3, "Economic Resilience": 8, "Domestic Social Stability": 6, "Infrastructure & Health": 8, "Public Preparedness": 7, "Climate Resilience": 5, "Energy Independence": 4, "Cybersecurity": 8, "Demographic Resilience": 3 } },
  { name: "Russia", iso3: "RUS", criteria: { "Geographic Isolation": 3, "Nuclear Risk": 4, "Political Neutrality": 3, "Economic Resilience": 5, "Domestic Social Stability": 4, "Infrastructure & Health": 7, "Public Preparedness": 8, "Climate Resilience": 8, "Energy Independence": 9, "Cybersecurity": 6, "Demographic Resilience": 3 } },
  { name: "India", iso3: "IND", criteria: { "Geographic Isolation": 5, "Nuclear Risk": 6, "Political Neutrality": 6, "Economic Resilience": 6, "Domestic Social Stability": 6, "Infrastructure & Health": 5, "Public Preparedness": 5, "Climate Resilience": 7, "Energy Independence": 4, "Cybersecurity": 6, "Demographic Resilience": 9 } },
];

// This data is static (see the module docstring above) - unlike bloc pages'
// lastmod (real ETL freshness), a fixed date here is the honest signal:
// the content genuinely hasn't changed since this date, so claiming
// otherwise via a rolling "last updated" timestamp would mislead crawlers.
// Bump this only when RISK_COUNTRIES/SCENARIOS actually change.
export const RISK_CONTENT_DATE = "2026-09-27";

export interface Scenario {
  id: string;
  slug: string;
  name: string;
  weights: Record<string, number>;
  explanation: string;
}

export const SCENARIOS: Scenario[] = [
  {
    id: "1", slug: "general-balanced-crisis", name: "General Balanced Crisis",
    weights: { "Geographic Isolation": 0.15, "Nuclear Risk": 0.15, "Political Neutrality": 0.10, "Economic Resilience": 0.10, "Domestic Social Stability": 0.10, "Infrastructure & Health": 0.10, "Public Preparedness": 0.05, "Climate Resilience": 0.05, "Energy Independence": 0.05, "Cybersecurity": 0.05, "Demographic Resilience": 0.05 },
    explanation: "A baseline starting point in which all factors are weighted in a balanced way.",
  },
  {
    id: "2", slug: "russia-nato-conflict", name: "Russia-NATO Conflict",
    weights: { "Geographic Isolation": 0.25, "Nuclear Risk": 0.25, "Political Neutrality": 0.20, "Economic Resilience": 0.05, "Domestic Social Stability": 0.05, "Infrastructure & Health": 0.0, "Public Preparedness": 0.05, "Climate Resilience": 0.0, "Energy Independence": 0.10, "Cybersecurity": 0.05, "Demographic Resilience": 0.0 },
    explanation: "Geographic distance, neutrality, and staying off nuclear target lists become the most important factors. Southern-hemisphere countries and isolated islands stand out.",
  },
  {
    id: "3", slug: "china-us-tension", name: "China-US Tension (Economic Crisis)",
    weights: { "Geographic Isolation": 0.15, "Nuclear Risk": 0.05, "Political Neutrality": 0.15, "Economic Resilience": 0.25, "Domestic Social Stability": 0.10, "Infrastructure & Health": 0.05, "Public Preparedness": 0.0, "Climate Resilience": 0.10, "Energy Independence": 0.05, "Cybersecurity": 0.10, "Demographic Resilience": 0.0 },
    explanation: "Economic self-sufficiency, strong industry, and low dependence on technology imports become critical. Economies away from the Pacific-Atlantic rivalry hold the advantage.",
  },
  {
    id: "4", slug: "hormuz-energy-shock", name: "Strait of Hormuz Crisis (Energy Shock)",
    weights: { "Geographic Isolation": 0.10, "Nuclear Risk": 0.0, "Political Neutrality": 0.05, "Economic Resilience": 0.20, "Domestic Social Stability": 0.15, "Infrastructure & Health": 0.05, "Public Preparedness": 0.0, "Climate Resilience": 0.10, "Energy Independence": 0.30, "Cybersecurity": 0.0, "Demographic Resilience": 0.05 },
    explanation: "Energy independence overrides everything else. Net energy exporters (Canada, Australia) and renewable-energy leaders (Iceland, Uruguay) come out ahead in this crisis.",
  },
  {
    id: "5", slug: "climate-water-wars", name: "Climate Crisis & Water Wars",
    weights: { "Geographic Isolation": 0.15, "Nuclear Risk": 0.0, "Political Neutrality": 0.05, "Economic Resilience": 0.10, "Domestic Social Stability": 0.20, "Infrastructure & Health": 0.10, "Public Preparedness": 0.0, "Climate Resilience": 0.30, "Energy Independence": 0.0, "Cybersecurity": 0.0, "Demographic Resilience": 0.10 },
    explanation: "Countries with water and food resources, temperate climates, distance from migration routes, and social cohesion become the safest places. Isolation and resource wealth are key.",
  },
  {
    id: "6", slug: "tech-energy-revolution", name: "Technological Energy Revolution",
    weights: { "Geographic Isolation": 0.0, "Nuclear Risk": 0.0, "Political Neutrality": 0.05, "Economic Resilience": 0.30, "Domestic Social Stability": 0.20, "Infrastructure & Health": 0.10, "Public Preparedness": 0.0, "Climate Resilience": 0.0, "Energy Independence": 0.0, "Cybersecurity": 0.20, "Demographic Resilience": 0.15 },
    explanation: "Diversified, innovative, high-tech economies not dependent on fossil fuels come out ahead. A young, educated population is a major advantage.",
  },
];

export function findScenario(slug: string): Scenario | undefined {
  return SCENARIOS.find((s) => s.slug === slug);
}

export interface RankedCountry {
  rank: number; // 1-based
  name: string;
  iso3: string;
  score: number;
  tier: "good" | "warning" | "critical";
  tierLabel: "Resilient" | "Moderate" | "Vulnerable";
}

// Same tier-by-rank-position split as the original tool: top third / middle
// third / bottom third of the 19 ranked countries, not a fixed score
// threshold - the tool is about RELATIVE standing under a given scenario,
// not an absolute pass/fail score.
function tierForRank(rankZeroBased: number, n: number): Pick<RankedCountry, "tier" | "tierLabel"> {
  const third = n / 3;
  if (rankZeroBased < third) return { tier: "good", tierLabel: "Resilient" };
  if (rankZeroBased < 2 * third) return { tier: "warning", tierLabel: "Moderate" };
  return { tier: "critical", tierLabel: "Vulnerable" };
}

export function calculateScores(scenario: Scenario): RankedCountry[] {
  const scored = RISK_COUNTRIES.map((c) => {
    let score = 0;
    for (const criterion of CRITERIA) {
      score += (c.criteria[criterion] ?? 0) * (scenario.weights[criterion] ?? 0);
    }
    return { name: c.name, iso3: c.iso3, score };
  });
  scored.sort((a, b) => b.score - a.score);
  return scored.map((c, i) => ({ rank: i + 1, ...c, ...tierForRank(i, scored.length) }));
}
