import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { NUMERIC_TO_ISO3 } from "../lib/iso3166Numeric";
import { NEUTRAL_MAP_FILL, STATUS_COLORS } from "../lib/colors";
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

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

const TIER_LABELS = { good: "Resilient", warning: "Moderate", critical: "Vulnerable" } as const;

interface Props {
  countries: RankedCountry[];
}

export default function RiskMap({ countries }: Props) {
  const byIso3 = new Map(countries.map((c) => [c.iso3, c]));

  return (
    <div className="gm-world-map">
      <style>{`
        .gm-world-map { --gm-neutral: ${NEUTRAL_MAP_FILL.dark}; --gm-stroke: #1e1e1e; }
        :root[data-theme="light"] .gm-world-map { --gm-neutral: ${NEUTRAL_MAP_FILL.light}; --gm-stroke: #fcfcfb; }
        .gm-legend { display: flex; gap: 1.5rem; margin-bottom: 0.75rem; font-size: 0.9rem; flex-wrap: wrap; }
        .gm-legend-item { display: flex; align-items: center; gap: 0.4rem; }
        .gm-legend-swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
      `}</style>
      <div className="gm-legend" role="list" aria-label="Map legend">
        {(Object.keys(TIER_LABELS) as (keyof typeof TIER_LABELS)[]).map((tier) => (
          <span className="gm-legend-item" role="listitem" key={tier}>
            <span className="gm-legend-swatch" style={{ background: STATUS_COLORS[tier] }} />
            {TIER_LABELS[tier]}
          </span>
        ))}
        <span className="gm-legend-item" role="listitem">
          <span className="gm-legend-swatch" style={{ background: "var(--gm-neutral)" }} />
          Not scored
        </span>
      </div>
      <ComposableMap projectionConfig={{ scale: 140 }} width={800} height={420} role="img" aria-label="World map colored by resilience tier">
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo) => {
              const iso3 = NUMERIC_TO_ISO3[geo.id as string];
              const scored = iso3 ? byIso3.get(iso3) : undefined;
              const fill = scored ? STATUS_COLORS[scored.tier] : "var(--gm-neutral)";
              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  strokeWidth={0.5}
                  style={{
                    default: { fill, stroke: "var(--gm-stroke)", outline: "none" },
                    hover: { fill, stroke: "var(--gm-stroke)", outline: "none", opacity: scored ? 0.85 : 1 },
                    pressed: { fill, stroke: "var(--gm-stroke)", outline: "none" },
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
  );
}
