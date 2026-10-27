"""Numeric grounding check for the LLM-written bloc/compare paragraphs.

synthesis.py tells the model "use ONLY the real figures below", but nothing
checks that it did. This module takes every number in a stored paragraph and
looks for it in the figures that page's prompt was built from (plus the
periods, and simple derived values such as ratios and differences, since the
compare prompt asks for "roughly how much"). It is a read-only audit: it
never writes to the database and never calls an LLM.

Verdicts per number:
  grounded    equals a prompt figure after rounding to the written precision
              (and the unit class agrees: % needs a % metric, $ a USD one)
  loose       within one unit of the last written digit (truncation, not rounding)
  derived     equals a ratio / difference / sum of two prompt figures
  year        a 4-digit year that appears as a period in the prompt data
  incidental  a bare small integer with no unit (counts, "top 3", "BRICS5")
  magnitude_error  the digits of a prompt figure but off by a power of ten
  ungrounded  none of the above - an invented or misattributed figure

`wrong_metric` is a separate verdict: the number matches a prompt figure but
its unit class contradicts that metric (e.g. "$1.7 trillion" matching a
percentage).
"""
from __future__ import annotations

import itertools
import math
import re
from dataclasses import dataclass, field

from . import db
from .synthesis import _COMPARE_BLOCS, _DIMENSIONS, _bloc_snapshot, _data_hash

_SCALES = {"trillion": 1e12, "billion": 1e9, "million": 1e6, "thousand": 1e3}

_NUM_RE = re.compile(
    r"(?P<cur>\$|US\$|€)?\s?(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?:\s?(?P<scale>trillion|billion|million|thousand)\b)?"
    r"(?P<pct>\s?%|\s?percent\b)?",
    re.IGNORECASE,
)


@dataclass
class Figure:
    metric_id: str
    unit: str
    value: float
    owner: str = ""  # bloc id for compare pages

    @property
    def klass(self) -> str:
        u = self.unit.lower()
        if "%" in u:
            return "pct"
        if "usd" in u or "$" in u:
            return "usd"
        return "other"


@dataclass
class NumberVerdict:
    text: str
    value: float
    verdict: str
    detail: str = ""


@dataclass
class PageReport:
    page_key: str
    provider: str
    model: str
    stale: bool
    numbers: list[NumberVerdict] = field(default_factory=list)
    broken_decimals: int = 0

    def count(self, verdict: str) -> int:
        return sum(1 for n in self.numbers if n.verdict == verdict)

    @property
    def clean(self) -> bool:
        return not any(n.verdict in ("ungrounded", "wrong_metric", "magnitude_error") for n in self.numbers)


# The small local model sometimes writes "5. 467" for 5.467; the figure is
# recoverable but the page would render it wrongly, so it is counted separately.
_BROKEN_DECIMAL_RE = re.compile(r"(?<=\d)\.\s+(?=\d)")


def count_broken_decimals(text: str) -> int:
    return len(_BROKEN_DECIMAL_RE.findall(text))


def extract_numbers(text: str) -> list[tuple[str, float, float, str, bool]]:
    """Returned as (surface, value, unit_step, klass_hint, has_unit_marker)."""
    out = []
    for m in _NUM_RE.finditer(_BROKEN_DECIMAL_RE.sub(".", text)):
        raw = m.group("num").replace(",", "")
        value = float(raw)
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        step = 10 ** -decimals
        scale = m.group("scale")
        if scale:
            value *= _SCALES[scale.lower()]
            step *= _SCALES[scale.lower()]
        klass = "pct" if m.group("pct") else ("usd" if m.group("cur") else "any")
        has_marker = bool(scale or m.group("pct") or m.group("cur"))
        out.append((m.group(0).strip(), value, step, klass, has_marker))
    return out


def _figures_for(page_key: str) -> tuple[list[Figure], set[str], dict] | None:
    """The figures the generating prompt saw, the periods, and the hash payload."""
    metrics = db.get_metrics()
    unit_of = {m.metric_id: m.unit for m in metrics}
    parts = page_key.split(":")
    if parts[0] == "bloc":
        blocs = [parts[1]]
        dim = None
    elif parts[0] == "compare":
        a, b = parts[1].split("-vs-")
        blocs = [a, b]
        dim = parts[2] if len(parts) > 2 else None
    else:
        return None
    dim_ids = None if dim is None else {m.metric_id for m in metrics if m.dimension == dim}
    figures, periods, snaps = [], set(), {}
    for bloc_id in blocs:
        snap = _bloc_snapshot(bloc_id)
        snaps[bloc_id] = snap
        for metric_id, (value, period) in snap.items():
            if dim_ids is not None and metric_id not in dim_ids:
                continue
            if value is None:
                continue
            figures.append(Figure(metric_id, unit_of[metric_id], float(value), bloc_id))
            periods.add(str(period))
    if parts[0] == "bloc":
        payload = snaps[blocs[0]]
    else:
        a, b = blocs
        payload = {**{f"a:{k}": v for k, v in snaps[a].items() if dim_ids is None or k in dim_ids},
                   **{f"b:{k}": v for k, v in snaps[b].items() if dim_ids is None or k in dim_ids}}
    return figures, periods, payload


def _metric_constants() -> set[float]:
    consts = set()
    for m in db.get_metrics():
        for _surface, value, *_ in extract_numbers(f"{m.name} {m.unit}"):
            consts.add(value)
    return consts


