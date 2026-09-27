"""Real-time conflict/cooperation signal per bloc and per bloc-pair -
ported from the standalone `GFCA` ("Grounded Crisis Analysis") tool
(~/my-projects/GFCA) into Global Monitor as a new module, at the user's
request (2026-09-27), instead of leaving it a separate deployment. GDELT
events are grouped by OUR bloc memberships (blocs.py) instead of GFCA's own
ad-hoc country-list queries - see `_touches`/`_is_bilateral` below.

Unlike every other data source in this project (annual/quarterly
structural indicators from World Bank/Comtrade/UNDP/SIPRI), this is an
hours-scale snapshot - see scheduler.py's own separate, more frequent job
for this module specifically. Everything here is a directly computable
statistic (counts, means, a real before/after delta) over real events -
no prediction, no fabricated confidence score, matching GFCA's own
"Scope decision" (see its README): the whole point is not to repeat an
unfounded accuracy claim.
"""
from __future__ import annotations

from . import db
from .config import settings
from .ingestion.gdelt import Event, fetch_window
from .models import TensionScore

_MAX_EXAMPLES = 5

# The most recently fetched GDELT window, kept in memory - reused by
# query_pair() (an ad-hoc, on-demand two-COUNTRY analysis, the counterpart
# to GFCA's own CLI: `analyze IR US`) instead of hitting GDELT again per
# request. This process runs continuously between scheduled refreshes (the
# Astro rebuild after each refresh is a subprocess, not a restart), so an
# in-memory cache is simple and sufficient - no need to persist it to disk.
_last_events: list[Event] = []

# The 4 blocs that participate in the main compare structure (same set as
# lib/pairs.ts/synthesis.py's own _COMPARE_BLOCS) -> 6 pairs. brics5 is
# deliberately excluded here too, same reasoning as everywhere else in this
# project: a secondary historical view of `brics`, not a 5th comparison
# target.
_COMPARE_BLOCS = ["brics", "eu", "us", "usmca"]
_PAIRS = [(_COMPARE_BLOCS[i], _COMPARE_BLOCS[j])
          for i in range(len(_COMPARE_BLOCS)) for j in range(i + 1, len(_COMPARE_BLOCS))]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _format_event(e: Event, kind: str) -> dict:
    return {
        "kind": kind, "date": e.event_date.isoformat(), "actor1": e.actor1_name,
        "actor2": e.actor2_name, "location": e.action_location,
        "goldstein": e.goldstein_scale, "source_url": e.source_url,
    }


def _dedup_by_source(ordered: list[Event], n: int) -> list[Event]:
    """The raw GDELT export has one row per (event, mentioning article)
    pair, so the same real-world story routinely produces several
    near-identical rows at the same extreme Goldstein score - dedup by
    source_url so citations are N actually-distinct stories, not the same
    headline repeated."""
    seen: set[str] = set()
    picked: list[Event] = []
    for e in ordered:
        key = e.source_url or f"__no_url_{e.global_event_id}"
        if key in seen:
            continue
        seen.add(key)
        picked.append(e)
        if len(picked) >= n:
            break
    return picked


def _summarize(events: list[Event], scope: str, window_hours: float) -> TensionScore:
    scored = [e for e in events if e.goldstein_scale is not None]
    goldstein_values = [e.goldstein_scale for e in scored]
    tone_values = [e.avg_tone for e in events if e.avg_tone is not None]

    # GDELT QuadClass: 1=Verbal Cooperation, 2=Material Cooperation,
    # 3=Verbal Conflict, 4=Material Conflict.
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for e in events:
        if e.quad_class in counts:
            counts[e.quad_class] += 1
    total = sum(counts.values())
    conflict_share = (counts[3] + counts[4]) / total if total else None

    delta = None
    dated = sorted((e for e in scored if e.date_added is not None), key=lambda e: e.date_added)
    if len(dated) >= 4:  # need a real sample on both sides, not just 1-2 events
        mid = len(dated) // 2
        first_half = _mean([e.goldstein_scale for e in dated[:mid]])
        second_half = _mean([e.goldstein_scale for e in dated[mid:]])
        if first_half is not None and second_half is not None:
            delta = second_half - first_half

    by_goldstein = sorted(scored, key=lambda e: e.goldstein_scale)
    examples = (
        [_format_event(e, "conflictual") for e in _dedup_by_source(by_goldstein, _MAX_EXAMPLES)]
        + [_format_event(e, "cooperative") for e in _dedup_by_source(list(reversed(by_goldstein)), _MAX_EXAMPLES)]
    )

    return TensionScore(
        scope=scope, window_hours=window_hours, n_events=len(events),
        mean_goldstein=_mean(goldstein_values), mean_tone=_mean(tone_values),
        verbal_cooperation=counts[1], material_cooperation=counts[2],
        verbal_conflict=counts[3], material_conflict=counts[4],
        conflict_share=conflict_share, goldstein_delta=delta, examples=examples,
        computed_at=db.now(),
    )


