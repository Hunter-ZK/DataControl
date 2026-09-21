from __future__ import annotations

import re
from typing import Any

import httpx

from agent3.contracts.authz import AuthzContext
from agent3.metadata.datacontrol_http import PortalMetadataProvider, PortalMetadataError
from agent3.semantic.models import Additivity, MetricDefinition
from agent3.semantic.registry import SemanticRegistry

_SPLIT = re.compile(r"[,，;；|]+")


def load_portal_semantics(base_url: str, metadata: PortalMetadataProvider, *, client: httpx.Client | None = None) -> SemanticRegistry:
    http = client or httpx.Client(timeout=10.0)
    try:
        response = http.get(f"{base_url.rstrip('/')}/metrics")
        response.raise_for_status()
        payload = response.json()
        rows: Any = payload.get("data", []) if isinstance(payload, dict) else []
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        raise PortalMetadataError(f"Portal metric request failed: {exc}") from exc
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
        aliases = tuple(x.strip() for x in _SPLIT.split(str(row.get("aliases") or "")) if x.strip())
        raw_additivity = str(row.get("timeAdditivity") or "additive").casefold()
        additivity = Additivity.NON_ADDITIVE if "non" in raw_additivity or "不可加" in raw_additivity else Additivity.ADDITIVE
        metrics.append(MetricDefinition(id=str(code), name=str(name), aliases=aliases, aggregation=str(aggregation), measure=str(measure), source_entity=table.full_name, additivity_time=additivity, caveats=str(row.get("caliber") or "")))
    return SemanticRegistry(tuple(metrics))
