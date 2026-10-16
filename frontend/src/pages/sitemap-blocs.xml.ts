import type { APIRoute } from "astro";
import { getBlocs, getCountries } from "../lib/data";
import { getLastUpdated, localizedLocs, urlEntry, urlset } from "../lib/sitemap";

export const GET: APIRoute = async ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const lastmod = await getLastUpdated();
  const blocs = await getBlocs();
  const countries = await getCountries();
  const entries = [
    ...localizedLocs(base, "/").map((loc) => urlEntry(loc, lastmod)),
    ...localizedLocs(base, "/countries/").map((loc) => urlEntry(loc, lastmod)),
    ...blocs.flatMap((b) => localizedLocs(base, `/bloc/${b.slug}/`).map((loc) => urlEntry(loc, lastmod))),
    ...countries.flatMap((c) =>
      localizedLocs(base, `/country/${c.iso3.toLowerCase()}/`).map((loc) => urlEntry(loc, lastmod)),
    ),
  ];
  return new Response(urlset(entries), { headers: { "Content-Type": "application/xml" } });
};
