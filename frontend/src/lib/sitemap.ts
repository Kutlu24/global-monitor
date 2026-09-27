// Shared helpers for the chunked sitemap endpoints (sitemap-*.xml.ts) -
// chunked by section (blocs, compare, dimensions) per the project plan's
// SEO section, even though the current ~65-URL total doesn't strictly
// need it yet - scales cleanly if per-metric time-series pages get added
// later (a realistic v2 feature that would multiply URL count 10-20x).
const API_URL = process.env.API_URL || "http://127.0.0.1:7860";

export async function getLastUpdated(): Promise<string> {
  try {
    const res = await fetch(`${API_URL}/api/last-updated`);
    const data = await res.json();
    return data.last_updated ?? new Date().toISOString();
  } catch {
    return new Date().toISOString();
  }
}

export function urlEntry(loc: string, lastmod: string): string {
  return `  <url>\n    <loc>${loc}</loc>\n    <lastmod>${lastmod}</lastmod>\n  </url>`;
}

export function urlset(entries: string[]): string {
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${entries.join("\n")}\n</urlset>`;
}

export function sitemapIndexEntry(loc: string, lastmod: string): string {
  return `  <sitemap>\n    <loc>${loc}</loc>\n    <lastmod>${lastmod}</lastmod>\n  </sitemap>`;
}
