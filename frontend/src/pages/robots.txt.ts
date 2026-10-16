import type { APIRoute } from "astro";

export const GET: APIRoute = ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const body = `User-agent: *\nAllow: /\nAllow: /hub/\nSitemap: ${base}/sitemap-index.xml\n`;
  return new Response(body, { headers: { "Content-Type": "text/plain" } });
};
