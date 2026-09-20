from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from backend.app.db.models import Dataset

class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_datasets(self, limit: int = 50, keyword: str | None = None) -> list[Dataset]:
        q = select(Dataset).order_by(Dataset.is_common.desc(), Dataset.updated_at.desc()).limit(limit)
        if keyword:
            needle = f"%{keyword}%"
            q = q.where((Dataset.biz_name.like(needle)) | (Dataset.table_name.like(needle)))
        return list(self.db.scalars(q).all())

    def get_dataset(self, asset_id: str) -> Dataset | None:
        q = select(Dataset).options(selectinload(Dataset.columns)).where(Dataset.asset_id == asset_id)
        return self.db.scalar(q)
