// Serving languages for the whole network, in switcher order.
//
// The same eight codes are used by Worldora (news digest), Worldora
// Intelligence (analysis) and now Global Monitor, so a reader can move
// between the four sites without the language changing under them. English
// is the default and lives at the URL ROOT (`/`, `/bloc/eu/`, ...) - every
// other language is served under its own prefix (`/tr/bloc/eu/`). That
// keeps every English URL that already exists, is linked from Worldora and
// is in search indexes exactly where it was.
export const LANGS = ["en", "tr", "de", "fr", "es", "ar", "zh", "ru"] as const;
export type Lang = (typeof LANGS)[number];

export const DEFAULT_LANG: Lang = "en";

/** Native names, used as the switcher's own labels - never translated. */
export const NATIVE_NAME: Record<Lang, string> = {
  en: "English",
  tr: "Türkçe",
  de: "Deutsch",
  fr: "Français",
  es: "Español",
  ar: "العربية",
  zh: "中文",
  ru: "Русский",
};

/** Arabic is the only right-to-left language in the set. */
export const RTL_LANGS: ReadonlySet<string> = new Set(["ar"]);

/** BCP-47 locale for Intl date/number formatting, per serving language. */
export const DATE_LOCALE: Record<Lang, string> = {
  en: "en-US",
  tr: "tr-TR",
  de: "de-DE",
  fr: "fr-FR",
  es: "es-ES",
  ar: "ar-EG",
  zh: "zh-CN",
  ru: "ru-RU",
};

export const isLang = (value: string | undefined | null): value is Lang =>
  !!value && (LANGS as readonly string[]).includes(value);

export const isDefaultLang = (lang: string): boolean => lang === DEFAULT_LANG;

export const isRtl = (lang: string): boolean => RTL_LANGS.has(lang);

/** Every language except English - what the `[lang]` route trees generate. */
export const NON_DEFAULT_LANGS: Lang[] = LANGS.filter((l) => l !== DEFAULT_LANG);

/** `/tr` + `/bloc/eu/` -> `/tr/bloc/eu/`; `en` is the unprefixed root. */
export function localizePath(path: string, lang: string): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  const withSlash = clean.endsWith("/") ? clean : `${clean}/`;
  return isDefaultLang(lang) ? withSlash : `/${lang}${withSlash}`;
}

/** The same page in another language - what the switcher links to. */
export function alternatePath(path: string, targetLang: string, currentLang: string): string {
  let rest = path;
  if (!isDefaultLang(currentLang) && rest.startsWith(`/${currentLang}/`)) {
    rest = rest.slice(currentLang.length + 1) || "/";
  } else if (!isDefaultLang(currentLang) && rest === `/${currentLang}`) {
    rest = "/";
  }
  return localizePath(rest, targetLang);
}

/** Pull the language out of a pathname (`/tr/bloc/eu/` -> `tr`). */
export function langFromPath(pathname: string): Lang {
  const segment = pathname.split("/").filter(Boolean)[0];
  return isLang(segment) ? segment : DEFAULT_LANG;
}

/** The page's path with any language prefix stripped. */
export function stripLang(pathname: string): string {
  const segment = pathname.split("/").filter(Boolean)[0];
  if (isLang(segment) && segment !== DEFAULT_LANG) {
    const rest = pathname.slice(segment.length + 1);
    return rest.startsWith("/") ? rest || "/" : `/${rest}`;
  }
  return pathname.endsWith("/") || pathname === "" ? pathname || "/" : `${pathname}/`;
}
