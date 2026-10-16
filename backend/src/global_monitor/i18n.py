"""Serving-language support for the Global Monitor API.

Eight languages, matching the wider network (Worldora digests all eight; the
Intelligence workspace ships its UI in the same eight codes): en, tr, de, fr,
es, ar, zh, ru. English is the canonical/default - every table below is
keyed by the English string or by a stable id, and a missing entry falls
back to English rather than failing, so adding a language never means
blocking on a complete dictionary.

Only strings the BACKEND owns live here (bloc names/descriptions, metric
names, risk criteria/flags/scenario text, epicentre and country names).
UI chrome - headings, buttons, nav - is translated in the frontend's
`src/i18n/`, where those strings are rendered.

Arabic is the only RTL language; the frontend reads `RTL` from here to set
`dir` and to pick which side of a layout mirrors.
"""
from __future__ import annotations

from .risk import CRITERIA, SCENARIOS

LANGS: tuple[str, ...] = ("en", "tr", "de", "fr", "es", "ar", "zh", "ru")
DEFAULT_LANG = "en"

NATIVE_NAME: dict[str, str] = {
    "en": "English", "tr": "Türkçe", "de": "Deutsch", "fr": "Français",
    "es": "Español", "ar": "العربية", "zh": "中文", "ru": "Русский",
}

RTL_LANGS: frozenset[str] = frozenset({"ar"})


def norm_lang(lang: str | None) -> str:
    """Any unknown/absent code is English - the API never 400s over a lang."""
    code = (lang or "").strip().lower()[:2]
    return code if code in LANGS else DEFAULT_LANG


def is_rtl(lang: str) -> bool:
    return norm_lang(lang) in RTL_LANGS


def synthesis_key(page_key: str, lang: str) -> str:
    """Storage key for a page's synthesis text in a language. English keeps
    the bare page_key (so every pre-existing row stays valid); the other
    seven languages append `|lang`. The API falls back to the bare key when
    a translation has not been generated yet."""
    lang = norm_lang(lang)
    return page_key if lang == DEFAULT_LANG else f"{page_key}|{lang}"


def pick(table: dict[str, str], lang: str, fallback: str | None = None) -> str:
    """Look up `lang`, then English, then `fallback` (usually the raw English
    string itself). Callers pass the English value as the fallback so an
    untranslated string degrades to readable English, never to a blank."""
    lang = norm_lang(lang)
    return table.get(lang) or table.get(DEFAULT_LANG) or (fallback or "")


# --- Blocs -----------------------------------------------------------------
# bloc_id -> lang. Bloc names are proper nouns in most languages but not all
# ("European Union" is AB/EU/UE/UE), and the descriptions are ordinary prose.

BLOC_NAME: dict[str, dict[str, str]] = {
    "brics": {"en": "BRICS+", "tr": "BRICS+", "de": "BRICS+", "fr": "BRICS+",
              "es": "BRICS+", "ar": "بريكس+", "zh": "金砖国家+", "ru": "БРИКС+"},
    "brics5": {
        "en": "BRICS (original five)", "tr": "BRICS (beş kurucu üye)",
        "de": "BRICS (die fünf Gründungsmitglieder)", "fr": "BRICS (les cinq membres fondateurs)",
        "es": "BRICS (los cinco miembros originales)", "ar": "بريكس (الخمسة المؤسسين)",
        "zh": "金砖国家（创始五国）", "ru": "БРИКС (пять стран-учредителей)",
    },
    "eu": {"en": "European Union", "tr": "Avrupa Birliği", "de": "Europäische Union",
           "fr": "Union européenne", "es": "Unión Europea", "ar": "الاتحاد الأوروبي",
           "zh": "欧盟", "ru": "Европейский союз"},
    "us": {"en": "United States", "tr": "Amerika Birleşik Devletleri", "de": "Vereinigte Staaten",
           "fr": "États-Unis", "es": "Estados Unidos", "ar": "الولايات المتحدة",
           "zh": "美国", "ru": "Соединённые Штаты"},
    "usmca": {
        "en": "USMCA (NAFTA)", "tr": "USMCA (NAFTA)", "de": "USMCA (NAFTA)",
        "fr": "ACEUM (ALENA)", "es": "T-MEC (TLCAN)", "ar": "USMCA (NAFTA)",
        "zh": "美墨加协定（北美自由贸易协定）", "ru": "USMCA (НАФТА)",
    },
}

BLOC_DESCRIPTION: dict[str, dict[str, str]] = {
    "brics": {
        "en": "Brazil, Russia, India, China, South Africa, and the 2024-25 expansion members",
        "tr": "Brezilya, Rusya, Hindistan, Çin, Güney Afrika ve 2024-25 genişleme üyeleri",
        "de": "Brasilien, Russland, Indien, China, Südafrika und die Mitglieder der Erweiterung 2024-25",
        "fr": "Brésil, Russie, Inde, Chine, Afrique du Sud et les membres de l'élargissement 2024-25",
        "es": "Brasil, Rusia, India, China, Sudáfrica y los miembros de la ampliación de 2024-25",
        "ar": "البرازيل وروسيا والهند والصين وجنوب أفريقيا وأعضاء التوسع لعامي 2024-2025",
        "zh": "巴西、俄罗斯、印度、中国、南非及2024-25年扩容成员",
        "ru": "Бразилия, Россия, Индия, Китай, Южная Африка и члены расширения 2024-25 гг.",
    },
    "brics5": {
        "en": "The founding five BRICS members, before the 2024-25 expansion",
        "tr": "2024-25 genişlemesinden önceki beş kurucu BRICS üyesi",
        "de": "Die fünf BRICS-Gründungsmitglieder vor der Erweiterung 2024-25",
        "fr": "Les cinq membres fondateurs des BRICS, avant l'élargissement de 2024-25",
        "es": "Los cinco miembros fundadores de los BRICS, antes de la ampliación de 2024-25",
        "ar": "الخمسة المؤسسين لبريكس قبل التوسع لعامي 2024-2025",
        "zh": "2024-25年扩容前的金砖五个创始成员国",
        "ru": "Пять стран-учредителей БРИКС до расширения 2024-25 гг.",
    },
    "eu": {
        "en": "The 27 current EU member states (post-Brexit)",
        "tr": "Brexit sonrası AB'nin mevcut 27 üye devleti",
        "de": "Die derzeitigen 27 EU-Mitgliedstaaten (nach dem Brexit)",
        "fr": "Les 27 États membres actuels de l'UE (après le Brexit)",
        "es": "Los 27 Estados miembros actuales de la UE (tras el Brexit)",
        "ar": "دول الاتحاد الأوروبي السبع والعشرون الحالية (بعد بريكست)",
        "zh": "欧盟现有27个成员国（英国脱欧后）",
        "ru": "Нынешние 27 государств-членов ЕС (после Brexit)",
    },
    "us": {
        "en": "The United States, tracked as a single-country bloc for comparison",
        "tr": "Karşılaştırma için tek ülke bloğu olarak takip edilen Amerika Birleşik Devletleri",
        "de": "Die Vereinigen Staaten, als Ein-Länder-Block für Vergleiche erfasst",
        "fr": "Les États-Unis, suivis comme bloc d'un seul pays pour la comparaison",
        "es": "Estados Unidos, seguido como bloque de un solo país para la comparación",
        "ar": "الولايات المتحدة، وتُتابع ككتلة من دولة واحدة للمقارنة",
        "zh": "美国，作为单一国家集团参与比较",
        "ru": "Соединённые Штаты, учитываемые как блок из одной страны для сравнения",
    },
    "usmca": {
        "en": "United States, Canada, and Mexico under USMCA (formerly NAFTA)",
        "tr": "USMCA (eski adıyla NAFTA) kapsamında ABD, Kanada ve Meksika",
        "de": "USA, Kanada und Mexiko unter dem USMCA (vormals NAFTA)",
        "fr": "États-Unis, Canada et Mexique dans le cadre de l'ACEUM (anciennement ALENA)",
        "es": "Estados Unidos, Canadá y México bajo el T-MEC (antes TLCAN)",
        "ar": "الولايات المتحدة وكندا والمكسيك بموجب اتفاقية USMCA (سابقًا NAFTA)",
        "zh": "美国、加拿大和墨西哥（美墨加协定，前身为北美自由贸易协定）",
        "ru": "США, Канада и Мексика в рамках USMCA (ранее НАФТА)",
    },
}

