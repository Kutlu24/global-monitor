import { defineConfig } from "astro/config";
import react from "@astrojs/react";

// SITE_URL comes from the same env var the FastAPI backend reads
// (config.py's `settings.site_url`) - empty is fine for local dev, but
// the real domain is required before canonical URLs/sitemaps mean
// anything in production (see the project plan's SEO section).
export default defineConfig({
  site: process.env.SITE_URL || "http://localhost:4321",
  integrations: [react()],
  output: "static",
});
