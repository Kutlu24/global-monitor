"""UNCTADstat foreign direct investment (inward flows and stock), from the public bulk file
`US.FdiFlowsStock`, a 7z archive holding one CSV.

Rows carry a UN M49 economy code (`0840`) instead of ISO3, translated through `_m49`; the world
and regional rows are not in that table and drop out. Values are in millions of current US$.
`Flow` 8 is the annual flow, 9 the end-of-year stock; `Direction` 1 is inward.

The latest year with a value is taken per country, limited to `_RECENT` years so a country that
stopped reporting years ago does not appear as current.
"""
from __future__ import annotations

import glob
import io
import tempfile

import httpx
import pandas as pd
import py7zr

from ..db import now
from ..models import Observation
from ._m49 import M49_TO_ISO3

URL = "https://unctadstat-api.unctad.org/bulkdownload/US.FdiFlowsStock/US_FdiFlowsStock"

# metric_id -> UNCTAD `Flow` code
FLOWS: dict[str, int] = {
    "fdi_inward_flow_usd": 8,
    "fdi_inward_stock_usd": 9,
}

_RECENT = 3
_MIN_COVERAGE = 100


def _read_table() -> pd.DataFrame:
    resp = httpx.get(URL, timeout=180.0, follow_redirects=True)
    resp.raise_for_status()
    with tempfile.TemporaryDirectory() as tmp:
        with py7zr.SevenZipFile(io.BytesIO(resp.content)) as z:
            z.extractall(tmp)
        return pd.read_csv(glob.glob(f"{tmp}/*.csv")[0])


def fetch(iso3_list: list[str]) -> list[Observation]:
    wanted = set(iso3_list)
    table = _read_table()
    table["iso3"] = pd.to_numeric(table["Economy"], errors="coerce").map(M49_TO_ISO3)
    value_col = "Millions of US$ at current prices"
    table = table[(table["Direction"] == 1) & table["iso3"].notna()]
    table = table.assign(value=pd.to_numeric(table[value_col], errors="coerce")).dropna(subset=["value"])
    last_year = int(table["Year"].max())
    fetched_at = now()
    out: list[Observation] = []
    for metric_id, flow in FLOWS.items():
        rows = table[(table["Flow"] == flow) & (table["Year"] > last_year - _RECENT)]
        if rows["iso3"].nunique() < _MIN_COVERAGE:
            raise RuntimeError(f"UNCTADstat {metric_id}: only {rows['iso3'].nunique()} countries, "
                               f"expected {_MIN_COVERAGE}+. Refusing to store a thin pull.")
        for r in rows.sort_values("Year").groupby("iso3").tail(1).itertuples():
            if r.iso3 in wanted:
                out.append(Observation(iso3=r.iso3, metric_id=metric_id, period=str(int(r.Year)),
                                       value=float(r.value) * 1e6, fetched_at=fetched_at))
    return out
