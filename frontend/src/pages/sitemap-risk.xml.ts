import type { APIRoute } from "astro";
import { urlEntry, urlset, getLastUpdated, localizedLocs } from "../lib/sitemap";
import { getRiskScenarios } from "../lib/data";

// Risk pages use the ETL's real `getLastUpdated()` now, not a hand-set
// constant. That constant existed precisely because the risk data was
// hardcoded and genuinely never changed, so borrowing the ETL timestamp
// would have overstated its freshness - the old comment said as much. With
// the data coming from World Bank/IMF/UNDP on a schedule, the real
// timestamp is now the accurate one.
export const GET: APIRoute = async ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const [scenarios, lastmod] = await Promise.all([getRiskScenarios(), getLastUpdated()]);
  const entries = [
    ...localizedLocs(base, "/risk/").map((loc) => urlEntry(loc, lastmod)),
    ...scenarios.flatMap((s) =>
      localizedLocs(base, `/risk/${s.slug}/`).map((loc) => urlEntry(loc, lastmod)),
    ),
  ];
  return new Response(urlset(entries), { headers: { "Content-Type": "application/xml" } });
};
