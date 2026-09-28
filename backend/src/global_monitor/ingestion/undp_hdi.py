"""UNDP Human Development Index - no API (their documented "Data API 2.0"
needs a manually-approved key with no self-serve signup as of this
writing), so this downloads UNDP's own published composite-indices CSV
directly (verified live, 2026-09-27) and parses the most recent `hdi_YYYY`
column with a value for each tracked country. Updates roughly once a year
alongside the annual Human Development Report - UI copy for anything
derived from this must say "synced from the latest official UNDP release,"
never "live" (see the project plan's SEO/data-honesty section).
"""
from __future__ import annotations

import csv
import io
import re

import httpx

from ..db import now
from ..models import Observation

CSV_URL = "https://hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_complete_time_series.csv"
# metric_id -> UNDP column prefix. The file is wide (1112 columns): one column
# per metric per year, named `hdi_1990`..`hdi_2023`.
#   hdi = Human Development Index (composite)
#   mys = Mean years of schooling
# `mys` was added 2026-09-28 because education was the one dimension with NO
# indicator anywhere in the risk model - income, health, employment,
# demographics, climate and energy were all covered, schooling was not. WDI
# does carry `SE.SEC.ENRR`, but enrolment counts students present rather than
# the learning they got, and UNDP's figure is the one already ingested here.
COLUMNS: dict[str, str] = {
    "hdi": "hdi",
    "mean_years_schooling": "mys",
}
_YEAR_COLUMN = re.compile(r"^([a-z_]+)_(\d{4})$")


def fetch(iso3_list: list[str]) -> list[Observation]:
    resp = httpx.get(CSV_URL, timeout=60.0, follow_redirects=True)
    resp.raise_for_status()
    # UNDP's own CSV isn't UTF-8 (country names like "Côte d'Ivoire" break
    # strict utf-8 decoding) - latin-1 never raises and is the right
    # encoding for this specific file (confirmed by inspecting real output).
    text = resp.content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    # Newest year present for each requested column prefix, independently -
    # the HDI composite and the schooling series are not guaranteed to be
    # populated in the same year for the same country.
    newest: dict[str, str] = {}
    for name in fieldnames:
        if not (m := _YEAR_COLUMN.match(name)):
            continue
        prefix, year = m.group(1), m.group(2)
        if prefix in COLUMNS.values() and year > newest.get(prefix, ""):
            newest[prefix] = year
    wanted = set(iso3_list)
    fetched_at = now()
    observations: list[Observation] = []
    for row in reader:
        iso3 = row.get("iso3")
        if iso3 not in wanted:
            continue
        for metric_id, prefix in COLUMNS.items():
            year = newest.get(prefix)
            if not year:
                continue
            raw = (row.get(f"{prefix}_{year}") or "").strip()
            # "" and ".." are UNDP's two spellings of "no value".
            if raw and raw != "..":
                try:
                    value = float(raw)
                except ValueError:
                    continue
                observations.append(Observation(
                    iso3=iso3, metric_id=metric_id, period=year,
                    value=value, fetched_at=fetched_at,
                ))
    return observations
