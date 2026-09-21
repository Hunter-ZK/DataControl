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

    def _context(self, row: dict) -> dict:
        asset_type = row["asset_type"]
        context: dict = {
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
            ds = self.db.get(Dataset, row["asset_id"])
            if ds:
                context.update(
                    catalogCode=ds.catalog_code,
                    layerCode=ds.layer_code,
                    status=ds.status,
                )
        elif asset_type == "COLUMN":
            column = self.db.get(Column, row["asset_id"])
            if column:
                ds = self.db.get(Dataset, column.dataset_id)
                context["parentAssetId"] = column.dataset_id
                if ds:
                    context.update(
                        catalogCode=ds.catalog_code,
                        layerCode=ds.layer_code,
                        status=ds.status,
                    )
        elif asset_type == "METRIC":
            metric = self.db.get(Metric, row["asset_id"])
            if metric:
                ds = self.db.get(Dataset, metric.source_dataset_id)
                context["parentAssetId"] = metric.source_dataset_id
                context["status"] = metric.status
                if ds:
                    context.update(catalogCode=ds.catalog_code, layerCode=ds.layer_code)
        else:
            # Reference assets expose status through their own APIs. Search keeps
            # filtering intentionally conservative rather than inventing catalog/layer.
            context["status"] = "EFFECTIVE"
        return context

    @staticmethod
    def _match_filters(item: dict, catalog: str | None, layer: str | None, status: str | None) -> bool:
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
        # Pull a bounded candidate window so facets describe the current query rather
        # than just one page. The index itself stays responsible for ranking.
        raw = self.engine.search(query, limit=500, asset_types=asset_types)
        enriched = [self._context(row) for row in raw]
        filtered = [x for x in enriched if self._match_filters(x, catalog, layer, status)]

        type_counts = Counter(x["assetType"] for x in filtered)
        layer_counts = Counter(x["layerCode"] for x in filtered if x.get("layerCode"))
        catalog_counts = Counter(x["catalogCode"] for x in filtered if x.get("catalogCode"))
        status_counts = Counter(x["status"] for x in filtered if x.get("status"))

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
