from __future__ import annotations

from typing import Any

import httpx

from agent3.contracts.authz import AuthzContext
from agent3.metadata.models import ColumnMetadata, TableMetadata


class PortalMetadataError(RuntimeError):
    pass


class PortalMetadataProvider:
    """Read-only MetadataProvider backed by the local DataControl Portal API.

    This adapter preserves the architecture boundary: Agent3 never imports Portal
    database models and never opens the Portal database directly.
    """

    def __init__(self, base_url: str, *, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=10.0)

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        try:
            response = self._client.get(f"{self.base_url}{path}", params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PortalMetadataError(f"Portal metadata request failed: {path}: {exc}") from exc
        if not isinstance(payload, dict) or "data" not in payload:
            raise PortalMetadataError(f"Portal metadata response is invalid: {path}")
        return payload["data"]

    @staticmethod
    def _brief(row: dict[str, Any]) -> TableMetadata:
        return TableMetadata(
            full_name=str(row.get("tableName") or row.get("assetId") or ""),
            aliases=tuple(x for x in (row.get("bizName"),) if x),
        )

    @staticmethod
    def _detail(row: dict[str, Any]) -> TableMetadata:
        columns = tuple(
            ColumnMetadata(
                name=str(item.get("columnName") or ""),
                data_type=str(item.get("dataType") or "unknown"),
                description=str(item.get("bizDefinition") or item.get("cnName") or ""),
            )
            for item in row.get("columns", [])
            if item.get("columnName")
        )
        description = str(row.get("bizDefinition") or row.get("statCaliber") or "")
        return TableMetadata(
            full_name=str(row.get("tableName") or row.get("assetId") or ""),
            description=description,
            columns=columns,
            partition_fields=(),
            row_count_estimate=row.get("rowCount"),
            aliases=tuple(x for x in (row.get("bizName"),) if x),
        )

    def all_tables(self, authz: AuthzContext) -> tuple[TableMetadata, ...]:
        _ = authz
        rows = self._get("/tables", params={"limit": 200})
        return tuple(self._brief(row) for row in rows)

    def search_tables(self, authz: AuthzContext, query: str, *, limit: int = 8) -> tuple[TableMetadata, ...]:
        _ = authz
        rows = self._get("/tables", params={"keyword": query, "limit": min(max(limit, 1), 200)})
        return tuple(self._brief(row) for row in rows[:limit])

    def get_table(self, authz: AuthzContext, full_name: str) -> TableMetadata | None:
        _ = authz
        # Stable asset IDs can be resolved directly. Physical names are resolved
        # through the Portal search API and then dereferenced by stable asset_id.
        if full_name.upper().startswith("DS"):
            candidates = [{"assetId": full_name, "tableName": full_name}]
        else:
            candidates = self._get("/tables", params={"keyword": full_name, "limit": 200})
        folded = full_name.casefold()
        selected = None
        for row in candidates:
            table_name = str(row.get("tableName") or "")
            if table_name.casefold() == folded or table_name.rsplit(".", 1)[-1].casefold() == folded:
                selected = row
                break
        if selected is None and len(candidates) == 1:
            selected = candidates[0]
        if selected is None:
            return None
        asset_id = selected.get("assetId")
        if not asset_id:
            return None
        try:
            detail = self._get(f"/tables/{asset_id}")
        except PortalMetadataError as exc:
            if "404" in str(exc):
                return None
            raise
        return self._detail(detail)
