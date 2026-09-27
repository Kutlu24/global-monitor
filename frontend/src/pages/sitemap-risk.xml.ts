import type { APIRoute } from "astro";
import { urlEntry, urlset } from "../lib/sitemap";
import { SCENARIOS, RISK_CONTENT_DATE } from "../lib/risk";

// Risk pages use a fixed content date, not the ETL's getLastUpdated() - see
// RISK_CONTENT_DATE's own comment in lib/risk.ts (this data doesn't change
// with the daily/weekly ETL, so borrowing that timestamp would overstate
// how fresh this specific content is).
export const GET: APIRoute = ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const entries = [
    urlEntry(`${base}/risk/`, RISK_CONTENT_DATE),
    ...SCENARIOS.map((s) => urlEntry(`${base}/risk/${s.slug}/`, RISK_CONTENT_DATE)),
  ];
  return new Response(urlset(entries), { headers: { "Content-Type": "application/xml" } });
};
