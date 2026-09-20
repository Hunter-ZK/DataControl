from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.assets import get_db
from backend.app.search.service import SearchService

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(min_length=1),
    asset_type: list[str] | None = Query(default=None),
    catalog: str | None = None,
    layer: str | None = None,
    status: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    data = SearchService(db).search(
        q,
        asset_types=asset_type,
        catalog=catalog,
        layer=layer,
        status=status,
        offset=offset,
        limit=limit,
    )
    return {"code": "OK", "data": data}


@router.get("/suggest")
def suggest(
    q: str = Query(min_length=1),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return {"code": "OK", "data": SearchService(db).suggest(q, limit)}
