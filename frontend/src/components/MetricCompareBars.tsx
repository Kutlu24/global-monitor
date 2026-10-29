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
//
// Styling deliberately lives in global.css, not in a <style> block here:
// this is a `client:visible` island, so component-scoped styles would only
// arrive at hydration and the whole chart would flash unstyled on scroll.

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

const CHART_HEIGHT = 96;
const BAR_WIDTH = 20;
const BAR_GAP = 12;
// Headroom ABOVE the tallest possible bar for its value label - without
// this, the winning bar (height === CHART_HEIGHT, top === baseline) puts
// its label at a negative y, clipped off the top of the SVG entirely
// (confirmed live: the larger of any two values silently lost its label).
const LABEL_SPACE = 20;
const BASELINE = LABEL_SPACE + CHART_HEIGHT;
const SVG_HEIGHT = BASELINE;
const TILE_WIDTH = BAR_WIDTH * 2 + BAR_GAP;

// A tile with a negative value gets a zero line: positive bars grow up from it,
// negative ones hang down, and the label sits at the data end of each. A tile
// of positive values keeps the zero line at the bottom, exactly as before.
function Bar({ value, zeroY, scale, color, label }: { value: number; zeroY: number; scale: number; color: string; label: string }) {
  const height = Math.max(2, Math.abs(value) * scale);
  const r = Math.min(4, height); // 4px rounded data-end, square at the zero line (skill spec)
  const w = BAR_WIDTH;
  const up = value >= 0;
  const end = up ? zeroY - height : zeroY + height;
  // Rounded data-end corners only - a plain <rect rx> would round all four.
  const path = up
    ? `M0,${zeroY} L0,${end + r} A${r},${r} 0 0 1 ${r},${end} L${w - r},${end} A${r},${r} 0 0 1 ${w},${end + r} L${w},${zeroY} Z`
    : `M0,${zeroY} L0,${end - r} A${r},${r} 0 0 0 ${r},${end} L${w - r},${end} A${r},${r} 0 0 0 ${w},${end - r} L${w},${zeroY} Z`;
  return (
    <g>
      <text x={w / 2} y={up ? end - 7 : end + 14} textAnchor="middle" className="gm-bar-value">
        {label}
      </text>
      <path d={path} fill={color} />
    </g>
  );
}

function Missing({ baseline }: { baseline: number }) {
  // "N/A" is a different KIND of absence from a short bar, so it is set in
  // the faint text token at regular weight rather than being drawn as a
  // stub - a 2px stub would read as "a very small number".
  return (
    <text x={BAR_WIDTH / 2} y={baseline - 7} textAnchor="middle" className="gm-bar-value gm-bar-value--na">
      N/A
    </text>
  );
}

export default function MetricCompareBars({ a, b, metrics }: Props) {
  // Reference the theme's bloc custom properties directly rather than
  // resolving a hex in JS. The comment on this block used to claim the fills
  // "follow the active theme" while assigning blocColor(...).dark, which is
  // the dark-mode hex frozen at build time - so on a light-theme load the
  // bars stayed dark. Reading the var defers the light/dark decision to the
  // cascade, which is the only place that knows the mode.
  const colorA = `var(--bloc-${a.id})`;
  const colorB = `var(--bloc-${b.id})`;

  return (
    <div
      className="gm-compare-bars"
      style={{ "--color-a": colorA, "--color-b": colorB } as React.CSSProperties}
    >
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
          // Per-tile scale: the taller of the two values is always full
          // height. Each tile is its own scale, which is the entire point of
          // small multiples - so a tile can be read within itself and never
          // against a neighbouring tile's geometry.
          const hi = Math.max(0, va ?? 0, vb ?? 0);
          const lo = Math.min(0, va ?? 0, vb ?? 0);
          const span = hi - lo;
          const scale = span > 0 ? CHART_HEIGHT / span : 0;
          const hasNegative = lo < 0;
          const zeroY = LABEL_SPACE + hi * scale;
          const svgHeight = hasNegative ? SVG_HEIGHT + LABEL_SPACE : SVG_HEIGHT;
          const format = FORMATTERS[m.formatType];
          return (
            <div className="gm-metric-tile" key={m.metric_id}>
              <div className="gm-metric-label">{m.label}</div>
              <div className="gm-metric-bars">
                <svg
                  width={BAR_WIDTH}
                  height={svgHeight}
                  role="img"
                  aria-label={`${m.label}: ${a.name} ${va != null ? format(va) : "no data"}`}
                >
                  {va != null ? (
                    <Bar value={va} zeroY={zeroY} scale={scale} color="var(--color-a)" label={format(va)} />
                  ) : (
                    <Missing baseline={hasNegative ? zeroY : BASELINE} />
                  )}
                  {hasNegative && <line x1={-BAR_GAP / 2} x2={BAR_WIDTH + BAR_GAP / 2} y1={zeroY} y2={zeroY} className="gm-zero-line" />}
                </svg>
                <svg
                  width={BAR_WIDTH}
                  height={svgHeight}
                  role="img"
                  aria-label={`${m.label}: ${b.name} ${vb != null ? format(vb) : "no data"}`}
                >
                  {vb != null ? (
                    <Bar value={vb} zeroY={zeroY} scale={scale} color="var(--color-b)" label={format(vb)} />
                  ) : (
                    <Missing baseline={hasNegative ? zeroY : BASELINE} />
                  )}
                  {hasNegative && <line x1={-BAR_GAP / 2} x2={BAR_WIDTH + BAR_GAP / 2} y1={zeroY} y2={zeroY} className="gm-zero-line" />}
                </svg>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
