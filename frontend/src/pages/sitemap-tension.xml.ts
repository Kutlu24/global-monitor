import type { APIRoute } from "astro";
import { urlEntry, urlset, getLastUpdated } from "../lib/sitemap";
import { PAIRS } from "../lib/pairs";

// Unlike the Risk module (a fixed content date - see sitemap-risk.xml.ts),
// Tension data genuinely refreshes every few hours, so the real
// getLastUpdated() signal is appropriate here, same as the structural
// bloc/compare/dimension pages.
export const GET: APIRoute = async ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const lastmod = await getLastUpdated();
  const entries = [
    urlEntry(`${base}/tension/`, lastmod),
    ...PAIRS.map((p) => urlEntry(`${base}/tension/${p.slug}/`, lastmod)),
  ];
  return new Response(urlset(entries), { headers: { "Content-Type": "application/xml" } });
};
