from __future__ import annotations

from backend.app.repositories.assets import AssetRepository


class AssetService:
    def __init__(self, repo: AssetRepository):
        self.repo = repo

    @staticmethod
    def _brief(row):
        return {
            "assetId": row.asset_id,
            "tableName": row.table_name,
            "bizName": row.biz_name,
            "layerCode": row.layer_code,
            "workspaceCode": row.workspace_code,
            "catalogCode": row.catalog_code,
            "status": row.status,
            "isCommon": row.is_common,
            "techOwner": row.tech_owner,
            "updateFreq": row.update_freq,
            "dataUpdatedAt": row.data_updated_at.isoformat() if row.data_updated_at else None,
        }

    def list_datasets(self, limit=50, keyword=None):
        return [self._brief(x) for x in self.repo.list_datasets(limit, keyword)]

    def page_datasets(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        keyword: str | None = None,
        catalog: str | None = None,
        layer: str | None = None,
        status: str | None = None,
    ) -> dict:
        rows = self.repo.list_datasets(
            limit,
            keyword,
            offset=offset,
            catalog=catalog,
            layer=layer,
            status=status,
        )
        total = self.repo.count_datasets(
            keyword,
            catalog=catalog,
            layer=layer,
            status=status,
        )
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": [self._brief(row) for row in rows],
        }

    def get_dataset(self, asset_id):
        row = self.repo.get_dataset(asset_id)
        if not row:
            return None
        data = self._brief(row)
        data.update(
            {
                "bizDefinition": row.biz_definition,
                "statCaliber": row.stat_caliber,
                "dataSourceDesc": row.data_source_desc,
                "grain": row.grain,
                "usageNotes": row.usage_notes,
                "bizOwner": row.biz_owner,
                "ownerDept": row.owner_dept,
                "scheduleDesc": row.schedule_desc,
                "scheduleNode": row.schedule_node,
                "storageBytes": row.storage_bytes,
                "rowCount": row.row_count,
                "columns": [
                    {
                        "assetId": column.asset_id,
                        "columnName": column.column_name,
                        "ordinalNo": column.ordinal_no,
                        "cnName": column.cn_name,
                        "dataType": column.data_type,
                        "bizDefinition": column.biz_definition,
                        "unit": column.unit,
                        "standardNo": column.standard_no,
                        "codeTableNo": column.code_table_no,
                    }
                    for column in row.columns
                ],
            }
        )
        return data
