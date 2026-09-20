from fastapi import APIRouter, Query
from backend.app.search.engine import SearchEngine

router = APIRouter(prefix="/api/v1/search", tags=["search"])

@router.get("")
def search(q: str = Query(min_length=1), limit: int = Query(20, ge=1, le=100)):
    return {"code": "OK", "data": SearchEngine().search(q, limit)}
