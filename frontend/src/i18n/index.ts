// The single import site for pages and layouts: a bound i18n object for the
// page's language, so frontmatter reads `const { t } = createI18n(lang)`
// instead of threading `lang` through every call.
//
//   import { createI18n } from "../i18n";
//   const { t, rtl, dimensionLabel, metricLabel } = createI18n(lang);
//   t("home.h1")                      -> "Ana sayfa"... in `lang`
//   t("home.badge", { date })         -> {date} interpolated
//   dimensionLabel("military")        -> localized dimension name
//   metricLabel("hdi", spec.label)    -> localized metric name, English fallback
import { isRtl, type Lang } from "./config";
import { t as tRaw } from "./ui";
import { dimensionLabel as dimLabel, metricLabel as metricRaw, metricShortLabel } from "./labels";
import { pluralCategory } from "./plural";

export interface I18n {
  lang: Lang;
  /** True for Arabic - the only RTL language in the set. */
  rtl: boolean;
  t: (key: string, vars?: Record<string, string | number>) => string;
  /** Plural-aware lookup: tries `${base}.${category}` for this language and
   *  count, then falls back to `${base}.other`, then the bare base key.
   *  `{n}` is always interpolated. */
  tn: (base: string, n: number, vars?: Record<string, string | number>) => string;
  dimensionLabel: (dimension: string) => string;
  metricLabel: (metricId: string, fallback?: string) => string;
  metricShortLabel: (metricId: string, fallback?: string) => string;
}

export function createI18n(lang: Lang): I18n {
  const tn = (base: string, n: number, vars?: Record<string, string | number>) => {
    const all = { n, ...vars };
    const category = pluralCategory(lang, n);
    const exact = tRaw(lang, `${base}.${category}`, all);
    if (exact !== `${base}.${category}`) return exact;
    const other = tRaw(lang, `${base}.other`, all);
    if (other !== `${base}.other`) return other;
    return tRaw(lang, base, all);
  };
  return {
    lang,
    rtl: isRtl(lang),
    t: (key, vars) => tRaw(lang, key, vars),
    tn,
    dimensionLabel: (dimension) => dimLabel(lang, dimension),
    metricLabel: (metricId, fallback) => metricRaw(lang, metricId, fallback),
    metricShortLabel: (metricId, fallback) => metricShortLabel(lang, metricId, fallback),
  };
}

export { LANGS, DEFAULT_LANG, NATIVE_NAME, NON_DEFAULT_LANGS, DATE_LOCALE, isLang, isDefaultLang, isRtl, localizePath, alternatePath, langFromPath, stripLang } from "./config";
export type { Lang } from "./config";