# --- Metrics ---------------------------------------------------------------
# metric_id -> lang. Only the metrics the frontend actually renders; the rest
# of the catalogue stays English-only and is used in synthesis prompts, which
# are generated in English and then translated as prose.

METRIC_NAME: dict[str, dict[str, str]] = {
    "gdp_current_usd": {
        "en": "GDP (current US$)", "tr": "GSYH (cari ABD doları)", "de": "BIP (aktuelle US-$)",
        "fr": "PIB (US$ actuels)", "es": "PIB (US$ actuales)", "ar": "الناتج المحلي الإجمالي (بالدولار الأمريكي الحالي)",
        "zh": "国内生产总值（现价美元）", "ru": "ВВП (текущие долл. США)",
    },
    "trade_exports_world_usd": {
        "en": "Exports to the world", "tr": "Dünyaya ihracat", "de": "Ausfuhren in die Welt",
        "fr": "Exportations vers le monde", "es": "Exportaciones al mundo", "ar": "الصادرات إلى العالم",
        "zh": "对世界出口", "ru": "Экспорт в мир",
    },
    "trade_imports_world_usd": {
        "en": "Imports from the world", "tr": "Dünyadan ithalat", "de": "Einfuhren aus der Welt",
        "fr": "Importations du monde", "es": "Importaciones del mundo", "ar": "الواردات من العالم",
        "zh": "自世界进口", "ru": "Импорт из мира",
    },
    "trade_pct_gdp": {
        "en": "Trade (% of GDP)", "tr": "Ticaret (GSYH'nin %'si)", "de": "Handel (% des BIP)",
        "fr": "Commerce (% du PIB)", "es": "Comercio (% del PIB)", "ar": "التجارة (من الناتج المحلي الإجمالي)",
        "zh": "贸易（占GDP比重）", "ru": "Торговля (% ВВП)",
    },
    "trade_intra_bloc_exports_usd": {
        "en": "Intra-bloc exports", "tr": "Blok içi ihracat", "de": "Ausfuhr innerhalb des Blocks",
        "fr": "Exportations intra-bloc", "es": "Exportaciones intrabloque", "ar": "الصادرات داخل الكتلة",
        "zh": "集团内部出口", "ru": "Экспорт внутри блока",
    },
    "population_total": {
        "en": "Population", "tr": "Nüfus", "de": "Bevölkerung", "fr": "Population",
        "es": "Población", "ar": "السكان", "zh": "人口", "ru": "Население",
    },
    "life_expectancy_years": {
        "en": "Life expectancy at birth", "tr": "Doğuşta beklenen yaşam süresi", "de": "Lebenserwartung bei Geburt",
        "fr": "Espérance de vie à la naissance", "es": "Esperanza de vida al nacer",
        "ar": "متوسط العمر عند الولادة", "zh": "出生时预期寿命", "ru": "Ожидаемая продолжительность жизни при рождении",
    },
    "secondary_enrollment_pct": {
        "en": "Secondary school enrollment (% gross)", "tr": "Ortaöğretim kayıtı (brüt %)",
        "de": "Sekundar-Einschulungsquote (Brutto-%)", "fr": "Inscription au secondaire (% brut)",
        "es": "Matrícula en secundaria (% bruta)", "ar": "التسجيل في التعليم الثانوي (إجمالي٪)",
        "zh": "中学入学率（毛入学率）", "ru": "Охват средним образованием (валовой %)",
    },
    "hdi": {
        "en": "Human Development Index", "tr": "İnsani Gelişme Endeksi", "de": "Index der menschlichen Entwicklung",
        "fr": "Indice de développement humain", "es": "Índice de Desarrollo Humano",
        "ar": "مؤشر التنمية البشرية", "zh": "人类发展指数", "ru": "Индекс человеческого развития",
    },
    "military_exp_usd": {
        "en": "Military expenditure (current US$)", "tr": "Askeri harcama (cari ABD doları)",
        "de": "Militärausgaben (aktuelle US-$)", "fr": "Dépenses militaires (US$ actuels)",
        "es": "Gasto militar (US$ actuales)", "ar": "الإنفاق العسكري (بالدولار الأمريكي الحالي)",
        "zh": "军费开支（现价美元）", "ru": "Военные расходы (текущие долл. США)",
    },
    "military_exp_pct_gdp": {
        "en": "Military expenditure (% of GDP)", "tr": "Askeri harcama (GSYH'nin %'si)",
        "de": "Militärausgaben (% des BIP)", "fr": "Dépenses militaires (% du PIB)",
        "es": "Gasto militar (% del PIB)", "ar": "الإنفاق العسكري (من الناتج المحلي الإجمالي)",
        "zh": "军费开支（占GDP比重）", "ru": "Военные расходы (% ВВП)",
    },
}

# --- Risk model ------------------------------------------------------------
# The risk payload's prose is entirely owned here. Keys are stable ids/slugs,
# never the English display string, so renaming an English label cannot strand
# the other seven languages.

