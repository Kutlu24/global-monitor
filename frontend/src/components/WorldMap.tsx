import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { NUMERIC_TO_ISO3 } from "../lib/iso3166Numeric";
import { NEUTRAL_MAP_FILL } from "../lib/colors";

// The "emphasis" form (dataviz skill: "one series is the point, rest are
// context -> emphasis, highlight one, gray the rest"), not a full
// categorical choropleth - deliberately. A choropleth showing all 4-5
// blocs' colors simultaneously would need every pair of those colors to
// pass the palette's stricter "all-pairs" CVD check (any two map regions
// can sit side by side), which caps this specific reference palette at 3
// mutually-safe hues - not enough for 4 real blocs. Emphasis sidesteps the
// cap entirely: at most 2 highlight colors are ever shown on one map (a
// single bloc's own page, or a compare-pair page's two blocs), well within
// the 2-hue safe zone, with every non-highlighted country in one neutral
// gray as context.
//
// Real SVG (react-simple-maps -> d3-geo), no WebGL/canvas - crawlable DOM,
// good Core Web Vitals. Hydrated as a client:visible Astro island (see the
// .astro pages that use this) since the topojson itself is fetched
// client-side; the actual bloc-membership DATA is already real static text
// elsewhere on the same page, so this island is a visual supplement, never
// the only place the information exists.

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

export interface Highlight {
  iso3: string[];
  color: string; // resolved hex (light or dark already picked by the caller)
  label: string;
}

interface Props {
  highlights: Highlight[]; // 1 or 2 - see the module comment above
}

export default function WorldMap({ highlights }: Props) {
  const iso3ToHighlight = new Map<string, Highlight>();
  for (const h of highlights) {
    for (const iso3 of h.iso3) iso3ToHighlight.set(iso3, h);
  }

  return (
    <div className="gm-world-map">
      <style>{`
        .gm-world-map { --gm-neutral: ${NEUTRAL_MAP_FILL.dark}; --gm-stroke: #1e1e1e; }
        :root[data-theme="light"] .gm-world-map { --gm-neutral: ${NEUTRAL_MAP_FILL.light}; --gm-stroke: #fcfcfb; }
        .gm-legend { display: flex; gap: 1.5rem; margin-bottom: 0.75rem; font-size: 0.9rem; }
        .gm-legend-item { display: flex; align-items: center; gap: 0.4rem; }
        .gm-legend-swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
      `}</style>
      <div className="gm-legend" role="list" aria-label="Map legend">
        {highlights.map((h) => (
          <span className="gm-legend-item" role="listitem" key={h.label}>
            <span className="gm-legend-swatch" style={{ background: h.color }} />
            {h.label}
          </span>
        ))}
      </div>
      <ComposableMap projectionConfig={{ scale: 140 }} width={800} height={420} role="img" aria-label="World map with highlighted countries">
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo) => {
              const iso3 = NUMERIC_TO_ISO3[geo.id as string];
              const highlight = iso3 ? iso3ToHighlight.get(iso3) : undefined;
              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  strokeWidth={0.5}
                  style={{
                    default: { fill: highlight ? highlight.color : "var(--gm-neutral)", stroke: "var(--gm-stroke)", outline: "none" },
                    hover: { fill: highlight ? highlight.color : "var(--gm-neutral)", stroke: "var(--gm-stroke)", outline: "none", opacity: highlight ? 0.85 : 1 },
                    pressed: { fill: highlight ? highlight.color : "var(--gm-neutral)", stroke: "var(--gm-stroke)", outline: "none" },
                  }}
                >
                  <title>{highlight ? `${geo.properties.name} — ${highlight.label}` : geo.properties.name}</title>
                </Geography>
              );
            })
          }
        </Geographies>
      </ComposableMap>
    </div>
  );
}
