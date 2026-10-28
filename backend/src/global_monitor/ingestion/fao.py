"""FAO food-security indicators, from the FAOSTAT bulk file "Food Security Data".

FAOSTAT has no ISO3 column; areas carry a UN M49 code written with a leading apostrophe ("'840"),
translated through `_m49`. Regions and income groups have M49 codes that are not countries and
fall out of that lookup.

The series is published as a 3-year average ("2023-2025"), so the period stored is that range, not
a single year. Only the newest window in the file is taken: aggregate.py buckets by period, so
mixing windows would split a bloc into thin aggregates.

Prevalence of undernourishment is deliberately not ingested. FAO prints "<2.5" for low-prevalence
countries, which is not a number, so rich countries drop out (18 of 48 tracked countries have a
value) and a bloc mean would be biased upwards by whoever is left.
"""
from __future__ import annotations

import io
import zipfile

import httpx
import pandas as pd

from ..db import now
from ..models import Observation
from ._m49 import M49_TO_ISO3

URL = "https://bulks-faostat.fao.org/production/Food_Security_Data_E_All_Data_(Normalized).zip"

# metric_id -> FAOSTAT item name
ITEMS: dict[str, str] = {
    "food_insecurity_pct": "Prevalence of moderate or severe food insecurity in the total population (percent) (3-year average)",
}

_MIN_COVERAGE = 100  # countries per metric


def _read_table() -> pd.DataFrame:
    resp = httpx.get(URL, timeout=180.0, follow_redirects=True)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        name = next(n for n in z.namelist() if n.endswith("All_Data_(Normalized).csv"))
        return pd.read_csv(z.open(name), encoding="latin-1", low_memory=False)


def fetch(iso3_list: list[str]) -> list[Observation]:
    wanted = set(iso3_list)
    table = _read_table()
    table["iso3"] = pd.to_numeric(table["Area Code (M49)"].astype(str).str.lstrip("'"),
                                  errors="coerce").map(M49_TO_ISO3)
    fetched_at = now()
    out: list[Observation] = []
    for metric_id, item in ITEMS.items():
        # Each country-year has three rows: the value and the lower and upper confidence bounds.
        rows = table[(table["Item"] == item) & (table["Element"] == "Value") & table["iso3"].notna()].copy()
        rows["value"] = pd.to_numeric(rows["Value"], errors="coerce")
        rows = rows[rows["value"].notna()]
        if rows["iso3"].nunique() < _MIN_COVERAGE:
            raise RuntimeError(f"FAOSTAT {metric_id}: only {rows['iso3'].nunique()} countries, "
                               f"expected {_MIN_COVERAGE}+. Refusing to store a thin pull.")
        newest = rows.assign(end=rows["Year"].astype(str).str[-4:]).sort_values("end")["Year"].iloc[-1]
        for r in rows[rows["Year"] == newest].itertuples():
            if r.iso3 in wanted:
                out.append(Observation(iso3=r.iso3, metric_id=metric_id, period=str(r.Year),
                                       value=float(r.value), fetched_at=fetched_at))
    return out
