import { ComposableMap, Geographies, Geography, Graticule } from "react-simple-maps";
import { NUMERIC_TO_ISO3 } from "../lib/iso3166Numeric";

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
//
// The map is drawn as a WELL: its own background darker than --page, with
// graticule / land / border as three further tokens (global.css). That
// separation is what stops it reading as a flat SVG pasted on the page.
// Background / graticule / land / border are deliberately four values
// rather than one gray: it is the same reason a chart needs an axis.

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

export interface Highlight {
  iso3: string[];
  /** A CSS color. Almost always `var(--bloc-<id>)` so the fill follows the
   *  active theme automatically - the previous version passed a pre-resolved
   *  hex, which meant the bloc page drew light-mode values on the dark
   *  default while every other map drew dark-mode ones. */
  color: string;
  label: string;
}

interface Props {
  highlights: Highlight[]; // 1 or 2 - see the module comment above
}

const MAP_W = 1000;
const MAP_H = 520;

export default function WorldMap({ highlights }: Props) {
  const iso3ToHighlight = new Map<string, Highlight>();
  for (const h of highlights) {
    for (const iso3 of h.iso3) iso3ToHighlight.set(iso3, h);
  }

  return (
    <figure className="gm-map">
      <div className="gm-map__legend" role="list" aria-label="Map legend">
        {highlights.map((h) => (
          <span className="gm-map__legend-item" role="listitem" key={h.label}>
            <span className="gm-map__legend-swatch" style={{ background: h.color }} aria-hidden="true" />
            {h.label}
          </span>
        ))}
        <span className="gm-map__legend-item gm-map__legend-item--muted" role="listitem">
          <span className="gm-map__legend-swatch" style={{ background: "var(--map-country)" }} aria-hidden="true" />
          Not in either bloc
        </span>
      </div>

      <div className="gm-map__well">
        <ComposableMap
          projectionConfig={{ scale: 147 }}
          width={MAP_W}
          height={MAP_H}
          role="img"
          aria-label="World map with highlighted countries"
        >
          {/* The graticule sits UNDER the land, so a country fill always wins
              the pixel and the grid only shows in the ocean. */}
          <Graticule stroke="var(--map-grid)" strokeWidth={0.5} />
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
                    className={`gm-map__country${highlight ? " is-highlighted" : ""}`}
                    style={{
                      // A `filter` rather than a second fill color: it works
                      // uniformly on a CSS-variable fill (which cannot be
                      // color-mix()'d from an inline SVG style) and is one
                      // composited property, so hover stays cheap.
                      default: {
                        fill: highlight ? highlight.color : "var(--map-country)",
                        stroke: "var(--map-stroke)",
                        outline: "none",
                      },
                      hover: { outline: "none", filter: "brightness(1.28)", cursor: "default" },
                      pressed: { outline: "none", filter: "brightness(1.1)" },
                    }}
                  >
                    <title>
                      {highlight ? `${geo.properties.name} — ${highlight.label}` : geo.properties.name}
                    </title>
                  </Geography>
                );
              })
            }
          </Geographies>
        </ComposableMap>
      </div>
    </figure>
  );
}
