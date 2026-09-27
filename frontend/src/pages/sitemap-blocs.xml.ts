import type { APIRoute } from "astro";
import { getBlocs, getCountries } from "../lib/data";
import { getLastUpdated, urlEntry, urlset } from "../lib/sitemap";

export const GET: APIRoute = async ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const lastmod = await getLastUpdated();
  const blocs = await getBlocs();
  const countries = await getCountries();
  const entries = [
    urlEntry(`${base}/`, lastmod),
    urlEntry(`${base}/countries/`, lastmod),
    ...blocs.map((b) => urlEntry(`${base}/bloc/${b.slug}/`, lastmod)),
    ...countries.map((c) => urlEntry(`${base}/country/${c.iso3.toLowerCase()}/`, lastmod)),
  ];
  return new Response(urlset(entries), { headers: { "Content-Type": "application/xml" } });
};
