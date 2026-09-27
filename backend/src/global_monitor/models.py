from __future__ import annotations

from dataclasses import dataclass
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
