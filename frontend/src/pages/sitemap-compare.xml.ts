import type { APIRoute } from "astro";
import { PAIRS } from "../lib/pairs";
import { DIMENSIONS } from "../lib/metrics";
import { getLastUpdated, urlEntry, urlset } from "../lib/sitemap";

export const GET: APIRoute = async ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const lastmod = await getLastUpdated();
  const entries = PAIRS.flatMap((p) => [
    urlEntry(`${base}/compare/${p.slug}/`, lastmod),
    ...DIMENSIONS.map((d) => urlEntry(`${base}/compare/${p.slug}/${d}/`, lastmod)),
  ]);
  return new Response(urlset(entries), { headers: { "Content-Type": "application/xml" } });
};