def _classify(surface, value, step, hint, has_marker, figures, periods, derived, constants):
    # Years
    if re.fullmatch(r"(19|20)\d{2}", surface) and surface in periods:
        return NumberVerdict(surface, value, "year")
    if re.fullmatch(r"(19|20)\d{2}", surface):
        return NumberVerdict(surface, value, "ungrounded", "year not among the prompt's periods")
    # Direct matches. The prompt shows figures at 4 significant digits, so a
    # paragraph can only be as exact as that; tolerance is the coarser of
    # (half the written last digit) and (0.5% of the figure's 4-sig-fig rounding).
    # Constants that live in metric names/units ("$3.65/day", "per 1,000") are echoed, not invented.
    if value in constants:
        return NumberVerdict(surface, value, "incidental", "constant from a metric name")
    best, mismatch = None, None
    for f in figures:
        diff = abs(value - abs(f.value))  # the regex drops minus signs, so compare magnitudes
        if diff <= step / 2 + 1e-9 * abs(f.value) or diff <= abs(f.value) * 0.0005:
            grade = "grounded"
        elif diff <= step:
            grade = "loose"
        else:
            continue
        if (hint == "pct" and f.klass != "pct") or (hint == "usd" and f.klass != "usd"):
            # Only a precise (3+ significant digits) clash is evidence of misattribution;
            # a bare "$9" matching 9.4 of anything is coincidence.
            if grade == "grounded" and len(surface.replace(".", "").replace(",", "").lstrip("$0")) >= 3:
                mismatch = mismatch or f
            continue
        if best is None or grade == "grounded":
            best = (grade, f)
            if grade == "grounded":
                break
    if best:
        verdict, f = best
        return NumberVerdict(surface, value, verdict, f"{f.metric_id} [{f.owner}]")
    if mismatch is not None:
        f = mismatch
        return NumberVerdict(surface, value, "wrong_metric", f"matches {f.metric_id} ({f.unit}) but its unit marker disagrees")
    for label, d in derived:
        if abs(value - d) <= max(step / 2, abs(d) * 0.006):
            return NumberVerdict(surface, value, "derived", label)
    # Right digits, wrong order of magnitude ("$95.44 billion" for 954.4 billion): the
    # model dropped or shifted a digit group. Needs 3+ significant digits to be evidence.
    # Only for figures written with a unit marker ($, %, a scale word), a unit class that
    # agrees with the metric, and a shift of at most three powers: a bare "3.492" or a
    # shift of x10^9 is unit-stripping or coincidence, not a slipped digit group.
    if has_marker and len(surface.replace(".", "").replace(",", "").lstrip("$0")) >= 3 and value > 0:
        for f in figures:
            if f.value == 0 or (hint == "pct" and f.klass != "pct") or (hint == "usd" and f.klass != "usd"):
                continue
            ratio = value / abs(f.value)
            exp = round(math.log10(ratio))
            if exp != 0 and abs(exp) <= 3 and abs(ratio / 10 ** exp - 1) <= 0.006:
                return NumberVerdict(surface, value, "magnitude_error",
                                     f"digits of {f.metric_id} [{f.owner}] but x10^{exp}")
    if not has_marker and value == int(value) and value <= 20 and "." not in surface:
        return NumberVerdict(surface, value, "incidental")
    return NumberVerdict(surface, value, "ungrounded")


def _derived_values(figures: list[Figure]):
    out = []
    by_metric: dict[str, list[Figure]] = {}
    for f in figures:
        by_metric.setdefault(f.metric_id, []).append(f)
    for metric_id, fs in by_metric.items():
        for x, y in itertools.permutations(fs, 2):
            if x.value and y.value:
                out.append((f"{metric_id}: {x.owner}/{y.owner} ratio", x.value / y.value))
                out.append((f"{metric_id}: {x.owner}-{y.owner} difference", abs(x.value - y.value)))
        if len(fs) == 2:
            out.append((f"{metric_id}: sum", fs[0].value + fs[1].value))
    # A single bloc: shares of one metric in another (e.g. "8% of global GDP") are not
    # derivable from the prompt, so are deliberately not allowed here.
    return out


def verify_page(row) -> PageReport | None:
    found = _figures_for(row.page_key)
    if found is None:
        return None
    figures, periods, payload = found
    report = PageReport(row.page_key, row.provider, row.model, stale=_data_hash(payload) != row.data_hash)
    derived = _derived_values(figures)
    constants = _metric_constants()
    report.broken_decimals = count_broken_decimals(row.text)
    for surface, value, step, hint, marker in extract_numbers(row.text):
        report.numbers.append(_classify(surface, value, step, hint, marker, figures, periods, derived, constants))
    return report


def verify_all() -> list[PageReport]:
    """Every stored English bloc/compare paragraph (translations are skipped:
    their numbers are checked by the translation prompt's own copy-through rule)."""
    reports = []
    for row in db.list_synthesis():
        if "|" in row.page_key:
            continue
        r = verify_page(row)
        if r is not None:
            reports.append(r)
    return reports


def summarize(reports: list[PageReport]) -> dict:
    total = sum(len(r.numbers) for r in reports)
    verdicts = ["grounded", "loose", "derived", "year", "incidental", "ungrounded", "magnitude_error", "wrong_metric"]
    return {
        "pages": len(reports),
        "pages_clean": sum(1 for r in reports if r.clean),
        "pages_stale": sum(1 for r in reports if r.stale),
        "numbers": total,
        "pages_with_broken_decimals": sum(1 for r in reports if r.broken_decimals),
        **{v: sum(r.count(v) for r in reports) for v in verdicts},
    }
