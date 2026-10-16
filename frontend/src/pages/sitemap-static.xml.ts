import type { APIRoute } from "astro";
import { getLastUpdated, localizedLocs, urlEntry, urlset } from "../lib/sitemap";

// Static structural pages that aren't backed by API content: the Geo
// Analysis Hub itself. Emitted per language like every other page.
export const GET: APIRoute = async ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const lastmod = await getLastUpdated();
  const entries = localizedLocs(base, "/hub/").map((loc) => urlEntry(loc, lastmod));
  return new Response(urlset(entries), { headers: { "Content-Type": "application/xml" } });
};
