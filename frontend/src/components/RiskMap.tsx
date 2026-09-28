import { ComposableMap, Geographies, Geography, Graticule } from "react-simple-maps";
import { NUMERIC_TO_ISO3 } from "../lib/iso3166Numeric";
import { STATUS_COLORS } from "../lib/colors";
import type { RankedCountry } from "../lib/risk";

// A status-color choropleth (Resilient/Moderate/Vulnerable), not a
// categorical one - this is WorldMap.tsx's sibling for a genuinely
// different color job. WorldMap uses "emphasis" (1-2 identity colors + gray
// context) because bloc identity colors are categorical and this
// palette's all-pairs CVD cap is 3-4 hues. Status colors are a SEPARATE,
// smaller, mode-invariant palette (dataviz skill's references/palette.md)
// designed to be shown together and to never be confused with a
// categorical series - so all three tiers can render on one map at once
// safely, unlike a 4-5-bloc categorical choropleth would be.
//
// That is also why every tier here is mode-invariant and why the fills stay
// hex literals rather than becoming CSS variables: the tier is a STATE, and
// a state must not change meaning when the theme does.

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

const TIER_LABELS = { good: "Resilient", warning: "Moderate", critical: "Vulnerable" } as const;

interface Props {
  countries: RankedCountry[];
}

const MAP_W = 1000;
const MAP_H = 520;

export default function RiskMap({ countries }: Props) {
  const byIso3 = new Map(countries.map((c) => [c.iso3, c]));

  return (
    <figure className="gm-map">
      <div className="gm-map__legend" role="list" aria-label="Map legend">
        {(Object.keys(TIER_LABELS) as (keyof typeof TIER_LABELS)[]).map((tier) => (
          <span className="gm-map__legend-item" role="listitem" key={tier}>
            <span className="gm-map__legend-swatch" style={{ background: STATUS_COLORS[tier] }} aria-hidden="true" />
            {TIER_LABELS[tier]}
          </span>
        ))}
        <span className="gm-map__legend-item gm-map__legend-item--muted" role="listitem">
          <span className="gm-map__legend-swatch" style={{ background: "var(--map-country)" }} aria-hidden="true" />
          Not scored
        </span>
      </div>

      <div className="gm-map__well">
        <ComposableMap
          projectionConfig={{ scale: 147 }}
          width={MAP_W}
          height={MAP_H}
          role="img"
          aria-label="World map colored by resilience tier"
        >
          <Graticule stroke="var(--map-grid)" strokeWidth={0.5} />
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const iso3 = NUMERIC_TO_ISO3[geo.id as string];
                const scored = iso3 ? byIso3.get(iso3) : undefined;
                const fill = scored ? STATUS_COLORS[scored.tier] : "var(--map-country)";
                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    strokeWidth={0.5}
                    className="gm-map__country"
                    style={{
                      default: { fill, stroke: "var(--map-stroke)", outline: "none" },
                      hover: { outline: "none", filter: "brightness(1.24)", cursor: "default" },
                      pressed: { outline: "none", filter: "brightness(1.08)" },
                    }}
                  >
                    <title>
                      {scored
                        ? `${geo.properties.name} — ${scored.tierLabel} (score ${scored.score.toFixed(2)}, rank #${scored.rank})`
                        : geo.properties.name}
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
