from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.api.assets import get_db
from backend.app.services.relations import RelationService

router = APIRouter(prefix="/api/v1/relations", tags=["relations"])


@router.get("/graph/{asset_id}")
def relation_graph(
    asset_id: str,
    depth: int = Query(2, ge=1, le=5),
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    max_nodes: int = Query(120, ge=10, le=500),
    db: Session = Depends(get_db),
):
    try:
        data = RelationService(db).graph(
            asset_id,
            depth=depth,
            direction=direction,
            max_nodes=max_nodes,
        )
    except KeyError:
        raise HTTPException(404, "Dataset not found") from None
    return {"code": "OK", "data": data}


@router.get("/columns/{column_id}")
def column_relation_graph(
    column_id: str,
    depth: int = Query(2, ge=1, le=5),
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    max_nodes: int = Query(120, ge=10, le=500),
    db: Session = Depends(get_db),
):
    try:
        data = RelationService(db).column_graph(
            column_id,
            depth=depth,
            direction=direction,
            max_nodes=max_nodes,
        )
    except KeyError:
        raise HTTPException(404, "Column not found") from None
    return {"code": "OK", "data": data}


@router.get("/fields/table/{dataset_id}")
def table_field_lineage(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    try:
        data = RelationService(db).table_field_lineage(dataset_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found") from None
    return {"code": "OK", "data": data}


@router.get("/path")
def relation_path(
    source: str,
    target: str,
    max_depth: int = Query(8, ge=1, le=12),
    db: Session = Depends(get_db),
):
    try:
        data = RelationService(db).path(source, target, max_depth=max_depth)
    except KeyError:
        raise HTTPException(404, "Source or target dataset not found") from None
    return {"code": "OK", "data": data}


@router.get("/impact/{asset_id}")
def relation_impact(
    asset_id: str,
    depth: int = Query(3, ge=1, le=5),
    max_nodes: int = Query(200, ge=10, le=500),
    db: Session = Depends(get_db),
):
    try:
        data = RelationService(db).impact(asset_id, depth=depth, max_nodes=max_nodes)
    except KeyError:
        raise HTTPException(404, "Dataset not found") from None
    return {"code": "OK", "data": data}
