"""UN Comtrade, via the OFFICIAL `comtradeapicall` PyPI package (not a
hand-rolled HTTP client - Comtrade's own request/response shape has enough
quirks, e.g. numeric M49 reporter/partner codes instead of ISO3, that
reusing the maintained client is the safer choice).

Two functions, matching the two trade-scope decisions from the project
plan:
- `fetch_world_totals`: each tracked country's total exports/imports to
  the WORLD (partnerCode="0") - one call per country per flow direction.
- `fetch_intra_bloc_flows`: for a bloc with 2+ members, each member's
  exports to every OTHER member, one call per reporter with all other
  members as a comma-joined partner list (NOT one call per bilateral pair -
  that would be N*(N-1) calls for an N-member bloc, e.g. 702 for the EU's
  27 members). Only exports are tracked - summing every member's
  exports-to-other-members already captures the bloc's total intra-bloc
  trade volume without also needing the (largely redundant) import
  direction.

Runs key-less by default (COMTRADE_API_KEY unset). CONFIRMED LIVE
(2026-09-27): the key-less "preview" quota is exhausted well before this
project's ~125-call full run completes (`previewFinalData` then prints a
`{"statusCode": 403, "message": "Out of call volume quota..."}` line and
returns an empty/None result, rather than raising) - `_ConsecutiveFailureBreaker`
below stops making further calls after a run of consecutive empty results,
instead of burning through the rest of the country/bloc list at 1 call/sec
for no benefit once the quota is known to be exhausted. Registering a real
COMTRADE_API_KEY (set in .env) raises the limit considerably - see
config.py's own comment.
"""
from __future__ import annotations

import time
from functools import lru_cache

import comtradeapicall

from ..db import now
from ..models import BlocTradeFlow, Observation

_CALL_DELAY_SECONDS = 1.0
_MAX_CONSECUTIVE_FAILURES = 4


class _ConsecutiveFailureBreaker:
    def __init__(self, max_consecutive: int = _MAX_CONSECUTIVE_FAILURES):
        self._max = max_consecutive
        self._streak = 0
        self.tripped = False

    def reset(self) -> None:
        self._streak = 0
        self.tripped = False

    def record(self, succeeded: bool) -> None:
        if succeeded:
            self._streak = 0
        else:
            self._streak += 1
            if self._streak >= self._max:
                self.tripped = True


# Module-level, shared across fetch_world_totals AND every fetch_intra_bloc_flows
# call within one ingest run - the quota is an account-level limit, not a
# per-function one, so a fresh breaker per bloc would let each of the 5
# blocs burn through _MAX_CONSECUTIVE_FAILURES more calls even after the
# quota is already known to be exhausted. pipeline.py calls reset_breaker()
# once at the start of each "comtrade" source run.
_breaker = _ConsecutiveFailureBreaker()


def reset_breaker() -> None:
    _breaker.reset()


@lru_cache(maxsize=None)
def _reporter_table():
    """Comtrade's own reference/metadata endpoint - NOT the rate-limited
    previewFinalData quota, safe to call once and cache for the process
    lifetime."""
    return comtradeapicall.getReference("reporter")


@lru_cache(maxsize=None)
def _country_code(iso3: str) -> str | None:
    """Comtrade's own reporter codes are numeric, not ISO3, and
    convertCountryIso3ToCode's comma-separated list is ORDERED
    UNRELIABLY - confirmed live (2026-09-27): for DEU it returns
    "280,276" with 280 being the pre-1990 "Fed. Rep. of Germany" entity
    (expired), and for USA/CHE it returns "840,756" as the FIRST code,
    neither of which exists at all in Comtrade's own reporter table
    (840/756 are ISO 3166-1 numeric codes, not Comtrade reporter codes -
    previewFinalData silently returns empty for them, never an error).
    This silently dropped all trade data for the US, Germany, and
    Switzerland from every ingest run until fixed. Resolve properly
    instead: look up the CURRENT (non-expired) entry for this iso3 in
    Comtrade's own reporter reference table."""
    table = _reporter_table()
    matches = table[table["reporterCodeIsoAlpha3"] == iso3]
    current = matches[matches["entryExpiredDate"].isna()]
    if not current.empty:
        return str(current.iloc[0]["reporterCode"])
    if not matches.empty:
        return str(matches.iloc[0]["reporterCode"])
    return None


def fetch_world_totals(iso3_list: list[str], period: str) -> list[Observation]:
    fetched_at = now()
    observations: list[Observation] = []
    for iso3 in iso3_list:
        if _breaker.tripped:
            break
        code = _country_code(iso3)
        if code is None:
            continue
        for flow_code, metric_id in (("X", "trade_exports_world_usd"), ("M", "trade_imports_world_usd")):
            if _breaker.tripped:
                break
            try:
                df = comtradeapicall.previewFinalData(
                    typeCode="C", freqCode="A", clCode="HS", period=period,
                    reporterCode=code, cmdCode="TOTAL", flowCode=flow_code,
                    partnerCode="0", partner2Code=None, customsCode=None, motCode=None,
                )
            except Exception:
                df = None
            time.sleep(_CALL_DELAY_SECONDS)
            got_data = df is not None and not df.empty
            _breaker.record(succeeded=got_data)
            if not got_data:
                continue
            value = float(df.iloc[0]["primaryValue"])
            observations.append(Observation(iso3=iso3, metric_id=metric_id, period=period,
                                              value=value, fetched_at=fetched_at))
    return observations


def fetch_intra_bloc_flows(
    bloc_id: str, member_iso3_list: list[str], period: str
) -> list[BlocTradeFlow]:
    if len(member_iso3_list) < 2:
        return []  # a single-country "bloc" (US) has no possible intra-bloc pairs
    fetched_at = now()
    codes = {iso3: _country_code(iso3) for iso3 in member_iso3_list}
    code_to_iso3 = {v: k for k, v in codes.items()}
    flows: list[BlocTradeFlow] = []
    for reporter_iso3 in member_iso3_list:
        if _breaker.tripped:
            break
        reporter_code = codes[reporter_iso3]
        if reporter_code is None:
            continue
        partner_codes = [codes[p] for p in member_iso3_list if p != reporter_iso3 and codes[p] is not None]
        if not partner_codes:
            continue
        try:
            df = comtradeapicall.previewFinalData(
                typeCode="C", freqCode="A", clCode="HS", period=period,
                reporterCode=reporter_code, cmdCode="TOTAL", flowCode="X",
                partnerCode=",".join(partner_codes), partner2Code=None, customsCode=None, motCode=None,
            )
        except Exception:
            df = None
        time.sleep(_CALL_DELAY_SECONDS)
        got_data = df is not None and not df.empty
        _breaker.record(succeeded=got_data)
        if not got_data:
            continue
        for _, row in df.iterrows():
            partner_iso3 = code_to_iso3.get(str(row["partnerCode"]))
            if partner_iso3 is None:
                continue
            flows.append(BlocTradeFlow(
                bloc_id=bloc_id, reporter_iso3=reporter_iso3, partner_iso3=partner_iso3,
                metric_id="trade_intra_bloc_exports_usd", period=period,
                value=float(row["primaryValue"]), fetched_at=fetched_at,
            ))
    return flows