CRITERION_NAME: dict[str, dict[str, str]] = {
    "economic_resilience": {
        "en": "Economic Resilience", "tr": "Ekonomik Dayanıklılık", "de": "Wirtschaftliche Widerstandsfähigkeit",
        "fr": "Résilience économique", "es": "Resiliencia económica", "ar": "المرونة الاقتصادية",
        "zh": "经济韧性", "ru": "Экономическая устойчивость",
    },
    "domestic_social_stability": {
        "en": "Domestic Social Stability", "tr": "İç Sosyal İstikrar", "de": "Innere soziale Stabilität",
        "fr": "Stabilité sociale interne", "es": "Estabilidad social interna", "ar": "الاستقرار الاجتماعي الداخلي",
        "zh": "国内社会稳定", "ru": "Внутренняя социальная стабильность",
    },
    "infrastructure_health": {
        "en": "Human & Physical Infrastructure", "tr": "İnsani ve Fiziksel Altyapı", "de": "Menschliche und physische Infrastruktur",
        "fr": "Infrastructures humaines et physiques", "es": "Infraestructura humana y física",
        "ar": "البنية التحتية البشرية والمادية", "zh": "人力与基础设施", "ru": "Человеческая и физическая инфраструктура",
    },
    "climate_resilience": {
        "en": "Climate Resilience", "tr": "İklim Dayanıklılığı", "de": "Klimaresilienz",
        "fr": "Résilience climatique", "es": "Resiliencia climática", "ar": "المرونة المناخية",
        "zh": "气候韧性", "ru": "Климатическая устойчивость",
    },
    "energy_independence": {
        "en": "Energy Independence", "tr": "Enerji Bağımsızlığı", "de": "Energieunabhängigkeit",
        "fr": "Indépendance énergétique", "es": "Independencia energética", "ar": "الاستقلالية الطاقية",
        "zh": "能源独立", "ru": "Энергетическая независимость",
    },
    "demographic_resilience": {
        "en": "Demographic Resilience", "tr": "Demografik Dayanıklılık", "de": "Demographische Resilienz",
        "fr": "Résilience démographique", "es": "Resiliencia demográfica", "ar": "المرونة الديموغرافية",
        "zh": "人口结构韧性", "ru": "Демографическая устойчивость",
    },
}

FLAG_LABEL: dict[str, dict[str, str]] = {
    "nuclear_armed": {
        "en": "Nuclear-armed state", "tr": "Nükleer silaha sahip devlet", "de": "Nuklear bewaffneter Staat",
        "fr": "État doté de l'arme nucléaire", "es": "Estado con armas nucleares", "ar": "دولة مسلحة بالأسلحة النووية",
        "zh": "拥核国家", "ru": "Ядерная держава",
    },
    "belligerent": {
        "en": "Party to this scenario", "tr": "Bu senaryonun tarafı", "de": "Partei in diesem Szenario",
        "fr": "Partie à ce scénario", "es": "Parte en este escenario", "ar": "طرف في هذا السيناريو",
        "zh": "本情景的当事方", "ru": "Сторона в этом сценарии",
    },
    "ida_credit": {
        "en": "IDA credit (fragility proxy)", "tr": "IDA kredisi (kırılganlık göstergesi)",
        "de": "IDA-Kredit (Proxy für Fragilität)", "fr": "Crédit IDA (proxy de fragilité)",
        "es": "Crédito IDA (proxy de fragilidad)", "ar": "ائتمان IDA (مؤشر بديل للهشاشة)",
        "zh": "IDA信贷（脆弱性代理指标）", "ru": "Кредит МАР (прокси-показатель уязвимости)",
    },
}

FLAG_BASIS: dict[str, dict[str, str]] = {
    "nuclear_armed": {
        "en": "Curated list of the nine states recognised as nuclear-armed under the NPT, cross-checked against SIPRI military expenditure. Reported only; never part of any score.",
        "tr": "NPT kapsamında nükleer silaha sahip olarak tanınan dokuz devletin elle derlenmiş listesi; SIPRI askeri harcamalarıyla çapraz kontrol edilir. Yalnızca raporlanır; hiçbir skora dâhil edilmez.",
        "de": "Kuratierte Liste der neun Staaten, die unter dem NVvT als nuklear bewaffnet gelten, abgeglichen mit den SIPRI-Militärausgaben. Nur berichtet; nie Teil einer Bewertung.",
        "fr": "Liste établie des neuf États reconnus comme dotés de l'arme nucléaire au titre du TNP, vérifiée avec les dépenses militaires du SIPRI. Uniquement signalé ; jamais intégré à un score.",
        "es": "Lista seleccionada de los nueve Estados reconocidos como armados nuclearmente bajo el TNP, verificada con el gasto militar del SIPRI. Solo se informa; nunca forma parte de ninguna puntuación.",
        "ar": "قائمة مُنسّقة للدول التسع المعترف بها كدول مسلحة بالأسلحة النووية بموجب معاهدة عدم الانتشار، وتم التحقق منها مقابل الإنفاق العسكري لمعهد ستوكهولم الدولي لأبحاث السلام. تُعرض فقط ولا تدخل في أي درجة.",
        "zh": "根据《不扩散核武器条约》被承认拥核的九国名单，与斯德哥尔摩国际和平研究所军费数据交叉核对。仅作报告，绝不计入任何评分。",
        "ru": "Утверждённый список из девяти государств, признанных ядерными по ДНЯП, сверенный с данными SIPRI о военных расходах. Только для отчётности; никогда не входит в оценку.",
    },
    "belligerent": {
        "en": "Per-scenario, hand-declared. Reported only; never part of any score.",
        "tr": "Senaryoya göre elle bildirilir. Yalnızca raporlanır; hiçbir skora dâhil edilmez.",
        "de": "Pro Szenario manuell festgelegt. Nur berichtet; nie Teil einer Bewertung.",
        "fr": "Déclaré à la main, scénario par scénario. Uniquement signalé ; jamais intégré à un score.",
        "es": "Declarado manualmente para cada escenario. Solo se informa; nunca forma parte de ninguna puntuación.",
        "ar": "مُحدّد يدويًا لكل سيناريو. يُعرض فقط ولا يدخل في أي درجة.",
        "zh": "按情景人工声明。仅作报告，绝不计入任何评分。",
        "ru": "Заявлено вручную для каждого сценария. Только для отчётности; никогда не входит в оценку.",
    },
    "ida_credit": {
        "en": "World Bank lending type. This is a poverty-and-creditworthiness signal, NOT a fragility classification: it omits conflict, institutional collapse and displacement, and misses fragile countries that are not IDA-eligible. The authoritative OECD DAC fragile-contexts list is not machine-readable and CPIA is not in the public World Bank API.",
        "tr": "Dünya Bankası kredi türü. Bu bir yoksulluk ve kredi değeri göstergesidir, bir kırılganlık sınıflandırması DEĞİLDİR: çatışma, kurumsal çöküş ve yerinden edilmeyi dışlar; IDA'ya uygun olmayan kırılgan ülkeleri kaçırır. OECD DAC kırılgan bağlam listesi makineyle okunamaz ve CPIA herkese açık Dünya Bankası API'sinde yoktur.",
        "de": "Kreditart der Weltbank. Dies ist ein Signal für Armut und Kreditwürdigkeit, KEINE Fragilitätsklassifikation: sie lässt Konflikt, institutionellen Zusammenbruch und Vertreibung aus und erfasst fragile Länder nicht, die nicht IDA-fähig sind. Die maßgebliche OECD-DAC-Liste fragiler Kontexte ist nicht maschinenlesbar, und CPIA fehlt in der öffentlichen Weltbank-API.",
        "fr": "Type de prêt de la Banque mondiale. Il s'agit d'un signal de pauvreté et de solvabilité, et NON d'une classification de fragilité : il ignore le conflit, l'effondrement institutionnel et le déplacement, et ne détecte pas les pays fragiles non éligibles à l'IDA. La liste OCDE-DAC des contextes fragiles n'est pas lisible par machine et le CPIA n'est pas disponible dans l'API publique de la Banque mondiale.",
        "es": "Tipo de préstamo del Banco Mundial. Es una señal de pobreza y solvencia, NO una clasificación de fragilidad: omite el colapso institucional, los conflictos y los desplazamientos, y no detecta los países frágiles no elegibles para el AID. La lista de contextos frágiles de la OCDE-DAC no es legible por máquina y el CPIA no está en la API pública del Banco Mundial.",
        "ar": "نوع التقديض من البنك الدولي. هذا مؤشر للفقر والائتمان وليس تصنيفًا للهشاشة: فهو يستبعد النزاع والانهيار المؤسسي والنزوح، ولا يرصد الدول الهشة غير المؤهلة لصندوق النقد الدولي. القائمة المرجعية لسياقات الهشاشة لدى لجنة التنمية التابعة لمنظمة التعاون والتنمية ليست قابلة للقراءة الآلية، ومؤشر CPIA غير متوفر واجهات البرمجة العامة للبنك الدولي.",
        "zh": "世界银行的贷款类型。这是贫困与偿付能力信号，并非脆弱性分类：它忽略冲突、制度崩溃与流离失所，也漏掉不具备IDA资格的脆弱国家。经合组织发展援助委员会的脆弱情境权威名单不具机器可读性，CPIA也不在世界银行公开API中。",
        "ru": "Тип кредитования Всемирного банка. Это сигнал бедности и кредитоспособности, а НЕ классификация уязвимости: она не учитывает конфликты, институциональный распад и перемещение населения и пропускает уязвимые страны, не имеющие права на кредиты МАР. Авторитетный список ОЭСР-КРР по уязвимым контекстам не машиночитаем, а CPIA отсутствует в публичном API Всемирного банка.",
    },
}

