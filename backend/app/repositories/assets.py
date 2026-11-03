from sqlalchemy import func, select
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

    def page_datasets(
        self, *, limit: int, offset: int, keyword: str | None = None,
        catalog_code: str | None = None, layer_code: str | None = None,
        status: str | None = "ONLINE",
    ) -> tuple[list[Dataset], int]:
        filters = []
        if keyword:
            needle = f"%{keyword}%"
            filters.append((Dataset.biz_name.like(needle)) | (Dataset.table_name.like(needle)))
        if catalog_code:
            filters.append(Dataset.catalog_code == catalog_code)
        if layer_code:
            filters.append(Dataset.layer_code == layer_code)
        if status and status != "ALL":
            filters.append(Dataset.status == status)
        total = self.db.scalar(select(func.count()).select_from(Dataset).where(*filters)) or 0
        stmt = (
            select(Dataset).where(*filters)
            .order_by(Dataset.is_common.desc(), Dataset.updated_at.desc(), Dataset.asset_id)
            .limit(limit).offset(offset)
        )
        return list(self.db.scalars(stmt).all()), total
