from __future__ import annotations

import re
from typing import Any

import httpx

from agent3.contracts.authz import AuthzContext
from agent3.metadata.models import CodeValueMetadata, ColumnMetadata, TableMetadata


class PortalMetadataError(RuntimeError):
    pass


_TIME_WORDS = re.compile(r"(?:本期|当期|当前|现在|最新(?:一期)?|最近一期|期末|本月|当月|上期|上一期|上月)")
_QUERY_WORDS = re.compile(r"(?:请|帮我|帮忙|查询|查一下|统计|生成|看看|看一下)")


def _search_phrase(value: str) -> str:
    cleaned = _QUERY_WORDS.sub("", value)
    cleaned = _TIME_WORDS.sub("", cleaned)
    return cleaned.strip(" ，,。；;：:") or value.strip()


class PortalMetadataProvider:
    """Read-only MetadataProvider backed by the local DataControl Portal API.

    The Portal endpoint is a loopback-only product boundary. Local HTTP calls must
    never inherit HTTP(S)_PROXY/ALL_PROXY from the developer shell, otherwise a
    desktop proxy can turn a healthy 127.0.0.1 request into a misleading 502.
    """

    def __init__(self, base_url: str, *, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=10.0, trust_env=False)

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
            full_name=str(row.get("tableName") or row.get("technicalName") or row.get("assetId") or ""),
            description=str(row.get("bizDefinition") or row.get("snippet") or ""),
            aliases=tuple(value for value in (row.get("bizName"), row.get("title")) if value),
        )

    @staticmethod
    def _detail(row: dict[str, Any]) -> TableMetadata:
        columns = tuple(
            ColumnMetadata(
                name=str(item.get("columnName") or ""),
                data_type=str(item.get("dataType") or "unknown"),
                description=str(item.get("bizDefinition") or item.get("cnName") or ""),
                code_table_no=str(item.get("codeTableNo") or ""),
                standard_no=str(item.get("standardNo") or ""),
            )
            for item in row.get("columns", [])
            if item.get("columnName")
        )
        description = "；".join(
            value
            for value in (
                str(row.get("bizDefinition") or "").strip(),
                str(row.get("statCaliber") or "").strip(),
                str(row.get("usageNotes") or "").strip(),
            )
            if value
        )
        return TableMetadata(
            full_name=str(row.get("tableName") or row.get("assetId") or ""),
            description=description,
            columns=columns,
            partition_fields=(),
            row_count_estimate=row.get("rowCount"),
            aliases=tuple(value for value in (row.get("bizName"),) if value),
        )

    def word_roots(self, authz: AuthzContext) -> set[str]:
        _ = authz
        rows = self._get("/word-roots")
        return {str(item.get("root") or "").casefold()
                for item in rows if isinstance(item, dict) and item.get("root")}

    def search_assets(self, authz: AuthzContext, query: str, *, limit: int = 12) -> dict[str, Any]:
        _ = authz
        data = self._get("/search", params={"q": _search_phrase(query), "limit": max(1, min(limit, 40))})
        items = data.get("items", []) if isinstance(data, dict) else []
        return {"assets": [
            {key: row.get(key) for key in ("assetId", "assetType", "title",
             "technicalName", "snippet", "parentAssetId", "score")}
            for row in items if isinstance(row, dict) and row.get("assetId") and row.get("assetType")
        ], "total": data.get("total", 0) if isinstance(data, dict) else 0,
            "researchPolicy": "internal_only"}

    def get_asset(self, authz: AuthzContext, asset_type: str, asset_id: str) -> dict[str, Any]:
        _ = authz
        if asset_type not in {"TABLE", "COLUMN", "METRIC", "CODE_TABLE", "STANDARD", "WORD_ROOT", "STAT_SYSTEM"}:
            raise ValueError("Unsupported asset type")
        if not re.fullmatch(r"[A-Za-z0-9_-]{2,40}", asset_id):
            raise ValueError("Invalid asset ID")
        return self._get(f"/agent-assets/{asset_type}/{asset_id}")

    def find_references(self, authz: AuthzContext, asset_type: str, asset_id: str) -> dict[str, Any]:
        _ = authz
        if not re.fullmatch(r"[A-Za-z0-9_-]{2,40}", asset_id):
            raise ValueError("Invalid asset ID")
        return self._get("/agent-assets/references", params={"asset_type": asset_type,
                                                              "asset_id": asset_id})

    def get_lineage_summary(self, authz: AuthzContext, asset_type: str, asset_id: str,
                            *, depth: int = 1) -> dict[str, Any]:
        _ = authz
        if asset_type not in ("TABLE", "COLUMN") or not re.fullmatch(r"[A-Za-z0-9_-]{2,40}", asset_id):
            raise ValueError("Invalid lineage asset")
        return self._get(f"/agent-assets/lineage/{asset_type}/{asset_id}",
                         params={"depth": max(1, min(depth, 3))})

    def all_tables(self, authz: AuthzContext) -> tuple[TableMetadata, ...]:
        _ = authz
        rows = self._get("/tables", params={"limit": 200})
        return tuple(self._brief(row) for row in rows)

    def search_tables(
        self,
        authz: AuthzContext,
        query: str,
        *,
        limit: int = 8,
    ) -> tuple[TableMetadata, ...]:
        _ = authz
        phrase = _search_phrase(query)
        try:
            result = self._get(
                "/search",
                params={"q": phrase, "asset_type": "TABLE", "limit": max(limit * 3, 20)},
            )
            items = result.get("items", []) if isinstance(result, dict) else []
            rows = [item for item in items if item.get("assetType") == "TABLE"]
        except PortalMetadataError:
            rows = []
        if not rows:
            rows = self._get(
                "/tables",
                params={"keyword": phrase, "limit": min(max(limit * 3, 20), 200)},
            )
        return tuple(self._brief(row) for row in rows[:limit])

    def get_table(self, authz: AuthzContext, full_name: str) -> TableMetadata | None:
        _ = authz
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

    def resolve_code_values(
        self,
        authz: AuthzContext,
        code_table_no: str,
        query: str,
        *,
        limit: int = 8,
    ) -> tuple[CodeValueMetadata, ...]:
        _ = authz
        detail = self._get(f"/code-tables/{code_table_no}")
        values = detail.get("values", []) if isinstance(detail, dict) else []
        needle = query.strip().casefold()
        ranked: list[tuple[int, CodeValueMetadata]] = []
        for row in values if isinstance(values, list) else []:
            value = str(row.get("value") or "")
            name = str(row.get("name") or "")
            description = str(row.get("description") or "")
            if not value:
                continue
            if not needle:
                score = 1
            elif value.casefold() == needle or name.casefold() == needle:
                score = 100
            elif needle in name.casefold() or needle in description.casefold():
                score = 10
            else:
                continue
            ranked.append(
                (
                    score,
                    CodeValueMetadata(
                        code_table_no=code_table_no,
                        value=value,
                        name=name or value,
                        description=description,
                    ),
                )
            )
        ranked.sort(key=lambda item: (-item[0], item[1].value))
        return tuple(item for _, item in ranked[: max(1, limit)])
