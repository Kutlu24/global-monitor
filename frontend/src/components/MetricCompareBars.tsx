import { blocColor } from "../lib/colors";
import { FORMATTERS, type FormatType } from "../lib/metrics";

// Small multiples of simple 2-bar grouped columns - one per metric, each
// with its OWN scale. Deliberately NOT a single radar/spider chart: radar
// axes force incompatible units (USD, %, years, an index) onto one shared
// 0-1 scale, which has the same "arbitrary alignment invents a
// correlation" flaw the dataviz skill explicitly bans for dual-axis
// charts, just generalized to N axes. Small multiples keep every metric's
// real scale intact and let the reader compare like-for-like within each
// tile - see the project's own dataviz-skill consultation notes.
//
// Plain SVG, no charting library - a 2-bar column is simple enough to hit
// the skill's exact mark spec (<=24px bars, 4px rounded data-end, square
// baseline) by hand, and it keeps this component's JS payload near zero,
// which matters more here than usual since this ships as a hydrated
// Astro island on an SEO-priority site.

// Deliberately just {metric_id, label, formatType} - all plain strings, all
// JSON-serializable. lib/metrics.ts's own MetricSpec also carries a real
// `format` function for use in .astro frontmatter (build-time only); a
// MetricSpec[] is still assignable here (structurally a superset), but
// this component only ever reads the serializable fields and resolves
// formatting itself via FORMATTERS[formatType] (see the import above).
// History: passing `format` itself across the island boundary throws
// "TypeError: a.format is not a function" at hydration time, since Astro
// JSON-serializes island props and functions don't survive that trip.
export interface IslandMetricSpec {
  metric_id: string;
  label: string;
  formatType: FormatType;
}

export interface CompareEntity {
  id: string;
  name: string;
  values: Record<string, number | null | undefined>;
}

interface Props {
  a: CompareEntity;
  b: CompareEntity;
  metrics: IslandMetricSpec[];
}

const CHART_HEIGHT = 110;
const BAR_WIDTH = 22;
const BAR_GAP = 10;
// Headroom ABOVE the tallest possible bar for its value label - without
// this, the winning bar (height === CHART_HEIGHT, top === baseline) puts
// its label at a negative y, clipped off the top of the SVG entirely
// (confirmed live: the larger of any two values silently lost its label).
const LABEL_SPACE = 18;
const BASELINE = LABEL_SPACE + CHART_HEIGHT;
const SVG_HEIGHT = BASELINE;

function Bar({ value, max, color, label }: { value: number; max: number; color: string; label: string }) {
  const height = max > 0 ? Math.max(2, (value / max) * CHART_HEIGHT) : 0;
  const top = BASELINE - height;
  const r = Math.min(4, height); // 4px rounded data-end, square at the baseline (skill spec)
  const w = BAR_WIDTH;
  // Rounded top corners only - a plain <rect rx> would round all four.
  const path = `M0,${BASELINE} L0,${top + r} A${r},${r} 0 0 1 ${r},${top} L${w - r},${top} A${r},${r} 0 0 1 ${w},${top + r} L${w},${BASELINE} Z`;
  return (
    <g>
      <text x={w / 2} y={top - 6} textAnchor="middle" fontSize="11" className="gm-bar-value">
        {label}
      </text>
      <path d={path} fill={color} />
    </g>
  );
}

export default function MetricCompareBars({ a, b, metrics }: Props) {
  const colorA = blocColor(a.id);
  const colorB = blocColor(b.id);

  return (
    <div className="gm-compare-bars">
      <style>{`
        .gm-compare-bars {
          --color-a-light: ${colorA.light}; --color-a-dark: ${colorA.dark};
          --color-b-light: ${colorB.light}; --color-b-dark: ${colorB.dark};
          --color-a: var(--color-a-dark); --color-b: var(--color-b-dark);
        }
        :root[data-theme="light"] .gm-compare-bars { --color-a: var(--color-a-light); --color-b: var(--color-b-light); }
        .gm-legend { display: flex; gap: 1.5rem; margin-bottom: 1rem; font-size: 0.9rem; }
        .gm-legend-item { display: flex; align-items: center; gap: 0.4rem; }
        .gm-legend-swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
        .gm-metric-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 1.5rem; }
        .gm-metric-tile { text-align: center; }
        .gm-metric-label { font-size: 0.85rem; margin-bottom: 0.5rem; }
        .gm-bar-value { fill: currentColor; }
        /* Value labels are wider than the bars they sit above (the SVG's
           own width is sized to just the bars, for centering) - without
           this an SVG's default overflow:hidden clips both ends of every
           label (confirmed live: "$460.6B" rendered as "160.6B", "$30.77T"
           as "$30.77"). The surrounding .gm-metric-tile grid column
           (minmax(140px, 1fr)) has ample spare width for the label to
           spill into, so this is visually safe, not just a clip disabled. */
        .gm-compare-bars svg { overflow: visible; }
      `}</style>
      <div className="gm-legend" role="list" aria-label="Series">
        <span className="gm-legend-item" role="listitem">
          <span className="gm-legend-swatch" style={{ background: "var(--color-a)" }} />
          {a.name}
        </span>
        <span className="gm-legend-item" role="listitem">
          <span className="gm-legend-swatch" style={{ background: "var(--color-b)" }} />
          {b.name}
        </span>
      </div>
      <div className="gm-metric-grid">
        {metrics.map((m) => {
          const va = a.values[m.metric_id];
          const vb = b.values[m.metric_id];
          if (va == null && vb == null) return null;
          const max = Math.max(va ?? 0, vb ?? 0);
          const width = BAR_WIDTH * 2 + BAR_GAP;
          const format = FORMATTERS[m.formatType];
          return (
            <div className="gm-metric-tile" key={m.metric_id}>
              <div className="gm-metric-label">{m.label}</div>
              <svg
                width={width}
                height={SVG_HEIGHT}
                role="img"
                aria-label={`${m.label}: ${a.name} ${va != null ? format(va) : "no data"}, ${b.name} ${vb != null ? format(vb) : "no data"}`}
              >
                <g transform="translate(0, 0)">
                  {va != null ? (
                    <Bar value={va} max={max} color="var(--color-a)" label={format(va)} />
                  ) : (
                    <text x={BAR_WIDTH / 2} y={BASELINE - 6} textAnchor="middle" fontSize="10" className="gm-bar-value">
                      N/A
                    </text>
                  )}
                </g>
                <g transform={`translate(${BAR_WIDTH + BAR_GAP}, 0)`}>
                  {vb != null ? (
                    <Bar value={vb} max={max} color="var(--color-b)" label={format(vb)} />
                  ) : (
                    <text x={BAR_WIDTH / 2} y={BASELINE - 6} textAnchor="middle" fontSize="10" className="gm-bar-value">
                      N/A
                    </text>
                  )}
                </g>
              </svg>
            </div>
          );
        })}
      </div>
    </div>
  );
}
