from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models import Dataset


class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _conditions(
        keyword: str | None = None,
        catalog: str | None = None,
        layer: str | None = None,
        status: str | None = None,
    ) -> list:
        conditions = []
        if keyword:
            needle = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    Dataset.biz_name.like(needle),
                    Dataset.table_name.like(needle),
                    Dataset.biz_definition.like(needle),
                )
            )
        if catalog:
            conditions.append(Dataset.catalog_code == catalog)
        if layer:
            conditions.append(Dataset.layer_code == layer)
        if status:
            conditions.append(Dataset.status == status)
        return conditions

    def list_datasets(
        self,
        limit: int = 50,
        keyword: str | None = None,
        *,
        offset: int = 0,
        catalog: str | None = None,
        layer: str | None = None,
        status: str | None = None,
    ) -> list[Dataset]:
        conditions = self._conditions(keyword, catalog, layer, status)
        query = select(Dataset)
        if conditions:
            query = query.where(*conditions)
        query = (
            query.order_by(
                Dataset.is_common.desc(),
                Dataset.updated_at.desc(),
                Dataset.asset_id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(query).all())

    def count_datasets(
        self,
        keyword: str | None = None,
        *,
        catalog: str | None = None,
        layer: str | None = None,
        status: str | None = None,
    ) -> int:
        conditions = self._conditions(keyword, catalog, layer, status)
        query = select(func.count()).select_from(Dataset)
        if conditions:
            query = query.where(*conditions)
        return int(self.db.scalar(query) or 0)

    def get_dataset(self, asset_id: str) -> Dataset | None:
        query = (
            select(Dataset)
            .options(selectinload(Dataset.columns))
            .where(Dataset.asset_id == asset_id)
        )
        return self.db.scalar(query)
