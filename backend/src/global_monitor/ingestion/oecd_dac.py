"""OECD Development Assistance Committee: net official development assistance given, from the
OECD SDMX API (`DSD_DAC1@DF_DAC1`, measure 11010, grant-equivalent basis, current US$).

Only DAC members and the few non-member reporters are in this dataset, so a country with no row
is a country that does not report, not a country that gave nothing. A bloc total therefore sums
the reporters among its members; the metric name says so.

`oecd.org` itself answers non-browser clients with 403, but `sdmx.oecd.org` serves the API
(verified 2026-10-28). Donor codes are ISO3, plus aggregates (`DAC`, `EU`, ...) that are not
countries and are dropped by the caller's `iso3_list` filter.
"""
from __future__ import annotations

import io

import httpx
import pandas as pd

from ..db import now
from ..models import Observation

URL = ("https://sdmx.oecd.org/public/rest/data/OECD.DCD.FSD,DSD_DAC1@DF_DAC1,1.5/"
       ".11010._Z.1160.USD.V._Z")
_YEARS_BACK = 3
_MIN_COVERAGE = 20  # DAC has ~32 members


def fetch(iso3_list: list[str], last_year: int) -> list[Observation]:
    wanted = set(iso3_list)
    resp = httpx.get(URL, params={"startPeriod": str(last_year - _YEARS_BACK), "endPeriod": str(last_year)},
                     headers={"Accept": "application/vnd.sdmx.data+csv; charset=utf-8"},
                     timeout=120.0, follow_redirects=True)
    resp.raise_for_status()
    table = pd.read_csv(io.StringIO(resp.text))
    table["value"] = pd.to_numeric(table["OBS_VALUE"], errors="coerce") * 10.0 ** pd.to_numeric(
        table["UNIT_MULT"], errors="coerce").fillna(0)
    table = table.dropna(subset=["value"])
    if table["DONOR"].nunique() < _MIN_COVERAGE:
        raise RuntimeError(f"OECD DAC1: only {table['DONOR'].nunique()} donors, expected {_MIN_COVERAGE}+. "
                           "Refusing to store a thin pull.")
    fetched_at = now()
    out: list[Observation] = []
    for r in table.sort_values("TIME_PERIOD").groupby("DONOR").tail(1).itertuples():
        if r.DONOR in wanted:
            out.append(Observation(iso3=r.DONOR, metric_id="oda_given_usd", period=str(r.TIME_PERIOD),
                                   value=float(r.value), fetched_at=fetched_at))
    return out
