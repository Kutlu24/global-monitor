import { useMemo } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  Graticule,
  Marker,
  Sphere,
} from "react-simple-maps";
import { NUMERIC_TO_ISO3 } from "../lib/iso3166Numeric";
import {
  RISK_AXES,
  breakLabels,
  bucketFor,
  fmtKm,
  rampVar,
  type QuintileBreaks,
  type RiskAxis,
  type RiskCountry,
  type RiskEpicentre,
} from "../lib/risk";

// Self-hosted, and at 50m rather than the 110m both this file and
// WorldMap.tsx used to pull from a jsDelivr URL. Two reasons, both measured
// against the actual 211-country risk universe:
//
//   1. Coverage. 110m resolves only 174 countries, so 43 of the 211 - most
//      of them small states and island microstates (Singapore, Malta,
//      Bahrain, Mauritius, the Comoros...) - had no geometry at all and
//      could never be drawn, no matter how much data the backend had. 50m
//      draws 209 of 211. Those 43 were not "low scoring", they were
//      invisible, and a reader would have read the gray as a finding.
//   2. Dependency. The geography used to be fetched from a third-party CDN
//      at runtime, so the one page whose whole point is "211 countries"
//      depended on jsDelivr being up. It is now a same-origin file in
//      public/geo/, cached by the browser like any other static asset.
//
// Cost: 108 KB -> 739 KB raw (~225 KB gzipped, and jsDelivr serves it
// brotli'd anyway). That is a real trade and it was worth measuring rather
// than assuming; see docs/risk-model.md.
const GEO_URL = "/geo/countries-50m.json";

interface Props {
  /** Ranked and unranked alike: unranked countries still have a real
   *  exposure distance, so on the exposure map they must not vanish, and on
   *  the structural map they must read as explicitly "no score" rather than
   *  "lowest". */
  countries: RiskCountry[];
  axis: RiskAxis;
  /** Drawn on the exposure map so the reader can see what "distance" is
   *  distance FROM, instead of taking a bare km figure on trust. Omitted on
   *  the structural map, where it would imply a conflict the axis knows
   *  nothing about. */
  epicentres?: RiskEpicentre[];
  /** Names of dataset countries this map resolution has no geometry for.
   *  Computed at build time by lib/atlas.ts rather than hardcoded, so the
   *  caption stays true if the geometry file is ever swapped. */
  undrawn?: string[];
  /** The four cut points of this axis's five classes, computed at build time
   *  from this scenario's own values (lib/risk.ts's quintileBreaks). Passed
   *  in rather than recomputed per country so the map and the table colour
   *  identically, and so the legend can print the real edges. */
  breaks: QuintileBreaks;
  /** The unit the breaks are in, for the legend labels. */
  unit: string;
  idPrefix: string;
}

const MAP_W = 1000;
const MAP_H = 520;

/**
 * world-atlas omits `id` for the three geometries Natural Earth splits out of
 * their neighbours (Kosovo, Northern Cyprus, Somaliland), so the numeric
 * lookup above returns nothing for them. Kosovo IS in the risk universe
 * (World Bank reports XKX), so without this it would render as unscored
 * while holding a real score. Matched on name because that is the only
 * identifier those geometries carry. Northern Cyprus and Somaliland are
 * deliberately not special-cased: they are not in the 211, and inventing a
 * score for them would be worse than drawing them as untracked.
 */
function iso3For(geo: { id?: string | number; properties: { name: string } }): string | undefined {
  if (geo.id != null) return NUMERIC_TO_ISO3[String(geo.id)];
  if (geo.properties.name === "Kosovo") return "XKX";
  return undefined;
}

/**
 * The value a given axis colours a country by, or null if it has none.
 *
 * Exposure deliberately uses RAW KILOMETRES, not the percentile. The
 * percentile is only defined for ranked countries, so using it here left
 * every one of the 36 unscored countries grey on the exposure map - on the
 * one axis where their distance is perfectly real and perfectly meaningful
 * (Yemen sits 3,737 km from a Kaliningrad scenario). The raw distance has no
 * such gap, and the five equal-count bands make the two scenarios directly
 * comparable without needing a percentile to normalise them.
 */
function axisValue(c: RiskCountry, axis: RiskAxis): number | null {
  return axis === "structural" ? (c.structural_score ?? null) : c.exposure_km;
}

