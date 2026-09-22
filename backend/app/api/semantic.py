from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.assets import get_db
from backend.app.db.models import Column, Dataset, Metric

router = APIRouter(prefix="/api/v1/semantic", tags=["semantic"])


def _tokens(value: str | None) -> list[str]:
    if not value:
        return []
    normalized = value.replace("，", ",").replace(";", ",").replace("；", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _json_list(value: str | None) -> list[dict]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


@router.get("/metrics/{metric_code}")
def metric_semantic_detail(metric_code: str, db: Session = Depends(get_db)):
    metric = db.execute(
        select(Metric).where(Metric.metric_code == metric_code)
    ).scalar_one_or_none()
    if metric is None:
        raise HTTPException(404, "Metric not found")

    dataset = db.get(Dataset, metric.source_dataset_id)
    columns = db.execute(
        select(Column).where(Column.dataset_id == metric.source_dataset_id)
    ).scalars().all()
    column_map = {column.column_name: column for column in columns}
    dimensions = []
    for name in _tokens(metric.valid_dimensions):
        column = column_map.get(name)
        dimensions.append(
            {
                "name": name,
                "label": column.cn_name if column and column.cn_name else name,
                "dataType": column.data_type if column else None,
                "codeTableNo": column.code_table_no if column else None,
                "standardNo": column.standard_no if column else None,
            }
        )

    return {
        "code": "OK",
        "data": {
            "assetId": metric.asset_id,
            "metricCode": metric.metric_code,
            "name": metric.metric_name,
            "aliases": _tokens(metric.aliases),
            "definition": metric.biz_definition,
            "metricKind": metric.metric_kind,
            "aggregation": metric.aggregation,
            "measureColumn": metric.measure_column,
            "formula": metric.formula,
            "numeratorMetricCode": metric.numerator_metric_code,
            "denominatorMetricCode": metric.denominator_metric_code,
            "source": {
                "assetId": dataset.asset_id if dataset else metric.source_dataset_id,
                "name": dataset.biz_name if dataset else metric.source_dataset_id,
                "tableName": dataset.table_name if dataset else None,
                "layerCode": dataset.layer_code if dataset else None,
            },
            "time": {
                "field": metric.time_field,
                "grain": metric.time_grain,
                "additivity": metric.time_additivity,
                "latestStrategy": metric.latest_strategy,
            },
            "validDimensions": dimensions,
            "mandatoryFilters": _json_list(metric.mandatory_filters),
            "statSystemCode": metric.stat_system_code,
            "caliber": metric.caliber_desc,
            "semanticNotes": metric.semantic_notes,
            "status": metric.status,
            "researchPolicy": "internal_only",
        },
    }
