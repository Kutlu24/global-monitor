import type { APIRoute } from "astro";

// Search-style AI crawlers are welcome; training-only crawlers are blocked.
const ALLOW = ["OAI-SearchBot", "ChatGPT-User", "PerplexityBot", "Claude-SearchBot", "Claude-User"];
const BLOCK = ["GPTBot", "ClaudeBot", "Google-Extended", "CCBot"];

export const GET: APIRoute = ({ site }) => {
  const base = site?.toString().replace(/\/$/, "") ?? "";
  const lines = ["User-agent: *", "Allow: /", "Allow: /hub/", ""];
  for (const bot of ALLOW) lines.push(`User-agent: ${bot}`, "Allow: /", "");
  for (const bot of BLOCK) lines.push(`User-agent: ${bot}`, "Disallow: /", "");
  lines.push(`Sitemap: ${base}/sitemap-index.xml`);
  return new Response(lines.join("\n") + "\n", { headers: { "Content-Type": "text/plain" } });
};
