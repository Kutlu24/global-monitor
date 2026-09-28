import type { APIRoute } from "astro";
import { getRiskScenarios, getRiskScenario } from "../../lib/data";

// A real, static JSON distribution for each scenario's schema.org/Dataset
// markup (see lib/schema.ts's `apiPath`). This used to serialise a
// hardcoded module with a `calculateScores()` call in it; now it mirrors
// what the live endpoint returns, so a Dataset's `distribution` points at
// genuinely the same numbers the page shows.
//
// The payload is the API's own, with two deliberate changes: `ranked` and
// `unranked` are merged into one `countries` array (the split is a
// rendering detail - a consumer wants every country) and the two axes stay
// separate keys, never a merged score.
export async function getStaticPaths() {
  const scenarios = await getRiskScenarios();
  return scenarios.map((s) => ({ params: { scenario: s.slug } }));
}

export const GET: APIRoute = async ({ params }) => {
  const data = await getRiskScenario(params.scenario!);
  const { ranked, unranked, ...meta } = data;
  return new Response(
    // `scenario` stays nested rather than being spread to the top level, so
    // this file is the API's own payload with one documented change: the
    // ranked/unranked split - a rendering detail, since a consumer wants
    // every country - is merged into one `countries` array. The two axes
    // remain separate keys and are never merged into a single score.
    JSON.stringify({ ...meta, countries: [...ranked, ...unranked] }, null, 2),
    { headers: { "Content-Type": "application/json" } },
  );
};
