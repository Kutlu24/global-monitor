// world-atlas's topojson (the standard react-simple-maps data source) keys
// countries by ISO 3166-1 NUMERIC code, not alpha-3 - this maps the ~48
// countries this project actually tracks (blocs.py + major_economies.py)
// from their numeric code to their alpha-3, so WorldMap.tsx can look up
// "does this map feature belong to a highlighted bloc/country" by numeric
// id. Only the tracked countries are listed - everything else on the map
// renders as untracked/neutral regardless, so there's no need for a full
// 249-country table.
export const NUMERIC_TO_ISO3: Record<string, string> = {
  "076": "BRA", "643": "RUS", "356": "IND", "156": "CHN", "710": "ZAF",
  "818": "EGY", "231": "ETH", "364": "IRN", "784": "ARE", "360": "IDN",
  "040": "AUT", "056": "BEL", "100": "BGR", "191": "HRV", "196": "CYP",
  "203": "CZE", "208": "DNK", "233": "EST", "246": "FIN", "250": "FRA",
  "276": "DEU", "300": "GRC", "348": "HUN", "372": "IRL", "380": "ITA",
  "428": "LVA", "440": "LTU", "442": "LUX", "470": "MLT", "528": "NLD",
  "616": "POL", "620": "PRT", "642": "ROU", "703": "SVK", "705": "SVN",
  "724": "ESP", "752": "SWE", "840": "USA", "124": "CAN", "484": "MEX",
  "392": "JPN", "826": "GBR", "410": "KOR", "036": "AUS", "756": "CHE",
  "702": "SGP", "376": "ISR", "578": "NOR",
  // Added for the Global Risk Simulator module's 19 scored countries
  // (see lib/risk.ts) - not part of blocs.py/major_economies.py.
  "554": "NZL", "352": "ISL", "858": "URY", "188": "CRI", "152": "CHL",
  "458": "MYS", "072": "BWA", "032": "ARG",
};
