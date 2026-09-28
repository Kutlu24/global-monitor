// BUILD-TIME ONLY. Do not import this from a `.tsx` island: it pulls in the
// whole 739 KB geometry file, which belongs in the browser as a plain
// `<fetch>` of /geo/countries-50m.json (see RiskMap.tsx), not as a bundled
// JS object. Only .astro frontmatter should reach for this.
//
// Its one job: work out which countries the map physically cannot draw, so
// the map can say so instead of silently leaving a country out. The previous
// 110m geometry left 43 of the 211 invisible - not greyed, *absent* - and
// nothing on the page said so. A reader seeing Singapore missing would
// reasonably conclude it wasn't scored, which was false: it was scored, and
// it just had no polygon at that resolution.

import atlas from "../../public/geo/countries-50m.json";
import { NUMERIC_TO_ISO3 } from "./iso3166Numeric";
import type { RiskCountry } from "./risk";

interface Geometry {
  id?: string;
  properties: { name: string };
}

const geometries = (atlas as unknown as {
  objects: { countries: { geometries: Geometry[] } };
}).objects.countries.geometries;

/**
 * Every alpha-3 the geometry file can actually paint.
 *
 * `id` is absent on the three polygons Natural Earth splits out of their
 * neighbours - Kosovo, Northern Cyprus, Somaliland. Kosovo is a real
 * scored country (World Bank reports it as XKX) and is keyed by name
 * instead; the other two are not in the dataset and stay undrawable,
 * correctly, because there is no World Bank observation to colour them with.
 */
export const DRAWABLE_ISO3: ReadonlySet<string> = new Set(
  geometries.flatMap((g) => {
    if (g.id != null) {
      const iso3 = NUMERIC_TO_ISO3[String(g.id)];
      return iso3 ? [iso3] : [];
    }
    return g.properties.name === "Kosovo" ? ["XKX"] : [];
  }),
);

/** Dataset countries this map cannot draw, by name, for the caption. */
export function undrawnCountries(countries: RiskCountry[]): string[] {
  return countries
    .filter((c) => !DRAWABLE_ISO3.has(c.iso3))
    .map((c) => c.name)
    .sort();
}
