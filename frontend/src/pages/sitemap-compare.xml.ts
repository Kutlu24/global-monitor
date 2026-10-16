import type { APIRoute } from "astro";
import { PAIRS } from "../lib/pairs";
import { DIMENSIONS } from "../lib/metrics";
import { getLastUpdated, localizedLocs, urlEntry, urlset } from "../lib/sitemap";

export const GET: APIRoute = async ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const lastmod = await getLastUpdated();
  const entries = PAIRS.flatMap((p) => [
    ...localizedLocs(base, `/compare/${p.slug}/`).map((loc) => urlEntry(loc, lastmod)),
    ...DIMENSIONS.flatMap((d) =>
      localizedLocs(base, `/compare/${p.slug}/${d}/`).map((loc) => urlEntry(loc, lastmod)),
    ),
  ]);
  return new Response(urlset(entries), { headers: { "Content-Type": "application/xml" } });
};