AXIS_STRUCTURAL: dict[str, str] = {
    "en": "Socio-economic and structural indicators only. Excludes proximity to conflict and nuclear posture, which are reported separately and never combined with it.",
    "tr": "Yalnızca sosyoekonomik ve yapısal göstergeler. Ayrı ayrı raporlanan ve bununla asla birleştirilmeyen çatışmaya yakınlığı ve nükleer duruşu içermez.",
    "de": "Nur sozioökonomische und strukturelle Indikatoren. Schließt Nähe zu Konflikten und nukleare Haltung aus, die separat berichtet werden und nie damit kombiniert werden.",
    "fr": "Uniquement des indicateurs socioéconomiques et structurels. Exclut la proximité des conflits et la posture nucléaire, signalés séparément et jamais combinés avec lui.",
    "es": "Solo indicadores socioeconómicos y estructurales. Excluye la cercanía a conflictos y la postura nuclear, que se informan por separado y nunca se combinan con él.",
    "ar": "مؤشرات اقتصادية اجتماعية وبنيوية فقط. تستبعد قرب النزاعات والموقع النووي، وهما يُعرضان بشكل منفصل ولا يُدمجان أبدًا معه.",
    "zh": "仅含社会经济与结构性指标。不含冲突邻近度与核态势，两者单独报告，绝不与之合并。",
    "ru": "Только социально-экономические и структурные показатели. Исключает близость к конфликтам и ядерный статус, которые сообщаются отдельно и никогда не объединяются с ним.",
}

EXPOSURE_AXIS_NOTE: dict[str, str] = {
    "en": "Distance to the nearest scenario epicentre, in kilometres. Purely geographic - not a prediction of who would be attacked.",
    "tr": "En yakın senaryo odak noktasına olan uzaklık, kilometre cinsinden. Tamamen coğrafi - kimin saldırı altında kalacağına dair bir tahmin değildir.",
    "de": "Entfernung zum nächsten Epizentrum des Szenarios, in Kilometern. Rein geographisch - keine Prognose darüber, wer angegriffen würde.",
    "fr": "Distance à l'épicentre le plus proche du scénario, en kilomètres. Purement géographique - ce n'est pas une prédiction de qui serait attaqué.",
    "es": "Distancia al epicentro más cercano del escenario, en kilómetros. Puramente geográfico; no es una predicción de quién sería atacado.",
    "ar": "المسافة إلى أقرب مركز اشتعال في السيناريو، بالكيلومترات. جغرافية بحتة وليست تنبؤًا بمن سيتعرض للهجوم.",
    "zh": "距情景最近震中的距离（公里）。纯地理指标，并非对谁会遭攻击的预测。",
    "ru": "Расстояние до ближайшего эпицентра сценария в километрах. Чисто географический показатель, а не прогноз того, кто подвергнется атаке.",
}

SCENARIO_NAME: dict[str, dict[str, str]] = {
    "general-balanced-crisis": {
        "en": "General Balanced Crisis", "tr": "Genel Denge Krizi", "de": "Allgemeine ausgewogene Krise",
        "fr": "Crise générale équilibrée", "es": "Crisis general equilibrada", "ar": "أزمة عامة متوازنة",
        "zh": "总体均衡危机", "ru": "Умеренный общий кризис",
    },
    "russia-nato-conflict": {
        "en": "Russia-NATO Conflict", "tr": "Rusya-NATO Çatışması", "de": "Russland-NATO-Konflikt",
        "fr": "Conflit Russie-OTAN", "es": "Conflicto Rusia-OTAN", "ar": "نزاع روسيا-حلف الناتو",
        "zh": "俄罗斯-北约冲突", "ru": "Конфликт Россия — НАТО",
    },
    "china-us-tension": {
        "en": "China-US Tension (Economic Crisis)", "tr": "Çin-ABD Gerilimi (Ekonomik Kriz)", "de": "China-USA-Spannung (Wirtschaftskrise)",
        "fr": "Tensions Chine-États-Unis (crise économique)", "es": "Tensión China-EE. UU. (crisis económica)",
        "ar": "توتر الصين-الولايات المتحدة (أزمة اقتصادية)", "zh": "中美紧张（经济危机）", "ru": "Противостояние Китай — США (экономический кризис)",
    },
    "hormuz-energy-shock": {
        "en": "Strait of Hormuz Crisis (Energy Shock)", "tr": "Hormuz Boğazı Krizi (Enerji Şoku)", "de": "Krise der Straße von Hormus (Energieschock)",
        "fr": "Crise du détroit d'Ormuz (choc énergétique)", "es": "Crisis del estrecho de Ormuz (choque energético)",
        "ar": "أزمة مضيق هرمز (صدمة طاقية)", "zh": "霍尔木兹海峡危机（能源冲击）", "ru": "Кризис Ормузского пролива (энергетический шок)",
    },
    "climate-water-wars": {
        "en": "Climate Crisis & Water Wars", "tr": "İklim Krizi ve Su Savaşları", "de": "Klimakrise und Wasserkriege",
        "fr": "Crise climatique et guerres de l'eau", "es": "Crisis climática y guerras del agua",
        "ar": "الأزمة المناخية وحروب المياه", "zh": "气候危机与水资源战争", "ru": "Климатический кризис и водные войны",
    },
    "tech-energy-revolution": {
        "en": "Technological Energy Revolution", "tr": "Teknolojik Enerji Devrimi", "de": "Technologische Energierevolution",
        "fr": "Révolution technologique de l'énergie", "es": "Revolución tecnológica energética",
        "ar": "الثورة التقنية في الطاقة", "zh": "技术能源革命", "ru": "Технологическая энергетическая революция",
    },
}

