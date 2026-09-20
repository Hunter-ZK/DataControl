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

    def get_dataset(self, asset_id):
        row = self.repo.get_dataset(asset_id)
        if not row:
            return None
        data = self._brief(row)
        data.update({
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
                {"assetId": c.asset_id, "columnName": c.column_name, "ordinalNo": c.ordinal_no,
                 "cnName": c.cn_name, "dataType": c.data_type, "bizDefinition": c.biz_definition,
                 "unit": c.unit, "standardNo": c.standard_no, "codeTableNo": c.code_table_no}
                for c in row.columns
            ],
        })
        return data
