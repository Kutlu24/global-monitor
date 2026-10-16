// Plural-category selection for the few count strings the UI renders
// ("{n} members with data", "{n} countries", ...). Not a full ICU
// implementation - just the rules that matter for OUR eight languages:
//
//  - ru needs three forms (1 участник / 2-4 участника / 5 участников),
//    the classic Slavic 1/2-4/other split driven by both the last digit
//    and the last two digits (11 is "other", not "one").
//  - tr, zh and ar use a single form for every count (Turkish and Chinese
//    have no grammatical plural; Arabic has a plural but not for the
//    small cardinal counts this site renders).
//  - en, de, fr and es split on exactly n === 1.
//
// A count key is written as three entries - `${base}.one`, `.few`, `.other` -
// and tn() picks whichever exists, falling back to `.other` then the bare
// base, so a language that only needs one form just defines that one.
import type { Lang } from "./config";

export type PluralCategory = "one" | "few" | "other";

export function pluralCategory(lang: Lang, n: number): PluralCategory {
  if (lang === "ru") {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) return "one";
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "few";
    return "other";
  }
  if (lang === "tr" || lang === "zh" || lang === "ar") return "other";
  return n === 1 ? "one" : "other";
}
