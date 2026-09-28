# Global Monitor design system

Everything visual in this site is driven by the custom properties in
`frontend/src/styles/global.css`. This file records the *measured* numbers
behind those properties, so the next person to change a value knows whether
the change is still legal.

The rule the whole system is built on: **colour never carries meaning on its
own.** Every bloc, status tier, and tension value is also labelled in text.
This is not decoration - the bloc palette's EU/USMCA pair sits around 6.7:1
(deuteranopia) and 9.8:1 (protanopia) separation in CIEDE2000, which is
visibly weak for a reader with red-green colour vision deficiency. Colour is
the fast channel; the label is the accurate one.

## How these numbers were checked

- Build: `cd frontend && API_URL=http://<api-host>:7863 npm run build`
  (76 static pages; the API URL is required at build time).
- A runtime audit over the built output covering: WCAG 2.1 contrast (with the
  correct 3:1 vs 4.5:1 threshold per computed font size and weight),
  horizontal overflow, reveal state, island hydration, resolved custom
  properties, and basic a11y (single `h1`, skip link, `lang`, accessible
  button names, `img` alt).
- The audit runs across 13 representative pages x {390, 768, 1440}px x
  {dark, light} = 78 page-renders. All are currently clean.

The worst case for a text colour is always `--overlay`, not `--page`:
`--overlay` is the highest-luminance surface, so it is what sets the floor
for every step in the ramp.

## Surfaces

Four levels, and the rule for which is which:

| level | dark | light | use |
|---|---|---|---|
| `--page` | `#141618` | `#f9f8f7` | the page background |
| `--surface` | `#242628` | `#fefdfd` | cards, table bodies, panels |
| `--raised` | `#2d2f31` | `#ffffff` | things that sit *on* a surface: inputs, chips, inset controls |
| `--overlay` | `#36383a` | `#f0eeec` | chrome only: nav, table headers, dropdowns |

`--surface` is the one with a hard ceiling. It sits at `#242628`, the
lightest cool-neutral that still clears 3:1 for `us` (`#008300`) and
`critical` (`#d03b3b`) - the two darkest marks in the set, and therefore the
ones that bound how far a panel can be lightened. `--raised` and `--overlay`
carry no data marks, so they are free to go higher.

`--overlay` is the one that gets misused. It is the lightest surface in the
dark set, so a bar or dot drawn on it loses the contrast that made it
readable on `--raised`. It is a navigation colour, not a place to put a
data mark.

Dark mode is the default and deliberately **not** pure black: `--page` is
`#141618`, a cool near-black, so elevation reads as a shift in lightness
rather than as a glowing panel on a void.

These four values were lifted ~25% perceptual from the first pass of this
design system, because panels were reading as too dark to work in. The
binding constraint was measured rather than assumed: a CDP pass over the
built site, walking up from every element painted in a bloc/status/tension
hex to its nearest non-transparent ancestor background, found marks on
exactly `--page`, `--surface` and `--map-bg` - and on nothing else. The
`--raised` lightness pin an earlier revision carried is therefore gone; it
was protecting a surface nothing painted on.

## Text ramp - dark

| token | --page | --surface | --raised | --overlay | worst | AA 4.5:1 |
|---|---|---|---|---|---|---|
| `--text` | 15.63 | 13.09 | 11.58 | 10.15 | **10.15** | yes |
| `--text-secondary` | 10.19 | 8.53 | 7.55 | 6.61 | **6.61** | yes |
| `--text-dim` | 8.34 | 6.99 | 6.18 | 5.42 | **5.42** | yes |
| `--text-muted` | 6.94 | 5.81 | 5.14 | 4.50 | **4.50** | yes |
| `--text-faint` | 4.65 | 3.89 | 3.44 | 3.02 | **3.02** | NO |

## Text ramp - light