SCENARIO_EXPLANATION: dict[str, dict[str, str]] = {
    "general-balanced-crisis": {
        "en": "A baseline in which no single factor dominates: all six structural criteria carry roughly equal weight. Exposure is measured against a generic set of global flashpoints rather than one theatre, so it is rough geographic context, not a prediction for any one region.",
        "tr": "Hiçbir tek faktörün baskın olmadığı bir taban senaryo: altı yapısal kriterin tümü roughly eşit ağırlıktadır. Maruziyet tek bir bölge yerine genel küresel kriz noktalarına göre ölçülür; bu nedenle kaba bir coğrafi bağlamdır, herhangi bir bölge için bir tahmin değildir.",
        "de": "Eine Ausgangslage, in der kein einzelner Faktor dominiert: Alle sechs strukturellen Kriterien tragen etwa gleiches Gewicht. Die Exposition wird gegen einen allgemeinen Satz globaler Brennpunkte gemessen statt gegen ein einzelnes Theater - grober geografischer Kontext, keine Prognose für eine Region.",
        "fr": "Une situation de base dans laquelle aucun facteur unique ne domine : les six critères structurels pèsent à peu près autant. L'exposition est mesurée par rapport à un ensemble générique de points chauds mondiaux plutôt qu'à un seul théâtre : un contexte géographique approximatif, pas une prédiction pour une région.",
        "es": "Una situación base en la que ningún factor domina: los seis criterios estructurales pesan aproximadamente lo mismo. La exposición se mide frente a un conjunto genérico de puntos críticos mundiales en lugar de un solo teatro: es contexto geográfico aproximado, no una predicción para ninguna región.",
        "ar": "وضع أساسي لا يهيمن عليه أي عامل واحد: تتساوى وزن المعايير البنوية الستة تقريبًا. تُقاس التعرض تجاه مجموعة عامة من بؤر التوتر العالمية بدل منطقة واحدة، لذا فهو سياق جغرافي تقريبي وليس تنبؤًا لأي منطقة.",
        "zh": "基准情景：没有任何单一因素占主导，六项结构性指标权重大致相当。暴露度针对一组通用的全球热点而非单一战区衡量，因此只是粗略的地理背景，并非对任何地区的预测。",
        "ru": "Базовый сценарий, в котором не доминирует ни один фактор: все шесть структурных критериев имеют примерно равный вес. Воздействие измеряется относительно обобщённого набора мировых очагов напряжения, а не одного театра - приблизительный географический контекст, а не прогноз для региона.",
    },
    "russia-nato-conflict": {
        "en": "Two separate questions, deliberately not combined into one. The structural score asks how well a country holds together on economic, social, infrastructure, climate, energy and demographic indicators. Exposure asks how far it sits from the Kaliningrad exclave, the Belarus-Russia border, Donetsk, the Suwalki Gap and the Finland-Russia border.",
        "tr": "Bilinçli olarak birleştirilmemiş iki ayrı soru. Yapısal skor, bir ülkenin ekonomik, sosyal, altyapı, iklim, enerji ve demografik göstergelerde ne kadar ayakta kaldığını sorar. Maruziyet ise Kaliningrad exclave'sine, Belarus-Rusya sınırına, Donetsk'e, Suwalki Geçidi'ne ve Finlandiya-Rusya sınırına ne kadar uzak olduğunu sorar.",
        "de": "Zwei getrennte Fragen, bewusst nicht zu einer zusammengefasst. Die strukturelle Bewertung fragt, wie gut ein Land auf wirtschaftlichen, sozialen, infrastrukturellen, klimatischen, energie- und demographischen Indikatoren zusammenhält. Die Exposition fragt, wie weit es von der russischen Exklave Kaliningrad, der Grenze Weißrussland-Russland, Donezk, dem Suwałki-Lücke und der Grenze Finnland-Russland entfernt liegt.",
        "fr": "Deux questions distinctes, volontairement non combinées. Le score structurel demande dans quelle mesure un pays tient bon sur les indicateurs économiques, sociaux, d'infrastructure, climatiques, énergétiques et démographiques. L'exposition demande à quelle distance il se trouve de l'enclave de Kaliningrad, de la frontière Biélorussie-Russie, de Donetsk, du corridor de Suwałki et de la frontière Finlande-Russie.",
        "es": "Dos preguntas separadas, deliberadamente no combinadas. La puntuación estructural pregunta cuánto se mantiene un país en los indicadores económicos, sociales, de infraestructura, climáticos, energéticos y demográficos. La exposición pregunta a qué distancia está del exclave de Kaliningrad, la frontera Bielorrusia-Rusia, Donetsk, el corredor de Suwałki y la frontera Finlandia-Rusia.",
        "ar": "سؤالان منفصلان لا يُدمجان عن عمد. تتساءل الدرجة البنوية عن مدى تماسك الدولة في المؤشرات الاقتصادية والاجتماعية والبنائية والمناخية والطاقي والديموغرافي. أما التعرض فيسألكم عن المسافة إلى منطقة كالينينغراد المنفصلة وحدود بيلاروسيا وروسيا ودونيتسك وممر سوفالكي وحدود فنلندا وروسيا.",
        "zh": "两个独立问题，刻意不合并。结构性评分考察一国在经济、社会、基础设施、气候、能源与人口指标上的稳固程度；暴露度则考察其距加里宁格勒飞地、白俄罗斯-俄罗斯边境、顿涅茨克、苏瓦乌基走廊及芬兰-俄罗斯边境的距离。",
        "ru": "Два отдельных вопроса, сознательно не сводимых к одному. Структурная оценка показывает, насколько страна держится по экономическим, социальным, инфраструктурным, климатическим, энергетическим и демографическим показателям. Воздействие показывает расстояние до Калининградской анклава, границы Беларуси и России, Донецка, Сувалкского коридора и границы Финляндии и России.",
    },
    "china-us-tension": {
        "en": "Economic self-sufficiency and industrial depth dominate, with isolation from the Taiwan/South China Sea theatres mattering but far less than in the Russia-NATO case.",
        "tr": "Ekonomik kendi kendine yeterlilik ve sanayi derinliği belirleyicidir; Tayvan/Güney Çin Denizi bölgelerinden uzaklık önem taşır ama Rusya-NATO vakasına göre çok daha azdır.",
        "de": "Wirtschaftliche Autarkie und industrielle Tiefe dominieren; die Distanz zu den Theatern Taiwan/Südchinesisches Meer spielt eine Rolle, aber weitaus weniger als im Fall Russland-NATO.",
        "fr": "L'autosuffisance économique et la profondeur industrielle dominent ; l'éloignement des théâtres Taïwan/Mer de Chine méridionale compte, mais bien moins que dans le cas Russie-OTAN.",
        "es": "La autosuficiencia económica y la profundidad industrial dominan; el aislamiento de los teatros de Taiwán y el mar Meridional de China importa, pero mucho menos que en el caso Rusia-OTAN.",
        "ar": "تحدد الاكتفاء الاقتصادي والعمق الصناعي المسار، بينما يُعد الانفصال عن مسرحيي تايوان والبحر الصيني الجنوبي مهمًا لكن أقل بكثير من حالة روسيا-الناتو.",
        "zh": "经济自给自足与工业深度占主导，与台海/南海战区的隔离程度有影响，但远不及俄罗斯-北约情景。",
        "ru": "Доминируют экономическая самодостаточность и промышленная глубина; отдалённость от театр Тайвань/Южно-Китайское море имеет значение, но гораздо меньшее, чем в случае Россия — НАТО.",
    },
    "hormuz-energy-shock": {
        "en": "Energy independence dominates the structural score. Exposure is still reported in kilometres, but it is a separate axis rather than something folded into the total: the Gulf states sit closest to Hormuz and are also the most fuel-export-dependent, so a combined number would say the same thing twice.",
        "tr": "Enerji bağımsızlığı yapısal skora hâkimdir. Maruziyet hâlâ kilometre cinsinden raporlanır ancak toplama dâhil edilmez; Körfez devletleri Hormuz'a en yakın olanlardır ve aynı zamanda en çok yakıt ihracatına bağımlıdırlar, bu nedenle birleşik bir rakam aynı şeyi iki kez söylerdi.",
        "de": "Energieunabhängigkeit dominiert die strukturelle Bewertung. Die Exposition wird weiterhin in Kilometern berichtet, ist aber eine eigene Achse und nicht Teil des Gesamtwerts: Die Golfstaaten sitzen am nächsten an Hormus und sind zugleich am stärksten vom Kraftstoffexport abhängig - eine kombinierte Zahl würde dasselbe zweimal aussagen.",
        "fr": "L'indépendance énergétique domine le score structurel. L'exposition reste exprimée en kilomètres, mais constitue un axe distinct et non une composante du total : les États du Golfe sont les plus proches d'Ormuz et aussi les plus dépendants des exportations de combustibles; un chiffre combiné dirait deux fois la même chose.",
        "es": "La independencia energética domina la puntuación estructural. La exposición sigue informándose en kilómetros, pero es un eje separado y no algo que se suma al total: los Estados del Golfe están más cerca de Ormuz y son también los más dependientes de las exportaciones de combustibles; una cifra combinada diría lo mismo dos veces.",
        "ar": "تحدد الاستقلالية الطاقية الدرجة البنوية. يبقى التعرض مُبلَّغًا بالكيلومترات لكنه محور منفصل لا يُدمج في المجموع: الدول الخليجية الأقرب إلى هرمز هي الأكثر اعتمادًا على تصدير الوقود، لذا سيقول الرقم المدمج الشيء نفسه مرتين.",
        "zh": "能源独立主导结构性评分。暴露度仍以公里报告，但作为独立坐标轴而非并入总分：海湾国家距霍尔木兹最近，同时也是燃料出口依赖度最高的，合并计算只会重复表达同一件事。",
        "ru": "Энергетическая независимость доминирует в структурной оценке. Воздействие по-прежнему сообщается в километрах, но является отдельной осью, а не частью итога: государства Залива ближе всего к Ормузу и при этом сильнее всего зависят от экспорта топлива, поэтому совокупное число сказало бы одно и то же дважды.",
    },
    "climate-water-wars": {
        "en": "Climate resilience leads, followed by social stability: water access and per-capita emissions pressure matter more than income.",
        "tr": "İklim dayanıklılığı önde gelir, onu sosyal istikrar izler: suya erişim ve kişi başına emisyon baskısı gelirden daha belirleyicidir.",
        "de": "Klimaresilienz führt an, gefolgt von sozialer Stabilität: Wasserverfügbarkeit und Pro-Kopf-Emissionsdruck wiegen mehr als Einkommen.",
        "fr": "La résilience climatique arrive en tête, suivie de la stabilité sociale : l'accès à l'eau et la pression des émissions par habitant comptent plus que le revenu.",
        "es": "La resiliencia climática encabeza la lista, seguida de la estabilidad social: el acceso al agua y la presión de las emisiones per cápita importan más que la renta.",
        "ar": "تأتي المرونة المناخية في المقدمة يليها الاستقرار الاجتماعي: يهم الوصول إلى المياه وضغط الانبعاثات للفرد أكثر من الدخل.",
        "zh": "气候韧性领先，社会稳定次之：水资源获取与人均排放压力比收入更重要。",
        "ru": "Лидирует климатическая устойчивость, затем социальная стабильность: доступ к водам и давление выбросов на душ населения важнее дохода.",
    },
    "tech-energy-revolution": {
        "en": "Diversified, innovative economies with good digital infrastructure and a young population come out ahead.",
        "tr": "İyi dijital altyapıya ve genç nüfusa sahip çeşitlendirilmiş, yenilikçi ekonomiler öne çıkar.",
        "de": "Diversifizierte, innovative Volkswirtschaften mit guter digitaler Infrastruktur und junger Bevölkerung schneiden am besten ab.",
        "fr": "Les économies diversifiées et innovantes, dotées d'une bonne infrastructure numérique et d'une population jeune, arrivent en tête.",
        "es": "Las economías diversificadas e innovadoras, con buena infraestructura digital y población joven, quedan por delante.",
        "ar": "تتفوق الاقتصادات المتنوعة والابتكارية ذات البنية الرقمية الجيدة والسكان الصغار في السن.",
        "zh": "数字化基础设施良好、人口年轻且多元化创新的经济体表现最佳。",
        "ru": "Лучше всего показывают себя диверсифицированные инновационные экономики с хорошей цифровой инфраструктурой и молодым населением.",
    },
}

