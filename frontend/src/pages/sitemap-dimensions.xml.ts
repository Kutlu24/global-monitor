import type { APIRoute } from "astro";
import { DIMENSIONS } from "../lib/metrics";
import { getLastUpdated, localizedLocs, urlEntry, urlset } from "../lib/sitemap";

export const GET: APIRoute = async ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const lastmod = await getLastUpdated();
  const entries = DIMENSIONS.flatMap((d) =>
    localizedLocs(base, `/dimension/${d}/`).map((loc) => urlEntry(loc, lastmod)),
  );
  return new Response(urlset(entries), { headers: { "Content-Type": "application/xml" } });
};