| token | --page | --surface | --raised | --overlay | worst | AA 4.5:1 |
|---|---|---|---|---|---|---|
| `--text` | 17.66 | 18.45 | 18.73 | 16.19 | **16.19** | yes |
| `--text-secondary` | 8.00 | 8.36 | 8.49 | 7.34 | **7.34** | yes |
| `--text-dim` | 6.34 | 6.62 | 6.72 | 5.81 | **5.81** | yes |
| `--text-muted` | 5.06 | 5.28 | 5.36 | 4.63 | **4.63** | yes |
| `--text-faint` | 3.41 | 3.56 | 3.62 | 3.12 | **3.12** | NO |

### `--text-faint` is decoration-only

`--text-faint` measures 3.02:1 on
`--overlay` in dark mode - below the 4.5:1 AA floor for body text. It is for
hairlines, tick marks, and dividers. **Do not set a character in it.**

An earlier revision annotated it "decorative only" and then used it for six
pieces of real text anyway (risk-rank numerals, tension-gauge end labels, the
sidebar counts and headings, and the link arrow), and the audit caught 4.35:1
on two of them.

## Accent

`--accent` does two jobs at once, which is why its value is constrained from
both directions:

1. as **link text** on the lightest surface, and
2. as a **button fill** under `--accent-ink`.

| mode | `--accent` | `--accent-ink` | as link (worst) | ink on fill |
|---|---|---|---|---|
| dark | `#4a9cf1` | `#0b0f14` | 4.10 | 6.70 |
| light | `#2668bd` | `#ffffff` | 4.78 | 5.53 |

Buttons must use `var(--accent-ink)`, never a literal `#fff`. The dark
`--accent` is a *light* blue, so white text on it measures
2.87:1, while the token measures
6.70:1.

The light `--accent` was darkened from `#2a78d6` to `#2668bd` - the
smallest change that clears both jobs (the old value managed
3.82:1 as a link and
4.42:1 under white).

## Categorical: blocs

From `frontend/src/lib/colors.ts`.

| bloc | light | dark | note |
|---|---|---|---|
| BRICS / BRICS+ | `#2a78d6` | `#3987e5` | |
| BRICS (original 5) | `#2a78d6` | `#3987e5` | same entity; deliberately reuses BRICS' colour |
| EU | `#eda100` | `#c98500` | |
| US | `#008300` | `#008300` | mode-invariant |
| USMCA | `#e87ba4` | `#d55181` | |

`#2a78d6, #eda100, #008300, #e87ba4` is the
only 4-subset of the reference palette that passes every all-pairs
CVD/contrast check in both modes. Any comparison page can put any two of them
side by side, so all-pairs is the binding constraint, not adjacent-pairs.

Use them through the CSS custom properties (`var(--bloc-eu)`), never by
resolving a hex in JS. Resolving `blocColor(id).dark` in a component freezes
the dark value at build time and the fill then ignores the active theme -
which is what `MetricCompareBars.tsx` used to do while its own comment
claimed the fills were theme-aware.

## Status tiers (Risk module)

`#0ca30c` (Resilient), `#fab219` (Moderate), `#d03b3b` (Vulnerable) -
mode-invariant, and deliberately distinct from every bloc colour so a status
never impersonates an identity. This is a *state* encoding, so all three
tiers can share one map safely, unlike a 4-5 colour categorical choropleth.

Always spelled out beside the dot.

## Diverging (Tension module)

| pole | dark | light |
|---|---|---|
| cooperation | `#3987e5` | `#2a78d6` |
| conflict | `#e66767` | `#e34948` |
| zero | `--raised` (neutral) | `--raised` (neutral) |

Goldstein is genuinely bipolar (-10 conflictual .. +10 cooperative), so this
is a diverging scale with a meaningful midpoint, not a sequential one. Two
rules the gauge follows:

- the **midpoint is neutral grey, never white** - zero must read as "nothing
  happening", not as a bright third category;
- the **poles are the brightest thing in the component** - on a dark surface
  the extremes have to be the brightest or they disappear.