SCENARIO_NOT_MEASURED: dict[str, dict[str, str]] = {
    "general-balanced-crisis": {
        "en": "No specific conflict or sector.", "tr": "Belirli bir çatışma veya sektör yok.",
        "de": "Kein bestimmter Konflikt oder Sektor.", "fr": "Aucun conflit ou secteur précis.",
        "es": "Ningún conflicto ni sector concreto.", "ar": "لا نزاع أو قطاع محدد.",
        "zh": "不针对特定冲突或部门。", "ru": "Без привязки к конкретному конфликту или сектору.",
    },
    "russia-nato-conflict": {
        "en": "Nuclear deterrence, alliance alignment, war losses and refugee flows. None are in the source data, so none are hand-scored. Nuclear-armed states and the parties to the conflict are flagged on their own axes, never folded into a score.",
        "tr": "Nükleer caydırıcılık, ittifak safı, savaş kayıpları ve göçmen akışları. Hiçbiri kaynak veride yok, bu yüzden hiçbiri elle puanlanmaz. Nükleer silaha sahip devletler ve çatışmanın tarafları kendi eksenlerinde işaretlenir; hiçbir zaman bir skora dâhil edilmez.",
        "de": "Nukleare Abschreckung, Bündniszugehörigkeit, Kriegsverluste und Flüchtlingsströme. Keines dieser Daten ist in den Quelldaten enthalten, daher wird nichts manuell bewertet. Nuklear bewaffnete Staaten und die Konfliktparteien werden auf eigenen Achsen gekennzeichnet und nie in eine Bewertung einbezogen.",
        "fr": "Dissuasion nucléaire, alignement des alliances, pertes de guerre et flux de réfugiés. Aucune de ces données n'existe dans les sources, rien n'est donc noté à la main. Les États dotés de l'arme nucléaire et les parties au conflit sont signalés sur leurs propres axes et jamais intégrés à un score.",
        "es": "Disuasión nuclear, alineación de alianzas, pérdidas de guerra y flujos de refugiados. Nada de esto está en los datos de origen, por lo que nada se puntúa manualmente. Los Estados con armas nucleares y las partes del conflicto se marcan en sus propios ejes y nunca se suman a una puntuación.",
        "ar": "الردع النووي والتقارب التحالفاتي وخسائر الحرب وتدفقات اللاجئين. لا شيء منها موجود في البيانات المصدرية، لذا لا يُقيَّم أي منها يدويًا. الدول النووية وأطراف النزاع تُعلَّم على محاورها الخاصة ولا تُدمج أبدًا في درجة.",
        "zh": "核威慑、联盟立场、战争损失与难民流。这些均不在源数据中，因此都不人工评分。拥核国家与冲突当事方在各自坐标轴上标注，绝不并入评分。",
        "ru": "Ядерное сдерживание, ориентация в блоках, военные потоки и беженцы. Ничего из этого нет в исходных данных, поэтому ничего не оценивается вручную. Ядерные державы и стороны конфликта отмечаются на собственных осях и никогда не включаются в оценку.",
    },
    "china-us-tension": {
        "en": "Semiconductor supply-chain position and tech decoupling specifically.",
        "tr": "Özellikle yarı iletken tedarik zinciri konumu ve teknolojik ayrışma.",
        "de": "Insbesondere die Position in der Halbleiter-Lieferkette und das technologische Entkoppeln.",
        "fr": "Notamment la position dans la chaîne d'approvisionnement des semi-conducteurs et le découplage technologique.",
        "es": "En concreto, la posición en la cadena de suministro de semiconductores y el desacople tecnológico.",
        "ar": "بشكل خاص موضع سلسلة توريد أشباه الموصلات والانفصال التكنولوجي.",
        "zh": "具体指半导体供应链地位与技术脱钩。",
        "ru": "В частности, положение в цепочке поставок полупроводников и технологический раскол.",
    },
    "hormuz-energy-shock": {
        "en": "Shipping insurance, chokepoint transit volumes, and spare oil capacity.",
        "tr": "Denizcilik sigortası, darboğaz geçiş hacimleri ve fazla petrol kapasitesi.",
        "de": "Schiffsversicherung, Durchgangsvolumen an Engstellen und Reserve-Ölkapazität.",
        "fr": "Assurance maritime, volumes de transit par les points de passage et capacité de pétrole excédentaire.",
        "es": "Seguro marítimo, volúmenes de tránsito por los puntos críticos y capacidad petrolera de reserva.",
        "ar": "تأمين الشحن وحجم العبور في المضائق وسعة النفط الاحتياطية.",
        "zh": "航运保险、咽喉要道通行量与剩余石油产能。",
        "ru": "Страхование судоходства, объёмы транзита через узкие места и резервная нефтедобыча.",
    },
    "climate-water-wars": {
        "en": "Actual freshwater availability per capita (no reliable free API for it).",
        "tr": "Gerçek kişi başına tatlı su erişilebilirliği (bunun için güvenilir ücretsiz bir API yok).",
        "de": "Tatsächliche Süßwasserverfügbarkeit pro Kopf (keine zuverlässige freie API dafür).",
        "fr": "Disponibilité réelle en eau douce par habitant (pas d'API fiable et gratuite).",
        "es": "Disponibilidad real de agua dulce per cápita (no hay una API gratuita fiable).",
        "ar": "التوافر الفعلي للمياه العذبة للفرد (لا توجد واجهة برمجة تطبيقات مجانية موثوقة).",
        "zh": "实际人均淡水资源可用量（无可靠的免费API）。",
        "ru": "Фактическая доступность пресной воды на душ населения (нет надёжного бесплатного API).",
    },
    "tech-energy-revolution": {
        "en": "R&D spend and human capital directly (only proxied via internet use and demographics).",
        "tr": "Ar-Ge harcaması ve insan sermayesi doğrudan (yalnızca internet kullanımı ve demografiyle dolaylı ölçülür).",
        "de": "F&E-Ausgaben und Humankapital direkt (nur über Internetnutzung und Demographie abgebildet).",
        "fr": "Dépenses de R&D et capital humain directement (seulement approchés via l'usage d'Internet et la démographie).",
        "es": "Gasto en I+D y capital humano directamente (solo a través del uso de Internet y la demografía).",
        "ar": "الإنفاق على البحث والتطوير رأس المال البشري مباشرة (يُقاس بالنيابة عبر استخدام الإنترنت والديموغرافيا فقط).",
        "zh": "研发投入与人力资本（仅通过互联网使用与人口结构间接代理）。",
        "ru": "Расходы на НИОКР и человеческий капитал напрямую (только косвенно через интернет и демографию).",
    },
}