export default function RiskMap({
  countries,
  axis,
  epicentres,
  undrawn = [],
  breaks,
  unit,
  idPrefix,
}: Props) {
  const meta = RISK_AXES[axis];
  const byIso3 = useMemo(() => new Map(countries.map((c) => [c.iso3, c])), [countries]);
  const labels = breakLabels(breaks);

  const legendId = `${idPrefix}-${axis}-legend`;

  return (
    <figure className="gm-map">
      <figcaption className="gm-map__caption">
        <h3 className="gm-map__title">{meta.title}</h3>
        <p className="gm-map__sub">{meta.caption}</p>
      </figcaption>

      <div className="gm-map__legend" id={legendId} role="list" aria-label={`${meta.title} legend`}>
        {labels.map((label, i) => (
          <span className="gm-map__legend-item" role="listitem" key={label}>
            <span
              className="gm-map__legend-swatch"
              style={{ background: rampVar(axis, i + 1) }}
              aria-hidden="true"
            />
            {label}
          </span>
        ))}
        <span className="gm-map__legend-item gm-map__legend-item--muted" role="listitem">
          <span className="gm-map__legend-swatch" style={{ background: "var(--map-country)" }} aria-hidden="true" />
          No score
        </span>
        <span className="gm-map__legend-direction">
          {meta.direction} &middot; bands in {unit}
        </span>
      </div>

      <div className="gm-map__well">
        <ComposableMap
          projectionConfig={{ scale: 147 }}
          width={MAP_W}
          height={MAP_H}
          role="img"
          aria-labelledby={legendId}
        >
          <Sphere stroke="var(--map-grid)" strokeWidth={0.5} fill="var(--map-bg)" />
          <Graticule stroke="var(--map-grid)" strokeWidth={0.5} />
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const iso3 = iso3For(geo as never);
                const c = iso3 ? byIso3.get(iso3) : undefined;
                const value = c ? axisValue(c, axis) : null;
                const fill =
                  c && value !== null
                    ? rampVar(axis, bucketFor(value, breaks, meta.higherIsStronger))
                    : "var(--map-country)";

                // Tooltip has to carry the numbers, because a choropleth
                // cannot: a reader hovering a mid-blue country has no way to
                // know it is 52.4 rather than 61.0. Always spell both axes
                // out, never colour alone, and say which one is unmeasured.
                const tip = !c
                  ? geo.properties.name
                  : [
                      geo.properties.name,
                      c.structural_score !== undefined
                        ? `structural ${c.structural_score.toFixed(1)}`
                        : "structural not scored",
                      `exposure ${fmtKm(c.exposure_km)}`,
                      c.exposure_percentile !== undefined
                        ? `(${c.exposure_percentile.toFixed(0)}th pct)`
                        : "(unranked)",
                      ...(c.nuclear_armed ? ["nuclear-armed"] : []),
                      ...(c.belligerent ? ["party to this scenario"] : []),
                      ...(c.ida_credit ? ["IDA credit"] : []),
                    ].join(" — ");

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    strokeWidth={0.4}
                    className="gm-map__country"
                    style={{
                      default: { fill, stroke: "var(--map-stroke)", outline: "none" },
                      hover: { outline: "none", filter: "brightness(1.2)", cursor: "default" },
                      pressed: { outline: "none", filter: "brightness(1.06)" },
                    }}
                  >
                    <title>{tip}</title>
                  </Geography>
                );
              })
            }
          </Geographies>

          {epicentres?.map(({ lat, lon, label }) => (
            <Marker key={`${lat},${lon},${label}`} coordinates={[lon, lat]}>
              {/* Rotated square, not a circle: a dot reads as a data point
                  of the same kind as the choropleth it sits on, whereas a
                  diamond reads as an annotation about the map rather than a
                  country. Filled so it survives over any ramp step. */}
              <path d="M0,-5L5,0L0,5L-5,0Z" fill="var(--text)" stroke="var(--map-bg)" strokeWidth={1.5}>
                <title>{`${label} — exposure is measured from here`}</title>
              </path>
            </Marker>
          ))}
        </ComposableMap>
      </div>

      {epicentres && (
        <p className="gm-map__footnote">
          <strong>&#9670; {epicentres.length} epicentre{epicentres.length === 1 ? "" : "s"}</strong>{" "}
          &mdash; {epicentres.map((e) => e.label).join(", ")}
        </p>
      )}
      {undrawn.length > 0 && (
        <p className="gm-map__footnote">
          {undrawn.length === 1 ? "1 country is" : `${undrawn.length} countries are`} too small
          for this map resolution to draw ({undrawn.join(", ")}).{" "}
          {undrawn.length === 1 ? "It is" : "They are"} still scored in full in the table below.
        </p>
      )}
    </figure>
  );
}
