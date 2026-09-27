"""SIPRI Military Expenditure Database - NO API, only a yearly-published
Excel file (verified live, 2026-09-27:
https://www.sipri.org/sites/default/files/SIPRI-Milex-data-1949-2025_v1.2.xlsx).
Deliberately fragile-tolerant: SIPRI can rename the file, resize the header,
or rename a country between releases, and this module's whole job is to
never crash the app when that happens - log loudly and let the caller keep
whatever data was already stored (see cli.py/scheduler.py, which never
delete `observations` on a failed re-ingest).

The "Current US$" sheet's `Country` column uses full English names, not
ISO3 - `_SIPRI_NAME_TO_ISO3` is a manual mapping for exactly the countries
this project tracks (confirmed against the real file's actual spellings,
e.g. "Czechia" not "Czech Republic", "Korea, South" not "South Korea").
Values are in millions of current US$ - multiplied by 1e6 here so
`military_exp_usd` is in the same raw-dollar units as `gdp_current_usd`.
"""
from __future__ import annotations

import io
import logging

import httpx
import openpyxl

from ..db import now
from ..models import Observation

logger = logging.getLogger(__name__)

XLSX_URL = "https://www.sipri.org/sites/default/files/SIPRI-Milex-data-1949-2025_v1.2.xlsx"
SHEET_NAME = "Current US$"

_SIPRI_NAME_TO_ISO3 = {
    "Brazil": "BRA", "Russia": "RUS", "India": "IND", "China": "CHN", "South Africa": "ZAF",
    "Egypt": "EGY", "Ethiopia": "ETH", "Iran": "IRN", "United Arab Emirates": "ARE", "Indonesia": "IDN",
    "Austria": "AUT", "Belgium": "BEL", "Bulgaria": "BGR", "Croatia": "HRV", "Cyprus": "CYP",
    "Czechia": "CZE", "Denmark": "DNK", "Estonia": "EST", "Finland": "FIN", "France": "FRA",
    "Germany": "DEU", "Greece": "GRC", "Hungary": "HUN", "Ireland": "IRL", "Italy": "ITA",
    "Latvia": "LVA", "Lithuania": "LTU", "Luxembourg": "LUX", "Malta": "MLT", "Netherlands": "NLD",
    "Poland": "POL", "Portugal": "PRT", "Romania": "ROU", "Slovakia": "SVK", "Slovenia": "SVN",
    "Spain": "ESP", "Sweden": "SWE", "United States of America": "USA", "Canada": "CAN", "Mexico": "MEX",
    "Japan": "JPN", "United Kingdom": "GBR", "Korea, South": "KOR", "Australia": "AUS",
    "Switzerland": "CHE", "Singapore": "SGP", "Israel": "ISR", "Norway": "NOR",
}


def fetch(iso3_list: list[str]) -> list[Observation]:
    wanted_isos = set(iso3_list)
    try:
        resp = httpx.get(XLSX_URL, timeout=60.0, follow_redirects=True)
        resp.raise_for_status()
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), read_only=True, data_only=True)
        ws = wb[SHEET_NAME]
        rows = list(ws.iter_rows(values_only=True))
    except Exception:
        logger.exception("SIPRI ingest failed (download/parse) - keeping last-known-good data")
        return []

    header_row = next((r for r in rows if r and r[0] == "Country"), None)
    if header_row is None:
        logger.error("SIPRI ingest failed - no 'Country' header row found (file structure changed?)")
        return []
    year_columns = [(i, y) for i, y in enumerate(header_row) if isinstance(y, int) and y > 1949]
    year_columns.sort(key=lambda pair: pair[1], reverse=True)

    fetched_at = now()
    observations: list[Observation] = []
    header_idx = rows.index(header_row)
    for row in rows[header_idx + 1:]:
        if not row or not row[0]:
            continue
        iso3 = _SIPRI_NAME_TO_ISO3.get(str(row[0]))
        if iso3 is None or iso3 not in wanted_isos:
            continue
        for col_idx, year in year_columns:
            raw = row[col_idx] if col_idx < len(row) else None
            if isinstance(raw, (int, float)):
                observations.append(Observation(
                    iso3=iso3, metric_id="military_exp_usd", period=str(year),
                    value=float(raw) * 1_000_000, fetched_at=fetched_at,
                ))
                break  # only the most recent numeric year per country
    return observations