# Epicentre labels are keyed by their English label (the tuples in risk.py
# have no id), so renaming one there orphans its seven translations - the
# build would fall back to English rather than fail.
EPICENTRE_LABEL: dict[str, dict[str, str]] = {
    "Kaliningrad exclave": {
        "en": "Kaliningrad exclave", "tr": "Kaliningrad eksklavı", "de": "Russische Exklave Kaliningrad",
        "fr": "Enclave de Kaliningrad", "es": "Exclave de Kaliningrado", "ar": "منطقة كالينينغراد المنفصلة",
        "zh": "加里宁格勒飞地", "ru": "Калининградская анклав",
    },
    "Belarus-Russia border": {
        "en": "Belarus-Russia border", "tr": "Belarus-Rusya sınırı", "de": "Grenze Weißrussland-Russland",
        "fr": "Frontière Biélorussie-Russie", "es": "Frontera Bielorrusia-Rusia", "ar": "حدود بيلاروسيا وروسيا",
        "zh": "白俄罗斯-俄罗斯边境", "ru": "Граница Беларуси и России",
    },
    "Belarus-Ukraine border (Gomel)": {
        "en": "Belarus-Ukraine border (Gomel)", "tr": "Belarus-Ukrayna sınırı (Homel)", "de": "Grenze Weißrussland-Ukraine (Homel)",
        "fr": "Frontière Biélorussie-Ukraine (Gomel)", "es": "Frontera Bielorrusia-Ucrania (Gómel)", "ar": "حدود بيلاروسيا وأوكرانيا (جوميل)",
        "zh": "白俄罗斯-乌克兰边境（戈梅利）", "ru": "Граница Беларуси и Украины (Гомель)",
    },
    "Donetsk / eastern Ukraine front": {
        "en": "Donetsk / eastern Ukraine front", "tr": "Donetsk / doğu Ukrayna cephesi", "de": "Donezk / Frontlinie Ostukraine",
        "fr": "Donetsk / front de l'Est de l'Ukraine", "es": "Donetsk / frente del este de Ucrania", "ar": "دونيتسك / جبهة شرق أوكرانيا",
        "zh": "顿涅茨克/乌克兰东部战线", "ru": "Донецк / восточноукраинский фронт",
    },
    "Suwalki Gap": {
        "en": "Suwalki Gap", "tr": "Suwalki Geçidi", "de": "Suwałki-Lücke", "fr": "Corridor de Suwałki",
        "es": "Corredor de Suwałki", "ar": "ممر سوفالكي", "zh": "苏瓦乌基走廊", "ru": "Сувалкский коридор",
    },
    "Finland-Russia border": {
        "en": "Finland-Russia border", "tr": "Finlandiya-Rusya sınırı", "de": "Grenze Finnland-Russland",
        "fr": "Frontière Finlande-Russie", "es": "Frontera Finlandia-Rusia", "ar": "حدود فنلندا وروسيا",
        "zh": "芬兰-俄罗斯边境", "ru": "Граница Финляндии и России",
    },
    "Strait of Hormuz": {
        "en": "Strait of Hormuz", "tr": "Hormuz Boğazı", "de": "Straße von Hormus", "fr": "Détroit d'Ormuz",
        "es": "Estrecho de Ormuz", "ar": "مضيق هرمز", "zh": "霍尔木兹海峡", "ru": "Ормузский пролив",
    },
    "Taiwan Strait": {
        "en": "Taiwan Strait", "tr": "Tayvan Boğazı", "de": "Taiwan-Straße", "fr": "Détroit de Taïwan",
        "es": "Estrecho de Taiwán", "ar": "مضيق تايوان", "zh": "台湾海峡", "ru": "Тайваньский пролив",
    },
    "Nile basin": {
        "en": "Nile basin", "tr": "Nil Havzası", "de": "Nil-Becken", "fr": "Bassin du Nil",
        "es": "Cuenca del Nilo", "ar": "حوض النيل", "zh": "尼罗河流域", "ru": "Бассейн Нила",
    },
    "Mekong basin": {
        "en": "Mekong basin", "tr": "Mekong Havzası", "de": "Mekong-Becken", "fr": "Bassin du Mékong",
        "es": "Cuenca del Mekong", "ar": "حوض ميكونغ", "zh": "湄公河流域", "ru": "Бассейн Меконга",
    },
    "US Great Lakes": {
        "en": "US Great Lakes", "tr": "ABD Büyük Gölleri", "de": "Große Seen der USA", "fr": "Grands Lacs américains",
        "es": "Grandes Lagos de EE. UU.", "ar": "البحيرات العظمى الأمريكية", "zh": "美国五大湖", "ru": "Большие озёра США",
    },
    "South China Sea": {
        "en": "South China Sea", "tr": "Güney Çin Denizi", "de": "Südchinesisches Meer", "fr": "Mer de Chine méridionale",
        "es": "Mar Meridional de China", "ar": "البحر الصيني الجنوبي", "zh": "南海", "ru": "Южно-Китайское море",
    },
    "Korean peninsula": {
        "en": "Korean peninsula", "tr": "Kore Yarımadası", "de": "Koreanische Halbinsel", "fr": "Péninsule coréenne",
        "es": "Península coreana", "ar": "شبه الجزيرة الكورية", "zh": "朝鲜半岛", "ru": "Корейский полуостров",
    },
    "Tigris-Euphrates": {
        "en": "Tigris-Euphrates", "tr": "Dicle-Fırat", "de": "Tigris-Euphrat", "fr": "Tigre-Euphrate",
        "es": "Tigris-Éufrates", "ar": "دجلة والفرات", "zh": "底格里斯河-幼发拉底河", "ru": "Тигр и Евфрат",
    },
    "Kalahari / Zambezi drought belt": {
        "en": "Kalahari / Zambezi drought belt", "tr": "Kalahari / Zambezi kuraklık kuşağı", "de": "Kalahari-/Sambesi-Trockengürtel",
        "fr": "Ceinture sécheresse Kalahari / Zambèze", "es": "Cinturón de sequía Kalahari / Zambezi", "ar": "حزام الجفاف في كالاهاري/زمبيزي",
        "zh": "卡拉哈里/赞比西干旱带", "ru": "Пояс засух Калахари / Замбези",
    },
    "Silicon Valley": {
        "en": "Silicon Valley", "tr": "Silikon Vadisi", "de": "Silicon Valley", "fr": "Silicon Valley",
        "es": "Silicon Valley", "ar": "وادي السيليكون", "zh": "硅谷", "ru": "Кремниевая долина",
    },
    "Taiwan semiconductor belt": {
        "en": "Taiwan semiconductor belt", "tr": "Tayvan yarı iletken kuşağı", "de": "Halbleitergürtel Taiwan",
        "fr": "Ceinture des semi-conducteurs de Taïwan", "es": "Cinturón de semiconductores de Taiwán", "ar": "حزام أشباه الموصلات في تايوان",
        "zh": "台湾半导体带", "ru": "Полупроводниковый пояс Тайваня",
    },
}


