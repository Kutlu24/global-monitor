"""Ingestion from the real GDELT 2.0 Event Database bulk export
(data.gdeltproject.org/gdeltv2/) - ported from the standalone `GFCA`
("Grounded Crisis Analysis") tool, see tension.py's own module docstring
for why this became a Global Monitor module instead of staying separate.

NOT the DOC 2.0 query API: the DOC API enforces a strict 1-request/5s
per-IP rate limit and returned HTTP 429 immediately in GFCA's own testing
(2026-09-09) - the shared egress IP was already throttled. The bulk Event
CSVs are plain static file downloads on a different host with no such
per-request limit, updated every 15 minutes, and carry the real per-event
Goldstein Scale this module needs (the DOC API doesn't expose that at all -
it's article/tone-level, not event-level).

File naming: `{YYYYMMDDHHMMSS}.export.CSV.zip`, timestamps on 15-minute UTC
boundaries. `lastupdate.txt` gives the latest one; earlier files are
reached by walking the timestamp back 15 minutes at a time.
"""
from __future__ import annotations

import io
import zipfile
from datetime import date, datetime, timedelta, timezone

import httpx
from pydantic import BaseModel

from ..config import settings

_LASTUPDATE_URL = "https://data.gdeltproject.org/gdeltv2/lastupdate.txt"
_TS_FORMAT = "%Y%m%d%H%M%S"
_STEP = timedelta(minutes=15)

# 0-indexed column positions in GDELT's 61-column tab-separated row -
# verified against a real live file (GFCA project, 2026-09-09). Only the
# fields this module actually reads are kept.
_COL_GLOBAL_EVENT_ID = 0
_COL_SQLDATE = 1
_COL_ACTOR1_NAME = 6
_COL_ACTOR1_COUNTRY_CODE = 7
_COL_ACTOR2_NAME = 16
_COL_ACTOR2_COUNTRY_CODE = 17
_COL_QUAD_CLASS = 29
_COL_GOLDSTEIN_SCALE = 30
_COL_AVG_TONE = 34
_COL_ACTION_GEO_FULLNAME = 52
_COL_DATE_ADDED = 59
_COL_SOURCE_URL = 60
_EXPECTED_COLUMN_COUNT = 61


class Event(BaseModel):
    global_event_id: int
    event_date: date
    actor1_name: str | None
    actor1_country_code: str | None
    actor2_name: str | None
    actor2_country_code: str | None
    quad_class: int | None  # 1=verbal coop, 2=material coop, 3=verbal conflict, 4=material conflict
    goldstein_scale: float | None  # -10 (most conflictual) .. +10 (most cooperative)
    avg_tone: float | None  # article sentiment, roughly -100..+100
    action_location: str | None  # human-readable place name only - GDELT's
    # own ActionGeo_CountryCode column is FIPS 10-4 (2-letter), a DIFFERENT
    # scheme from the CAMEO/ISO3-compatible actor country codes below, so
    # it's deliberately not modeled here (see tension.py's `_touches`).
    date_added: datetime | None  # when GDELT ingested this, not when it happened
    source_url: str | None

    @classmethod
    def from_row(cls, row: list[str]) -> Event:
        def s(i: int) -> str | None:
            return row[i] or None

        def f(i: int) -> float | None:
            v = row[i]
            return float(v) if v else None

        def n(i: int) -> int | None:
            v = row[i]
            return int(v) if v else None

        return cls(
            global_event_id=int(row[_COL_GLOBAL_EVENT_ID]),
            event_date=datetime.strptime(row[_COL_SQLDATE], "%Y%m%d").date(),
            actor1_name=s(_COL_ACTOR1_NAME),
            actor1_country_code=s(_COL_ACTOR1_COUNTRY_CODE),
            actor2_name=s(_COL_ACTOR2_NAME),
            actor2_country_code=s(_COL_ACTOR2_COUNTRY_CODE),
            quad_class=n(_COL_QUAD_CLASS),
            goldstein_scale=f(_COL_GOLDSTEIN_SCALE),
            avg_tone=f(_COL_AVG_TONE),
            action_location=s(_COL_ACTION_GEO_FULLNAME),
            date_added=(
                datetime.strptime(row[_COL_DATE_ADDED], "%Y%m%d%H%M%S")
                if row[_COL_DATE_ADDED] else None
            ),
            source_url=s(_COL_SOURCE_URL),
        )


class GdeltError(RuntimeError):
    pass


def _latest_export_timestamp(client: httpx.Client) -> datetime:
    resp = client.get(_LASTUPDATE_URL, timeout=20.0)
    resp.raise_for_status()
    for line in resp.text.strip().splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2].endswith(".export.CSV.zip"):
            filename = parts[2].rsplit("/", 1)[-1]
            ts_str = filename.split(".", 1)[0]
            return datetime.strptime(ts_str, _TS_FORMAT).replace(tzinfo=timezone.utc)
    raise GdeltError(f"Could not find an .export.CSV.zip entry in lastupdate.txt: {resp.text[:300]!r}")


def _export_url(ts: datetime) -> str:
    return f"{settings.gdelt_base_url}/{ts.strftime(_TS_FORMAT)}.export.CSV.zip"


def _fetch_and_parse(url: str, client: httpx.Client) -> list[Event]:
    resp = client.get(url, timeout=30.0, follow_redirects=True)
    if resp.status_code == 404:
        return []  # older files can be missing/not-yet-published - skip, don't fail the window
    resp.raise_for_status()
    events: list[Event] = []
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        text = zf.read(csv_name).decode("utf-8", errors="replace")
    for line in text.splitlines():
        if not line.strip():
            continue
        row = line.split("\t")
        if len(row) < _EXPECTED_COLUMN_COUNT:
            continue  # malformed/truncated line - skip rather than crash a whole window fetch
        try:
            events.append(Event.from_row(row))
        except (ValueError, IndexError):
            continue  # one bad row shouldn't lose the rest of a ~2000-row file
    return events


def fetch_window(hours: float | None = None, max_files: int = 32) -> list[Event]:
    """Walks backward from the latest available snapshot in 15-minute
    steps. `max_files` bounds a large request independently of `hours` so
    it can't accidentally trigger dozens of multi-MB downloads. Missing/404
    files are skipped, not fatal. Fetched ONCE per refresh cycle and shared
    across every bloc/pair's aggregation (tension.py), not once per scope."""
    hours = settings.tension_window_hours if hours is None else hours
    n_files = min(max_files, max(1, round(hours * 4)))
    all_events: list[Event] = []
    with httpx.Client() as client:
        ts = _latest_export_timestamp(client)
        for _ in range(n_files):
            all_events.extend(_fetch_and_parse(_export_url(ts), client))
            ts -= _STEP
    return all_events
