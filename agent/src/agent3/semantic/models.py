from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Additivity(StrEnum):
    ADDITIVE = "additive"
    NON_ADDITIVE = "non_additive"


class MetricKind(StrEnum):
    BASE = "base"
    RATIO = "ratio"
    DERIVED = "derived"


class ComparisonKind(StrEnum):
    NONE = "none"
    YOY = "yoy"
    MOM = "mom"


class SelectionMode(StrEnum):
    SINGLE = "single"
    MULTIPLE = "multiple"


@dataclass(frozen=True, slots=True)
class MandatoryFilter:
    field: str
    op: str
    value: Any


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    id: str
    name: str
    aggregation: str
    measure: str
    source_entity: str
    aliases: tuple[str, ...] = ()
    mandatory_filters: tuple[MandatoryFilter, ...] = ()
    additivity_time: Additivity = Additivity.ADDITIVE
    grain: tuple[str, ...] = ()
    valid_dimensions: tuple[str, ...] = ()
    time_field: str = "dt"
    owner: str = ""
    caveats: str = ""
    kind: MetricKind = MetricKind.BASE
    numerator_metric_id: str = ""
    denominator_metric_id: str = ""
    formula: str = ""
    time_grain: str = ""
    latest_strategy: str = "MAX"


@dataclass(frozen=True, slots=True)
class ClarificationOption:
    id: str
    label: str
    description: str
    value: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ClarificationRequest:
    id: str
    question: str
    selection_mode: SelectionMode
    options: tuple[ClarificationOption, ...]
    allow_custom_input: bool = False


@dataclass(frozen=True, slots=True)
class QueryIR:
    metric_id: str
    dimensions: tuple[str, ...] = ()
    filters: tuple[MandatoryFilter, ...] = ()
    time_values: tuple[str, ...] = ()
    comparison: ComparisonKind = ComparisonKind.NONE
    order: str = ""
    limit: int | None = None
