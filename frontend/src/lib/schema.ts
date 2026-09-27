// schema.org/Dataset JSON-LD builder - the real, underused differentiator
// for a data site specifically: tagging comparison pages this way surfaces
// them in Google's Dataset Search in addition to normal web search (see
// the project plan's SEO section). `distribution` links to this same
// page's own backing API endpoint as the machine-readable source.
export interface DatasetSchemaInput {
  name: string;
  description: string;
  url: string;
  apiPath: string;
  license?: string;
}

export function datasetSchema({ name, description, url, apiPath, license }: DatasetSchemaInput) {
  return {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name,
    description,
    url,
    license: license ?? "https://creativecommons.org/licenses/by/4.0/",
    creator: { "@type": "Organization", name: "Global Monitor" },
    distribution: {
      "@type": "DataDownload",
      encodingFormat: "application/json",
      contentUrl: apiPath,
    },
  };
}
