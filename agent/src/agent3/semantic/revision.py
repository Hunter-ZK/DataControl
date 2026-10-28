"""Deterministic, source-preserving incremental QueryIR revisions."""
from __future__ import annotations

from typing import Any

from agent3.semantic.models import ComparisonKind, MandatoryFilter, QueryIR

_ALLOWED = {"dimensions", "timeValues", "comparison", "filtersAdd", "order", "orderMetricId", "limit"}


def revise_plan(plan: dict[str, Any], changes: dict[str, Any]) -> QueryIR:
    if not isinstance(plan, dict) or not isinstance(changes, dict):
        raise ValueError("Structured semantic plan and change mapping are required")
    unexpected = set(changes) - _ALLOWED
    if unexpected:
        raise ValueError(f"Unsupported or unsafe revision keys: {sorted(unexpected)}")
    ids = plan.get("metrics", ())
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids):
        raise ValueError("Previous validated metric IDs are required")
    if plan.get("semanticValidated") is not True:
        raise ValueError("Cannot revise a plan that was not semantically validated")
    dims = changes.get("dimensions", plan.get("dimensions", []))
    times = changes.get("timeValues", plan.get("timeValues", []))
    if not isinstance(dims, list) or not all(isinstance(x, str) for x in dims):
        raise ValueError("dimensions must be a list of strings")
    if not isinstance(times, list) or not all(isinstance(x, str) for x in times):
        raise ValueError("timeValues must be a list of strings")
    prior_filters = plan.get("filters", [])
    additions = changes.get("filtersAdd", [])
    if not isinstance(prior_filters, list) or not isinstance(additions, list):
        raise ValueError("Filters must be structured lists")
    combined = []
    for row in [*prior_filters, *additions]:
        if not isinstance(row, dict) or not isinstance(row.get("field"), str) or not isinstance(row.get("op"), str):
            raise ValueError("Filters require field and op strings; raw SQL is not permitted")
        combined.append(MandatoryFilter(field=row["field"], op=row["op"], value=row.get("value")))
    try:
        comparison = ComparisonKind(changes.get("comparison", plan.get("comparison", "none")))
    except ValueError as exc:
        raise ValueError("comparison must be none, yoy or mom") from exc
    limit = changes.get("limit", plan.get("limit"))
    if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 1000):
        raise ValueError("limit must be 1..1000")
    return QueryIR(
        metric_id=ids[0], metric_ids=tuple(ids[1:]), dimensions=tuple(dims),
        filters=tuple(combined), time_values=tuple(times), comparison=comparison,
        order=str(changes.get("order", plan.get("order", ""))),
        order_metric_id=str(changes.get("orderMetricId", plan.get("orderMetricId", ""))),
        limit=limit,
    )