def scenario_name(slug: str, lang: str) -> str:
    return pick(SCENARIO_NAME.get(slug, {}), lang, slug)


def criterion_name(key: str, lang: str) -> str:
    return pick(CRITERION_NAME.get(key, {}), lang, CRITERIA.get(key, {}).get("name", key))


def epicentre_label(label: str, lang: str) -> str:
    return pick(EPICENTRE_LABEL.get(label, {}), lang, label)


def localize_scenario_dict(s: dict, lang: str) -> dict:
    """API-level scenario payload, localized in place (returns a new dict)."""
    lang = norm_lang(lang)
    slug = s["slug"]
    return {
        **s,
        "name": scenario_name(slug, lang),
        "explanation": pick(SCENARIO_EXPLANATION.get(slug, {}), lang, s.get("explanation", "")),
        "not_measured": pick(SCENARIO_NOT_MEASURED.get(slug, {}), lang, s.get("not_measured", "")),
        "epicentres": [{**e, "label": epicentre_label(e.get("label", ""), lang)} for e in s.get("epicentres", [])],
    }


def localize_risk_payload(payload: dict, lang: str) -> dict:
    """Full /api/risk/{slug} payload with every owned string localized."""
    from .i18n_countries import country_name  # lazy: that module imports us

    lang = norm_lang(lang)
    out = dict(payload)
    out["scenario"] = localize_scenario_dict(payload["scenario"], lang)
    out["criteria"] = {k: criterion_name(k, lang) for k in payload.get("criteria", {})}
    out["flags"] = {
        k: {
            **f,
            "label": pick(FLAG_LABEL.get(k, {}), lang, f.get("label", k)),
            "basis": pick(FLAG_BASIS.get(k, {}), lang, f.get("basis", "")),
        }
        for k, f in payload.get("flags", {}).items()
    }
    out["axes"] = {
        **payload.get("axes", {}),
        "structural": pick(AXIS_STRUCTURAL, lang, payload.get("axes", {}).get("structural", "")),
        "exposure": pick(EXPOSURE_AXIS_NOTE, lang, payload.get("axes", {}).get("exposure", "")),
    }

    def _row(c: dict) -> dict:
        english = c.get("name_en") or c.get("name", c.get("iso3", ""))
        return {**c, "name": country_name(c.get("iso3", ""), lang, english), "name_en": english}

    out["ranked"] = [_row(c) for c in payload.get("ranked", [])]
    out["unranked"] = [_row(c) for c in payload.get("unranked", [])]
    return out
