// Fixed categorical bloc colors, validated with the dataviz skill's
// `validate_palette.js` for all-pairs safety (any 2 of these 4 can appear
// side by side - a comparison page, a 2-highlight map - and pass every
// CVD/contrast check in both light and dark mode): {blue, yellow, green,
// magenta} passes ALL CHECKS all-pairs in both modes; every other 4-subset
// of the reference palette's 8 hues that was tried failed at least one
// check in at least one mode (this specific 8-hue palette only clears 3
// slots for all-pairs comparisons generally - {blue, yellow, green,
// magenta} is the one 4-subset found that clears all 4).
//
// brics5 (the historical-5 view) intentionally reuses `brics`'s own color -
// they're the same entity at a different membership snapshot, never shown
// as competing identities on the same page, so they don't need to be
// mutually distinguishable at all.
export const BLOC_COLORS: Record<string, { light: string; dark: string }> = {
  brics: { light: "#2a78d6", dark: "#3987e5" }, // blue
  brics5: { light: "#2a78d6", dark: "#3987e5" }, // same as brics, see above
  eu: { light: "#eda100", dark: "#c98500" }, // yellow
  us: { light: "#008300", dark: "#008300" }, // green (mode-invariant in the reference palette)
  usmca: { light: "#e87ba4", dark: "#d55181" }, // magenta
};

export const NEUTRAL_MAP_FILL = { light: "#e1e0d9", dark: "#2c2c2a" }; // gridline/hairline step - "context" gray for emphasis maps

export function blocColor(blocId: string): { light: string; dark: string } {
  return BLOC_COLORS[blocId] ?? { light: "#52514e", dark: "#c3c2b7" }; // secondary ink as a safe fallback
}