def _touches(e: Event, codes: set[str]) -> bool:
    """Deliberately actor1/actor2 only, NOT action_country_code - confirmed
    live (2026-09-27): GDELT's actor country codes are CAMEO, which match
    ISO 3166-1 alpha-3 for real countries (verified against a real fetch:
    USA/FRA/DEU/GBR/etc. all matched exactly), but ActionGeo_CountryCode is
    a DIFFERENT scheme entirely - FIPS 10-4 2-letter codes (e.g. "RP" for
    the Philippines, "UK" for the United Kingdom) - comparing it against our
    ISO3 sets would silently never match anything. Actor codes alone are
    also the more semantically correct signal anyway: who is interacting,
    not where a related news article happened to be geotagged."""
    return e.actor1_country_code in codes or e.actor2_country_code in codes


def _is_bilateral(e: Event, codes_a: set[str], codes_b: set[str]) -> bool:
    """Real interaction BETWEEN the two sides specifically - stricter than
    `_touches` on both groups at once, which would also match a purely
    internal event within one bloc."""
    return ((e.actor1_country_code in codes_a and e.actor2_country_code in codes_b)
            or (e.actor1_country_code in codes_b and e.actor2_country_code in codes_a))


def refresh_all() -> int:
    """Fetches ONE GDELT window and reuses it for every bloc's own score
    plus every bloc-pair's bilateral score - a single network fetch shared
    across all scopes, not one fetch per bloc/pair. Returns the number of
    scopes updated (0 if the GDELT fetch itself returned nothing, e.g. a
    transient outage - callers should treat that as "try again next
    cycle," not a hard failure)."""
    window_hours = settings.tension_window_hours
    events = fetch_window(window_hours)
    if not events:
        return 0

    global _last_events
    _last_events = events

    members_by_bloc = {b.bloc_id: set(db.get_current_members(b.bloc_id)) for b in db.get_blocs()}

    count = 0
    for bloc_id, codes in members_by_bloc.items():
        if not codes:
            continue
        db.upsert_tension_score(_summarize([e for e in events if _touches(e, codes)],
                                            f"bloc:{bloc_id}", window_hours))
        count += 1

    for a, b in _PAIRS:
        codes_a, codes_b = members_by_bloc.get(a, set()), members_by_bloc.get(b, set())
        if not codes_a or not codes_b:
            continue
        matched = [e for e in events if _is_bilateral(e, codes_a, codes_b)]
        db.upsert_tension_score(_summarize(matched, f"pair:{a}-{b}", window_hours))
        count += 1

    return count


def query_pair(iso3_a: str, iso3_b: str) -> TensionScore | None:
    """Ad-hoc, on-demand analysis between any two specific countries - not
    limited to our 4 tracked blocs. The counterpart to GFCA's own CLI
    (`analyze IR US`), added after user feedback that the bloc-only version
    dropped this part of the original tool. Reuses whichever window
    refresh_all() last fetched (see `_last_events`) rather than fetching
    GDELT again per call - this is reachable from a public page, and a
    live GDELT download per click would be both slow and easy to abuse.
    Returns None if no window has been fetched yet (fresh boot, before the
    first refresh completes) - the caller should treat that as "try again
    shortly," not a permanent failure.

    Deliberately has NO LLM synthesis, unlike the bloc/pair scores - see
    api/app.py's own comment on why an unbounded public query endpoint
    shouldn't trigger a real LLM call per request."""
    if not _last_events:
        return None
    codes_a, codes_b = {iso3_a.upper()}, {iso3_b.upper()}
    matched = [e for e in _last_events if _is_bilateral(e, codes_a, codes_b)]
    return _summarize(matched, f"query:{iso3_a.upper()}-{iso3_b.upper()}", settings.tension_window_hours)
