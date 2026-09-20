from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.api.assets import get_db
from backend.app.api.auth import get_current_user, get_optional_user
from backend.app.db.application_models import AuditLog, SearchHistory
from backend.app.db.models import Dataset, Favorite, User, ViewLog

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])


class AssetRef(BaseModel):
    assetType: str
    assetId: str


class SearchHistoryRequest(BaseModel):
    keyword: str


def _dataset_payload(db: Session, asset_id: str):
    row = db.get(Dataset, asset_id)
    if row is None:
        return {"assetId": asset_id, "bizName": asset_id, "tableName": None}
    return {"assetId": row.asset_id, "bizName": row.biz_name, "tableName": row.table_name, "layerCode": row.layer_code}


@router.get("/favorites")
def list_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Favorite).where(Favorite.user_id == user.id).order_by(Favorite.created_at.desc())).scalars().all()
    data = []
    for row in rows:
        asset = _dataset_payload(db, row.asset_id) if row.asset_type == "TABLE" else {"assetId": row.asset_id}
        data.append({"assetType": row.asset_type, "createdAt": row.created_at, **asset})
    return {"code": "OK", "data": data}


@router.post("/favorites")
def add_favorite(body: AssetRef, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exists = db.get(Favorite, (user.id, body.assetType, body.assetId))
    if exists is None:
        db.add(Favorite(user_id=user.id, asset_type=body.assetType, asset_id=body.assetId))
        db.add(AuditLog(user_id=user.id, action="FAVORITE_ADD", target_type=body.assetType, target_id=body.assetId))
        db.commit()
    return {"code": "OK", "data": {"favorited": True}}


@router.delete("/favorites/{asset_type}/{asset_id}")
def remove_favorite(asset_type: str, asset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(delete(Favorite).where(Favorite.user_id == user.id, Favorite.asset_type == asset_type, Favorite.asset_id == asset_id))
    db.add(AuditLog(user_id=user.id, action="FAVORITE_REMOVE", target_type=asset_type, target_id=asset_id))
    db.commit()
    return {"code": "OK", "data": {"favorited": False}}


@router.post("/views")
def record_view(body: AssetRef, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    user_id = user.id if user else None
    db.add(ViewLog(user_id=user_id, asset_type=body.assetType, asset_id=body.assetId, viewed_at=datetime.utcnow()))
    db.add(AuditLog(user_id=user_id, action="VIEW_ASSET", target_type=body.assetType, target_id=body.assetId))
    db.commit()
    return {"code": "OK", "data": {"recorded": True}}


@router.get("/recent-views")
def recent_views(limit: int = 12, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if limit < 1 or limit > 50:
        raise HTTPException(400, "limit must be between 1 and 50")
    rows = db.execute(select(ViewLog).where(ViewLog.user_id == user.id).order_by(ViewLog.viewed_at.desc()).limit(limit)).scalars().all()
    return {"code": "OK", "data": [{"assetType": x.asset_type, "viewedAt": x.viewed_at, **(_dataset_payload(db, x.asset_id) if x.asset_type == "TABLE" else {"assetId": x.asset_id})} for x in rows]}


@router.post("/search-history")
def record_search(body: SearchHistoryRequest, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    keyword = body.keyword.strip()
    if not keyword:
        raise HTTPException(400, "keyword is required")
    user_id = user.id if user else None
    db.add(SearchHistory(user_id=user_id, keyword=keyword))
    db.add(AuditLog(user_id=user_id, action="SEARCH", target_type="SEARCH", target_id=keyword[:64]))
    db.commit()
    return {"code": "OK", "data": {"recorded": True}}


@router.get("/search-history")
def search_history(limit: int = 20, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(SearchHistory).where(SearchHistory.user_id == user.id).order_by(SearchHistory.searched_at.desc()).limit(min(max(limit, 1), 100))).scalars().all()
    return {"code": "OK", "data": [{"keyword": x.keyword, "searchedAt": x.searched_at} for x in rows]}


@router.get("/audit")
def audit(limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "ADMIN":
        raise HTTPException(403, "Admin role required")
    rows = db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(max(limit, 1), 200))).scalars().all()
    return {"code": "OK", "data": [{"id": x.id, "userId": x.user_id, "action": x.action, "targetType": x.target_type, "targetId": x.target_id, "detail": x.detail, "createdAt": x.created_at} for x in rows]}