The track is a two-sided wash made by `color-mix()`-ing each pole toward
`--raised`, so the track and the bar drawn on it can never disagree.

`TensionGauge.astro` and the inline `Gauge` in `CountryTensionQuery.tsx` emit
the same class names on purpose, and the styling lives once in `global.css`
(section 9b). The React copy sits behind a runtime fetch, so island-local
styles would arrive late and make the gauge visibly restyle itself on mount.

## Map

| token | dark | light | role |
|---|---|---|---|
| `--map-bg` | `#0f1113` | `#ffffff` | the recessed well the map sits in |
| `--map-country` | `#3a4049` | `#d0d4d9` | non-highlighted countries (context) |
| `--map-grid` | `#1f242b` | `#eceef0` | graticule |
| `--map-stroke` | `#0f1113` | `#ffffff` | inter-country seam |

The map is drawn into a bordered well with a soft vignette so the SVG's
rectangular bounding box does not read as a hard crop, and a 0.5px graticule
carries the projection. `vector-effect: non-scaling-stroke` keeps the seam
hairline-thin at any scale.

`WorldMap.tsx` and `RiskMap.tsx` are siblings with genuinely different jobs.
`WorldMap` is an *emphasis* map (1-2 identity colours over grey context,
because the categorical palette's all-pairs cap is 3-4 hues); `RiskMap` is a
*status* choropleth. That is why the bloc palette cannot simply be extended
into a 5-colour categorical map.

There is deliberately no `NEUTRAL_MAP_FILL` constant. It used to mirror
`--hairline` in `colors.ts` and drifted out of agreement with
`--map-country`; one custom property, one source of truth.

## Type

`Inter Variable` for UI and text, `JetBrains Mono Variable` for every number.
Both self-hosted via `@fontsource-variable/*` and preloaded. Numbers use
`font-variant-numeric: tabular-nums` so columns of figures align.

`@fontsource-variable/ibm-plex-mono` was the first choice and is not
installable (404 from the registry); JetBrains Mono is the substitute.

## Motion

- Scroll reveal is gated behind `html.gm-motion`, added by an inline `<head>`
  script **only** when `prefers-reduced-motion` reports no preference. The CSS
  selectors are `.gm-motion [data-reveal]`, not a bare `.gm-reveal` class: a
  bare class would hide content by default and depend on the observer to
  reveal it, which is a content-availability bug on an SEO-first site.
- A 2.5s backstop reveals everything unconditionally, so a broken observer
  can cost the animation but never the content.
- `prefers-reduced-motion: reduce` also neutralises the live-dot pulse and
  smooth scrolling.

## Layout rules

- `.gm-table-wrap` gives wide data tables their own horizontal scroll
  container. A 7-column table cannot shrink to 390px, and a table that
  overflows its parent makes the **whole page** scroll sideways, detaching the
  fixed sidebar from the left edge. No `min-width` is set, so a 2-column table
  still fits on a phone and only genuinely wide tables scroll.
- `.gm-hero::before` is a decorative absolutely-positioned wash. An absolutely
  positioned child **does** contribute to its ancestor's `scrollWidth`, so the
  hero carries `overflow-x: clip` as a guard. Its absence was a real 157px
  horizontal-scroll bug that only appeared on the homepage.
- The radius scale is `xs / sm / lg / xl / full` - there is no `md`, because
  `--radius-lg` *is* the default.

## Known issues

- `tsc --noEmit` reports three pre-existing errors (`Cannot find name
  'process'` in `src/lib/data.ts`, `sitemap.ts`, and `tension.ts`).
  `@types/node` is not a declared dependency. This predates the design system
  and is unrelated to it; the project's only gate is `npm run build`, which
  passes.
- There is no theme toggle. The theme is `data-theme` on `<html>` and nothing
  currently writes it, so light mode is reachable only by setting the
  attribute by hand. The light palette is fully built and audited, but not
  reachable through the UI.
