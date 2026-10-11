// Sibling sites. Global Monitor is one of three public sites that link to each other:
//   Worldora              - hourly multilingual news digest (what is happening)
//   Global Monitor        - this site (structural bloc / country data)
//   Worldora Intelligence - evidence-based analysis workspace (what it may mean)
// Addresses are read at BUILD time so a purchased domain only needs an env change.
const clean = (u: string) => u.replace(/\/+$/, "");

export const WORLDORA_URL = clean(process.env.WORLDORA_URL || "https://kutlu24.github.io/worldora");
export const INTELLIGENCE_URL = process.env.INTELLIGENCE_URL || "https://gfca.onrender.com/ui/intel.html";

/** The practice that runs the three sites: its home page (static, DE/FR/EN). */
export const HUB_URL = clean(process.env.HUB_URL || "https://wintech-partners.onrender.com");
export const HUB_SITE_URL = `${HUB_URL}/en/`;
export const HUB_NAME = "Winterthur Tech Partners";

/** Worldora section that best matches the page being read. */
export function worldoraSectionFor(path: string): { slug: string; label: string } {
  if (path.startsWith("/tension")) return { slug: "defense", label: "Defense & Security" };
  if (path.startsWith("/dimension/military")) return { slug: "defense", label: "Defense & Security" };
  if (path.startsWith("/dimension/economic") || path.startsWith("/dimension/trade") || path.startsWith("/risk"))
    return { slug: "economy", label: "Economy" };
  return { slug: "world", label: "Foreign policy" };
}

export const worldoraSectionUrl = (slug: string) => `${WORLDORA_URL}/en/${slug}.html`;

/** Deep link into the Intelligence workspace's Ask view with the question prefilled. */
export function intelligenceAskUrl(question: string): string {
  return `${INTELLIGENCE_URL}#ask?q=${encodeURIComponent(question.slice(0, 300))}`;
}
export const intelligenceBriefingUrl = `${INTELLIGENCE_URL}#briefing`;
