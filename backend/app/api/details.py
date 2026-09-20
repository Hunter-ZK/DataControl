from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.api.assets import get_db
from backend.app.db.models import ChangeLog, Column, CommonSql, CommonSqlDataset, Dataset, DatasetTag, Tag

router = APIRouter(prefix="/api/v1", tags=["asset-details"])


def _column_payload(x: Column) -> dict:
    return {
        "assetId": x.asset_id,
        "datasetId": x.dataset_id,
        "columnName": x.column_name,
        "cnName": x.cn_name,
        "dataType": x.data_type,
        "ordinalNo": x.ordinal_no,
        "bizDefinition": x.biz_definition,
        "unit": x.unit,
        "codeTableNo": x.code_table_no,
        "standardNo": x.standard_no,
    }


@router.get("/columns")
def columns(
    dataset_id: str | None = None,
    keyword: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(Column)
    if dataset_id:
        stmt = stmt.where(Column.dataset_id == dataset_id)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Column.column_name.like(like), Column.cn_name.like(like), Column.biz_definition.like(like)))
    rows = db.execute(stmt.order_by(Column.dataset_id, Column.ordinal_no).limit(limit)).scalars().all()
    return {"code": "OK", "data": [_column_payload(x) for x in rows]}


@router.get("/columns/{asset_id}")
def column_detail(asset_id: str, db: Session = Depends(get_db)):
    row = db.get(Column, asset_id)
    if row is None:
        raise HTTPException(404, "Column not found")
    return {"code": "OK", "data": _column_payload(row)}


@router.get("/tables/{asset_id}/tags")
def table_tags(asset_id: str, db: Session = Depends(get_db)):
    if db.get(Dataset, asset_id) is None:
        raise HTTPException(404, "Dataset not found")
    rows = db.execute(
        select(Tag)
        .join(DatasetTag, DatasetTag.tag_code == Tag.tag_code)
        .where(DatasetTag.dataset_id == asset_id)
        .order_by(Tag.tag_group, Tag.tag_name)
    ).scalars().all()
    return {"code": "OK", "data": [{"code": x.tag_code, "name": x.tag_name, "group": x.tag_group} for x in rows]}


@router.get("/tables/{asset_id}/changes")
def table_changes(asset_id: str, limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db)):
    if db.get(Dataset, asset_id) is None:
        raise HTTPException(404, "Dataset not found")
    rows = db.execute(select(ChangeLog).where(ChangeLog.dataset_id == asset_id).order_by(ChangeLog.change_date.desc()).limit(limit)).scalars().all()
    return {
        "code": "OK",
        "data": [
            {
                "id": x.id,
                "changeDate": x.change_date,
                "changeType": x.change_type,
                "content": x.content,
                "changedBy": x.changed_by,
            }
            for x in rows
        ],
    }


@router.get("/tables/{asset_id}/common-sql")
def table_common_sql(asset_id: str, db: Session = Depends(get_db)):
    if db.get(Dataset, asset_id) is None:
        raise HTTPException(404, "Dataset not found")
    rows = db.execute(
        select(CommonSql)
        .join(CommonSqlDataset, CommonSqlDataset.sql_code == CommonSql.sql_code)
        .where(CommonSqlDataset.dataset_id == asset_id, CommonSql.status == "VALID")
        .order_by(CommonSql.sql_code)
    ).scalars().all()
    return {
        "code": "OK",
        "data": [
            {
                "sqlCode": x.sql_code,
                "title": x.title,
                "question": x.question,
                "sqlText": x.sql_text,
                "dialect": x.dialect,
                "description": x.description,
            }
            for x in rows
        ],
    }
