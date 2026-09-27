from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Dimension = Literal["economic", "trade", "social", "military"]
Aggregation = Literal["sum", "mean", "weighted_mean"]


@dataclass(frozen=True)
class Bloc:
    bloc_id: str
    name: str
    slug: str
    description: str = ""


@dataclass(frozen=True)
class Country:
    iso3: str
    name: str


@dataclass(frozen=True)
class BlocMembership:
    bloc_id: str
    iso3: str
    effective_from: str
    effective_to: str | None = None


@dataclass(frozen=True)
class Metric:
    metric_id: str
    dimension: Dimension
    name: str
    unit: str
    source: str
    source_dataset_code: str | None
    license: str | None
    update_cadence: Literal["continuous", "quarterly", "annual"]
    default_aggregation: Aggregation
    weight_metric_id: str | None = None


@dataclass(frozen=True)
class Observation:
    iso3: str
    metric_id: str
    period: str
    value: float | None
    fetched_at: str


@dataclass(frozen=True)
class BlocTradeFlow:
    bloc_id: str
    reporter_iso3: str
    partner_iso3: str
    metric_id: str
    period: str
    value: float | None
    fetched_at: str


@dataclass(frozen=True)
class BlocAggregate:
    bloc_id: str
    metric_id: str
    period: str
    value: float | None
    member_count: int
    computed_at: str


@dataclass(frozen=True)
class SynthesisText:
    page_key: str
    text: str
    data_hash: str
    generated_at: str
    provider: str
    model: str


@dataclass(frozen=True)
class TensionScore:
    """A real-time (GDELT-derived) conflict/cooperation signal - ported
    from the standalone `GFCA` ("Grounded Crisis Analysis") tool into
    Global Monitor as a new module, see tension.py's own docstring. Unlike
    every other metric in this project (annual/quarterly structural
    indicators), this is an hours-scale snapshot, recomputed every few
    hours, not daily/weekly - `scope` is either `bloc:{bloc_id}` (any real
    event touching that bloc's own members) or `pair:{a}-{b}` (bilateral
    events between two blocs' members specifically)."""
    scope: str
    window_hours: float
    n_events: int
    mean_goldstein: float | None  # -10 (most conflictual) .. +10 (most cooperative)
    mean_tone: float | None  # article sentiment, roughly -100..+100
    verbal_cooperation: int
    material_cooperation: int
    verbal_conflict: int
    material_conflict: int
    conflict_share: float | None
    goldstein_delta: float | None  # second-half mean - first-half mean of the window
    examples: list[dict] = field(default_factory=list)  # a handful of real (date, actors, location, goldstein, source_url) dicts, for citation/grounding - never fabricated
    computed_at: str = ""
