"""Bounded read-only asset facts for the deterministic Agent3 MCP tools.

Identifiers are looked up by primary key, not interpolated into SQL or URLs.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.api.assets import get_db
from backend.app.db.models import (
    CodeTable, Column, DataStandard, Dataset, Metric, StatisticalSystem,
    TableLineage, WordRoot,
)

router = APIRouter(prefix="/api/v1/agent-assets", tags=["agent-assets"])

ASSET_MODELS = {
    "TABLE": Dataset, "COLUMN": Column, "METRIC": Metric,
    "CODE_TABLE": CodeTable, "STANDARD": DataStandard,
    "WORD_ROOT": WordRoot, "STAT_SYSTEM": StatisticalSystem,
}
LABEL_FIELDS = {
    "TABLE": ("biz_name", "table_name", "biz_definition"),
    "COLUMN": ("cn_name", "column_name", "biz_definition"),
    "METRIC": ("metric_name", "metric_code", "biz_definition"),
    "CODE_TABLE": ("code_table_name", "code_table_no", "description"),
    "STANDARD": ("standard_name", "standard_no", "business_definition"),
    "WORD_ROOT": ("cn_name", "root_en", "description"),
    "STAT_SYSTEM": ("stat_system_name", "stat_system_code", "document_no"),
}
DETAIL_FIELDS = {
    "TABLE": ("layer_code", "grain", "update_freq", "status", "stat_caliber"),
    "COLUMN": ("dataset_id", "data_type", "code_table_no", "standard_no"),
    "METRIC": ("source_dataset_id", "aggregation", "measure_column", "time_field",
               "time_additivity", "valid_dimensions", "stat_system_code", "caliber_desc"),
    "CODE_TABLE": ("version", "status"),
    "STANDARD": ("code_table_no", "status"),
    "WORD_ROOT": ("en_full", "synonyms", "status"),
    "STAT_SYSTEM": ("version", "issuer", "status"),
}


def _asset(db: Session, asset_type: str, asset_id: str):
    model = ASSET_MODELS.get(asset_type.upper())
    if model is None:
        raise HTTPException(422, "Unsupported asset type")
    item = db.get(model, asset_id)
    if item is None:
        raise HTTPException(404, "Asset not found")
    return item


@router.get("/references")
def references(
    asset_type: str, asset_id: str, limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    item = _asset(db, asset_type, asset_id)
    category = asset_type.upper()
    stmt = None
    if category == "CODE_TABLE":
        stmt = select(Column).where(Column.code_table_no == item.code_table_no)
    elif category == "STANDARD":
        stmt = select(Column).where(Column.standard_no == item.standard_no)
    elif category == "STAT_SYSTEM":
        stmt = select(Metric).where(Metric.stat_system_code == item.stat_system_code)
    else:
        return {"code": "OK", "data": {"assetId": asset_id, "references": [],
                                       "status": "unsupported_relationship"}}
    rows = db.execute(stmt.limit(limit)).scalars().all()
    result_type = "METRIC" if category == "STAT_SYSTEM" else "COLUMN"
    return {"code": "OK", "data": {
        "assetId": asset_id, "status": "complete",
        "references": [{
            "assetId": row.asset_id, "assetType": result_type,
            "title": row.metric_name if result_type == "METRIC" else row.cn_name or row.column_name,
        } for row in rows],
    }}


@router.get("/lineage/{asset_type}/{asset_id}")
def lineage(asset_type: str, asset_id: str, depth: int = Query(1, ge=1, le=3),
            db: Session = Depends(get_db)):
    if asset_type.upper() not in ("TABLE", "COLUMN"):
        raise HTTPException(422, "Only datasets or columns support lineage")
    item = _asset(db, asset_type, asset_id)
    if asset_type.upper() == "COLUMN":
        from backend.app.services.relations import RelationService
        result = RelationService(db).column_graph(asset_id, depth=depth, max_nodes=80)
        return {"code": "OK", "data": {"assetId": asset_id, "assetType": "COLUMN",
                                       "graph": result}}
    frontier = {item.asset_id}
    visited = {item.asset_id}
    edges = []
    for _ in range(depth):
        if not frontier:
            break
        rows = db.execute(select(TableLineage).where(or_(
            TableLineage.src_asset_id.in_(frontier),
            TableLineage.dst_asset_id.in_(frontier),
        )).limit(160)).scalars().all()
        nxt = set()
        for edge in rows:
            record = {"srcAssetId": edge.src_asset_id, "dstAssetId": edge.dst_asset_id,
                      "taskName": edge.task_name, "evidence": edge.evidence}
            if record not in edges:
                edges.append(record)
            nxt.update([edge.src_asset_id, edge.dst_asset_id])
        frontier = nxt - visited
        visited |= nxt
    return {"code": "OK", "data": {"assetId": asset_id, "assetType": "TABLE",
                                   "edges": edges[:160], "nodes": sorted(visited)}}


@router.get("/{asset_type}/{asset_id}")
def get_agent_asset(asset_type: str, asset_id: str, db: Session = Depends(get_db)):
    category = asset_type.upper()
    item = _asset(db, category, asset_id)
    title_field, technical_field, definition_field = LABEL_FIELDS[category]
    detail = {field: getattr(item, field, None) for field in DETAIL_FIELDS[category]}
    return {"code": "OK", "data": {
        "assetId": item.asset_id, "assetType": category,
        "title": getattr(item, title_field) or getattr(item, technical_field),
        "technicalName": getattr(item, technical_field),
        "definition": getattr(item, definition_field) or "",
        "details": detail,
    }}
