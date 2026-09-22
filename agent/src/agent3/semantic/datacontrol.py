from __future__ import annotations

import json
import re
from typing import Any

import httpx

from agent3.contracts.authz import AuthzContext
from agent3.metadata.datacontrol_http import PortalMetadataError, PortalMetadataProvider
from agent3.semantic.models import Additivity, MandatoryFilter, MetricDefinition, MetricKind
from agent3.semantic.registry import SemanticRegistry

_SPLIT = re.compile(r"[,，;；|]+")


def _tokens(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(x).strip() for x in value if str(x).strip())
    return tuple(x.strip() for x in _SPLIT.split(str(value)) if x.strip())


def _mandatory_filters(value: Any) -> tuple[MandatoryFilter, ...]:
    if value is None or value == "":
        return ()
    payload = value
    if isinstance(value, str):
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return ()
    if not isinstance(payload, list):
        return ()
    filters: list[MandatoryFilter] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "").strip()
        op = str(item.get("op") or "eq").strip()
        if not field or "value" not in item:
            continue
        filters.append(MandatoryFilter(field=field, op=op, value=item.get("value")))
    return tuple(filters)


def load_portal_semantics(
    base_url: str,
    metadata: PortalMetadataProvider,
    *,
    client: httpx.Client | None = None,
) -> SemanticRegistry:
    # This is always a local Portal call in DataControl. Do not inherit shell
    # proxy settings for 127.0.0.1/localhost; desktop proxies can otherwise
    # return 502 for an otherwise healthy Portal.
    owned_client = client is None
    http = client or httpx.Client(timeout=10.0, trust_env=False)
    try:
        response = http.get(f"{base_url.rstrip('/')}/metrics")
        response.raise_for_status()
        payload = response.json()
        rows: Any = payload.get("data", []) if isinstance(payload, dict) else []
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        raise PortalMetadataError(f"Portal metric request failed: {exc}") from exc
    finally:
        if owned_client:
            http.close()

    authz = AuthzContext.system(purpose="portal-semantic-load")
    metrics: list[MetricDefinition] = []
    for row in rows if isinstance(rows, list) else []:
        source_id = row.get("sourceDatasetId")
        aggregation = row.get("aggregation")
        measure = row.get("measureColumn")
        code = row.get("metricCode")
        name = row.get("name")
        if not all((source_id, aggregation, measure, code, name)):
            continue
        table = metadata.get_table(authz, str(source_id))
        if table is None:
            continue
        raw_additivity = str(row.get("timeAdditivity") or "additive").casefold()
        additivity = (
            Additivity.NON_ADDITIVE
            if "non" in raw_additivity or "不可加" in raw_additivity
            else Additivity.ADDITIVE
        )
        raw_kind = str(row.get("metricKind") or "BASE").casefold()
        try:
            kind = MetricKind(raw_kind)
        except ValueError:
            kind = MetricKind.BASE
        metrics.append(
            MetricDefinition(
                id=str(code),
                name=str(name),
                aliases=_tokens(row.get("aliases")),
                aggregation=str(aggregation),
                measure=str(measure),
                source_entity=table.full_name,
                mandatory_filters=_mandatory_filters(row.get("mandatoryFilters")),
                additivity_time=additivity,
                valid_dimensions=_tokens(row.get("validDimensions")),
                time_field=str(row.get("timeField") or "dt"),
                owner=str(row.get("statSystemCode") or ""),
                caveats=str(row.get("caliber") or row.get("definition") or ""),
                kind=kind,
                numerator_metric_id=str(row.get("numeratorMetricCode") or ""),
                denominator_metric_id=str(row.get("denominatorMetricCode") or ""),
                formula=str(row.get("formula") or ""),
                time_grain=str(row.get("timeGrain") or ""),
                latest_strategy=str(row.get("latestStrategy") or "MAX"),
            )
        )
    return SemanticRegistry(tuple(metrics))
