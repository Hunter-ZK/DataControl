from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.db.session import SessionLocal
from backend.app.repositories.assets import AssetRepository
from backend.app.services.assets import AssetService

router = APIRouter(prefix="/api/v1", tags=["assets"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/tables")
def list_tables(limit: int = Query(50, ge=1, le=200), keyword: str | None = None, db: Session = Depends(get_db)):
    return {"code": "OK", "data": AssetService(AssetRepository(db)).list_datasets(limit, keyword)}

@router.get("/tables/{asset_id}")
def get_table(asset_id: str, db: Session = Depends(get_db)):
    data = AssetService(AssetRepository(db)).get_dataset(asset_id)
    if data is None:
        raise HTTPException(404, "Asset not found")
    return {"code": "OK", "data": data}
