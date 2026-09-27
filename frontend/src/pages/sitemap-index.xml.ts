import type { APIRoute } from "astro";
import { getLastUpdated, sitemapIndexEntry } from "../lib/sitemap";

export const GET: APIRoute = async ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const lastmod = await getLastUpdated();
  const body = `<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${[
    sitemapIndexEntry(`${base}/sitemap-blocs.xml`, lastmod),
    sitemapIndexEntry(`${base}/sitemap-compare.xml`, lastmod),
    sitemapIndexEntry(`${base}/sitemap-dimensions.xml`, lastmod),
  ].join("\n")}\n</sitemapindex>`;
  return new Response(body, { headers: { "Content-Type": "application/xml" } });
};
