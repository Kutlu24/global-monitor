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
_YEAR_COLUMN = re.compile(r"^hdi_(\d{4})$")


def fetch(iso3_list: list[str]) -> list[Observation]:
    resp = httpx.get(CSV_URL, timeout=60.0, follow_redirects=True)
    resp.raise_for_status()
    # UNDP's own CSV isn't UTF-8 (country names like "Côte d'Ivoire" break
    # strict utf-8 decoding) - latin-1 never raises and is the right
    # encoding for this specific file (confirmed by inspecting real output).
    text = resp.content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    year_columns = sorted(
        (m.group(1) for name in (reader.fieldnames or []) if (m := _YEAR_COLUMN.match(name))),
        reverse=True,
    )
    wanted = set(iso3_list)
    fetched_at = now()
    observations: list[Observation] = []
    for row in reader:
        iso3 = row.get("iso3")
        if iso3 not in wanted:
            continue
        for year in year_columns:
            raw = row.get(f"hdi_{year}", "").strip()
            if raw:
                observations.append(Observation(iso3=iso3, metric_id="hdi", period=year,
                                                  value=float(raw), fetched_at=fetched_at))
                break  # only the most recent non-empty year per country
    return observations
