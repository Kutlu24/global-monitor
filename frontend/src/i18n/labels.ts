// Dimension and metric labels in all eight serving languages.
//
// These are the one class of label that lives in the FRONTEND rather than
// the backend's i18n dictionaries: metric *values* and bloc aggregates come
// from the API already localized, but the metric display names embedded in
// the page structure (tables, nav counts, compare bars) are a rendering
// concern wired through lib/metrics.ts's MetricSpec at build time.
//
// Lookup always falls back to English, and callers may pass a fallback
// (typically the English label already on a MetricSpec) so an unknown
// metric id degrades to its existing English name rather than the raw id.
import type { Lang } from "./config";
import { DEFAULT_LANG } from "./config";

type ByLang = Record<Lang, string>;

export const DIMENSION_LABEL: Record<string, ByLang> = {
  economic: { en: "Economic", tr: "Ekonomik", de: "Wirtschaft", fr: "Économique", es: "Económico", ar: "اقتصادي", zh: "经济", ru: "Экономическое" },
  trade: { en: "Trade", tr: "Ticaret", de: "Handel", fr: "Commerce", es: "Comercio", ar: "تجارة", zh: "贸易", ru: "Торговое" },
  social: { en: "Social", tr: "Sosyal", de: "Sozial", fr: "Social", es: "Social", ar: "اجتماعي", zh: "社会", ru: "Социальное" },
  military: { en: "Military", tr: "Askeri", de: "Militärisch", fr: "Militaire", es: "Militar", ar: "عسكري", zh: "军事", ru: "Военное" },
};

export const METRIC_LABEL: Record<string, ByLang> = {
  gdp_current_usd: { en: "GDP (current US$)", tr: "GSYH (cari ABD doları)", de: "BIP (aktuelle US-$)", fr: "PIB (US$ courants)", es: "PIB (US$ corrientes)", ar: "الناتج المحلي الإجمالي (بالدولار الجاري)", zh: "GDP（现价美元）", ru: "ВВП (текущие цены, долл. США)" },
  trade_exports_world_usd: { en: "Exports to the world", tr: "Dünyaya ihracat", de: "Exporte in die Welt", fr: "Exportations vers le monde", es: "Exportaciones al mundo", ar: "الصادرات إلى العالم", zh: "对世界出口", ru: "Экспорт в мир" },
  trade_imports_world_usd: { en: "Imports from the world", tr: "Dünyadan ithalat", de: "Importe aus der Welt", fr: "Importations du monde", es: "Importaciones del mundo", ar: "الواردات من العالم", zh: "自世界进口", ru: "Импорт из мира" },
  trade_pct_gdp: { en: "Trade (% of GDP)", tr: "Ticaret (% GSYH)", de: "Handel (% des BIP)", fr: "Commerce (% du PIB)", es: "Comercio (% del PIB)", ar: "التجارة (٪ من الناتج)", zh: "贸易（占GDP百分比）", ru: "Торговля (% ВВП)" },
  trade_intra_bloc_exports_usd: { en: "Intra-bloc exports", tr: "Blok içi ihracat", de: "Exporte innerhalb des Blocks", fr: "Exportations intra-bloc", es: "Exportaciones intrabloque", ar: "الصادرات داخل الكتلة", zh: "集团内出口", ru: "Внутриблочный экспорт" },
  population_total: { en: "Population", tr: "Nüfus", de: "Bevölkerung", fr: "Population", es: "Población", ar: "السكان", zh: "人口", ru: "Население" },
  life_expectancy_years: { en: "Life expectancy at birth", tr: "Doğuşta beklenen yaşam süresi", de: "Lebenserwartung bei Geburt", fr: "Espérance de vie à la naissance", es: "Esperanza de vida al nacer", ar: "متوسط العمر عند الولادة", zh: "出生时预期寿命", ru: "Ожидаемая продолжительность жизни при рождении" },
  secondary_enrollment_pct: { en: "Secondary school enrollment (% gross)", tr: "Ortaöğretim kaydı (brüt %)", de: "Sekundar-Einschulungsquote (Brutto-%)", fr: "Inscription au secondaire (% brut)", es: "Matrícula de secundaria (% bruta)", ar: "التسجيل في التعليم الثانوي (٪ إجمالي)", zh: "中学入学率（毛入学率%）", ru: "Охват средним образованием (валовой %)" },
  hdi: { en: "Human Development Index", tr: "İnsani Gelişme Endeksi", de: "Human Development Index", fr: "Indice de développement humain", es: "Índice de desarrollo humano", ar: "مؤشر التنمية البشرية", zh: "人类发展指数", ru: "Индекс человеческого развития" },
  military_exp_usd: { en: "Military expenditure (current US$)", tr: "Askeri harcama (cari ABD doları)", de: "Militärausgaben (aktuelle US-$)", fr: "Dépenses militaires (US$ courants)", es: "Gasto militar (US$ corrientes)", ar: "الإنفاق العسكري (بالدولار الجاري)", zh: "军费（现价美元）", ru: "Военные расходы (текущие цены, долл. США)" },
  military_exp_pct_gdp: { en: "Military expenditure (% of GDP)", tr: "Askeri harcama (% GSYH)", de: "Militärausgaben (% des BIP)", fr: "Dépenses militaires (% du PIB)", es: "Gasto militar (% del PIB)", ar: "الإنفاق العسكري (٪ من الناتج)", zh: "军费（占GDP百分比）", ru: "Военные расходы (% ВВП)" },
};

// Short forms for the headline-per-dimension slots (compare overview,
// homepage stats) where the full "(current US$)" qualifier is noise.
export const METRIC_SHORT_LABEL: Record<string, ByLang> = {
  gdp_current_usd: { en: "GDP", tr: "GSYH", de: "BIP", fr: "PIB", es: "PIB", ar: "الناتج المحلي الإجمالي", zh: "GDP", ru: "ВВП" },
  trade_exports_world_usd: METRIC_LABEL.trade_exports_world_usd,
  population_total: METRIC_LABEL.population_total,
  military_exp_usd: { en: "Military expenditure", tr: "Askeri harcama", de: "Militärausgaben", fr: "Dépenses militaires", es: "Gasto militar", ar: "الإنفاق العسكري", zh: "军费", ru: "Военные расходы" },
};

const pick = (table: Record<string, ByLang>, key: string, lang: Lang): string | undefined =>
  table[key]?.[lang] ?? table[key]?.[DEFAULT_LANG];

export function dimensionLabel(lang: Lang, dimension: string): string {
  return pick(DIMENSION_LABEL, dimension, lang) ?? dimension;
}

export function metricLabel(lang: Lang, metricId: string, fallback?: string): string {
  return pick(METRIC_LABEL, metricId, lang) ?? fallback ?? metricId;
}

export function metricShortLabel(lang: Lang, metricId: string, fallback?: string): string {
  return pick(METRIC_SHORT_LABEL, metricId, lang) ?? metricLabel(lang, metricId, fallback);
}
