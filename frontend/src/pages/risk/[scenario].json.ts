import type { APIRoute } from "astro";
import { SCENARIOS, calculateScores } from "../../lib/risk";

// A real, static JSON distribution for each scenario's schema.org/Dataset
// markup to link to (see lib/schema.ts's `apiPath`) - this module has no
// Python backend behind it (see risk.ts's own module docstring), but the
// site's SEO approach elsewhere always backs a Dataset's `distribution`
// with a real machine-readable URL, not a page that merely claims to be
// one. Astro can generate this as a static file at build time same as any
// other page, no backend needed.
export async function getStaticPaths() {
  return SCENARIOS.map((s) => ({ params: { scenario: s.slug } }));
}

export const GET: APIRoute = ({ params }) => {
  const scenario = SCENARIOS.find((s) => s.slug === params.scenario)!;
  const ranked = calculateScores(scenario);
  return new Response(
    JSON.stringify({ scenario: scenario.name, weights: scenario.weights, ranking: ranked }, null, 2),
    { headers: { "Content-Type": "application/json" } },
  );
};
