from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Column, Dataset, Metric
from backend.app.search.engine import SearchEngine


class SearchService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = SearchEngine()

    def _enrich(self, rows: list[dict]) -> list[dict]:
        table_ids = {row["asset_id"] for row in rows if row["asset_type"] == "TABLE"}
        column_ids = {row["asset_id"] for row in rows if row["asset_type"] == "COLUMN"}
        metric_ids = {row["asset_id"] for row in rows if row["asset_type"] == "METRIC"}

        columns = (
            self.db.execute(select(Column).where(Column.asset_id.in_(column_ids))).scalars().all()
            if column_ids
            else []
        )
        metrics = (
            self.db.execute(select(Metric).where(Metric.asset_id.in_(metric_ids))).scalars().all()
            if metric_ids
            else []
        )
        column_map = {item.asset_id: item for item in columns}
        metric_map = {item.asset_id: item for item in metrics}
        parent_ids = {item.dataset_id for item in columns}
        parent_ids.update(item.source_dataset_id for item in metrics)
        dataset_ids = table_ids | parent_ids
        datasets = (
            self.db.execute(select(Dataset).where(Dataset.asset_id.in_(dataset_ids))).scalars().all()
            if dataset_ids
            else []
        )
        dataset_map = {item.asset_id: item for item in datasets}

        enriched: list[dict] = []
        for row in rows:
            asset_type = row["asset_type"]
            context = {
                "assetId": row["asset_id"],
                "assetType": asset_type,
                "title": row["title"],
                "technicalName": row["technical_name"],
                "titleHighlight": row.get("title_hl") or row["title"],
                "technicalNameHighlight": row.get("technical_name_hl") or row["technical_name"],
                "snippet": row.get("snippet") or "",
                "score": row.get("score", 0),
                "catalogCode": None,
                "layerCode": None,
                "status": None,
                "parentAssetId": None,
            }
            if asset_type == "TABLE":
                ds = dataset_map.get(row["asset_id"])
                if ds:
                    context.update(
                        catalogCode=ds.catalog_code,
                        layerCode=ds.layer_code,
                        status=ds.status,
                    )
            elif asset_type == "COLUMN":
                column = column_map.get(row["asset_id"])
                if column:
                    ds = dataset_map.get(column.dataset_id)
                    context["parentAssetId"] = column.dataset_id
                    if ds:
                        context.update(
                            catalogCode=ds.catalog_code,
                            layerCode=ds.layer_code,
                            status=ds.status,
                        )
            elif asset_type == "METRIC":
                metric = metric_map.get(row["asset_id"])
                if metric:
                    ds = dataset_map.get(metric.source_dataset_id)
                    context["parentAssetId"] = metric.source_dataset_id
                    context["status"] = metric.status
                    if ds:
                        context.update(catalogCode=ds.catalog_code, layerCode=ds.layer_code)
            else:
                context["status"] = "EFFECTIVE"
            enriched.append(context)
        return enriched

    @staticmethod
    def _filter(
        item: dict,
        *,
        asset_types: set[str] | None = None,
        catalog: str | None = None,
        layer: str | None = None,
        status: str | None = None,
    ) -> bool:
        if asset_types and item.get("assetType") not in asset_types:
            return False
        if catalog and item.get("catalogCode") != catalog:
            return False
        if layer and item.get("layerCode") != layer:
            return False
        if status and item.get("status") != status:
            return False
        return True

    def search(
        self,
        query: str,
        *,
        asset_types: list[str] | None = None,
        catalog: str | None = None,
        layer: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        # Retrieve the complete literal match set so total/facets are exact. The
        # index handles textual narrowing/ranking; metadata filters stay grounded
        # in relational facts and are applied after one batched enrichment pass.
        raw = self.engine.search(query, limit=None)
        enriched = self._enrich(raw)
        type_filter = set(asset_types) if asset_types else None

        type_scope = [
            item
            for item in enriched
            if self._filter(item, catalog=catalog, layer=layer, status=status)
        ]
        typed_scope = [
            item
            for item in enriched
            if self._filter(item, asset_types=type_filter)
        ]
        layer_scope = [
            item
            for item in typed_scope
            if self._filter(item, catalog=catalog, status=status)
        ]
        catalog_scope = [
            item
            for item in typed_scope
            if self._filter(item, layer=layer, status=status)
        ]
        status_scope = [
            item
            for item in typed_scope
            if self._filter(item, catalog=catalog, layer=layer)
        ]
        filtered = [
            item
            for item in enriched
            if self._filter(
                item,
                asset_types=type_filter,
                catalog=catalog,
                layer=layer,
                status=status,
            )
        ]

        type_counts = Counter(item["assetType"] for item in type_scope)
        layer_counts = Counter(item["layerCode"] for item in layer_scope if item.get("layerCode"))
        catalog_counts = Counter(
            item["catalogCode"] for item in catalog_scope if item.get("catalogCode")
        )
        status_counts = Counter(item["status"] for item in status_scope if item.get("status"))

        return {
            "query": query,
            "total": len(filtered),
            "offset": offset,
            "limit": limit,
            "items": filtered[offset : offset + limit],
            "facets": {
                "assetTypes": dict(type_counts),
                "layers": dict(layer_counts),
                "catalogs": dict(catalog_counts),
                "statuses": dict(status_counts),
            },
        }

    def suggest(self, query: str, limit: int = 8) -> list[dict]:
        return [
            {
                "assetId": row["asset_id"],
                "assetType": row["asset_type"],
                "title": row["title"],
                "technicalName": row["technical_name"],
            }
            for row in self.engine.suggest(query, limit)
        ]

    def top_catalogs(self, limit: int = 8) -> list[dict]:
        rows = self.db.execute(select(Dataset.catalog_code)).scalars().all()
        counts = Counter(rows)
        return [{"catalogCode": code, "count": count} for code, count in counts.most_common(limit)]
