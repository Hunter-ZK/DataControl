from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.api.assets import get_db
from backend.app.db.models import (
    Catalog,
    CodeTable,
    CodeValue,
    Column,
    DataStandard,
    Dataset,
    Metric,
    StatisticalSystem,
    TableLineage,
    WordRoot,
)

router = APIRouter(prefix="/api/v1", tags=["reference"])


@router.get("/home/overview")
def home_overview(db: Session = Depends(get_db)):
    layer_rows = db.execute(
        select(Dataset.layer_code, func.count()).where(Dataset.status != "OFFLINE").group_by(Dataset.layer_code)
    ).all()
    catalog_rows = db.execute(
        select(Catalog.catalog_code, Catalog.catalog_name, func.count(Dataset.asset_id))
        .join(Dataset, Dataset.catalog_code == Catalog.catalog_code, isouter=True)
        .group_by(Catalog.catalog_code, Catalog.catalog_name)
        .order_by(func.count(Dataset.asset_id).desc())
        .limit(8)
    ).all()
    return {
        "code": "OK",
        "data": {
            "tableCount": db.scalar(select(func.count()).select_from(Dataset)) or 0,
            "columnCount": db.scalar(select(func.count()).select_from(Column)) or 0,
            "metricCount": db.scalar(select(func.count()).select_from(Metric)) or 0,
            "codeTableCount": db.scalar(select(func.count()).select_from(CodeTable)) or 0,
            "standardCount": db.scalar(select(func.count()).select_from(DataStandard)) or 0,
            "wordRootCount": db.scalar(select(func.count()).select_from(WordRoot)) or 0,
            "statSystemCount": db.scalar(select(func.count()).select_from(StatisticalSystem)) or 0,
            "layers": [{"layerCode": code, "tableCount": count} for code, count in layer_rows],
            "topCatalogs": [{"code": code, "name": name, "tableCount": count} for code, name, count in catalog_rows],
        },
    }


@router.get("/catalogs")
def catalogs(db: Session = Depends(get_db)):
    rows = db.execute(select(Catalog).order_by(Catalog.catalog_code)).scalars().all()
    return {"code": "OK", "data": [{"code": x.catalog_code, "parentCode": x.parent_code, "name": x.catalog_name, "description": x.description} for x in rows]}


@router.get("/code-tables")
def code_tables(keyword: str | None = None, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    stmt = select(CodeTable)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(CodeTable.code_table_no.like(like), CodeTable.code_table_name.like(like)))
    rows = db.execute(stmt.order_by(CodeTable.code_table_no).limit(limit)).scalars().all()
    return {"code": "OK", "data": [{"assetId": x.asset_id, "codeTableNo": x.code_table_no, "name": x.code_table_name, "version": x.version, "status": x.status, "description": x.description} for x in rows]}


@router.get("/code-tables/{code_table_no}")
def code_table_detail(code_table_no: str, db: Session = Depends(get_db)):
    row = db.execute(select(CodeTable).where(CodeTable.code_table_no == code_table_no)).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Code table not found")
    values = db.execute(select(CodeValue).where(CodeValue.code_table_no == code_table_no).order_by(CodeValue.id)).scalars().all()
    return {"code": "OK", "data": {"assetId": row.asset_id, "codeTableNo": row.code_table_no, "name": row.code_table_name, "description": row.description, "status": row.status, "values": [{"value": v.code_value, "name": v.code_name, "description": v.description} for v in values]}}


@router.get("/data-standards")
def data_standards(keyword: str | None = None, db: Session = Depends(get_db)):
    stmt = select(DataStandard)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(DataStandard.standard_no.like(like), DataStandard.standard_name.like(like)))
    rows = db.execute(stmt.order_by(DataStandard.standard_no)).scalars().all()
    return {"code": "OK", "data": [{"assetId": x.asset_id, "standardNo": x.standard_no, "name": x.standard_name, "definition": x.business_definition, "codeTableNo": x.code_table_no, "status": x.status} for x in rows]}


@router.get("/word-roots")
def word_roots(keyword: str | None = None, db: Session = Depends(get_db)):
    stmt = select(WordRoot)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(WordRoot.root_en.like(like), WordRoot.cn_name.like(like), WordRoot.synonyms.like(like)))
    rows = db.execute(stmt.order_by(WordRoot.root_en)).scalars().all()
    return {"code": "OK", "data": [{"assetId": x.asset_id, "root": x.root_en, "cnName": x.cn_name, "enFull": x.en_full, "synonyms": x.synonyms, "description": x.description, "status": x.status} for x in rows]}


@router.get("/metrics")
def metrics(keyword: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Metric)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Metric.metric_code.like(like), Metric.metric_name.like(like), Metric.aliases.like(like)))
    rows = db.execute(stmt.order_by(Metric.metric_code)).scalars().all()
    return {"code": "OK", "data": [{"assetId": x.asset_id, "metricCode": x.metric_code, "name": x.metric_name, "aliases": x.aliases, "sourceDatasetId": x.source_dataset_id, "aggregation": x.aggregation, "measureColumn": x.measure_column, "timeField": x.time_field, "timeAdditivity": x.time_additivity, "caliber": x.caliber_desc, "status": x.status} for x in rows]}


@router.get("/stat-systems")
def stat_systems(db: Session = Depends(get_db)):
    rows = db.execute(select(StatisticalSystem).order_by(StatisticalSystem.stat_system_code)).scalars().all()
    return {"code": "OK", "data": [{"assetId": x.asset_id, "code": x.stat_system_code, "name": x.stat_system_name, "version": x.version, "issuer": x.issuer, "documentNo": x.document_no, "status": x.status} for x in rows]}


@router.get("/relations/tables/{asset_id}")
def table_relations(asset_id: str, db: Session = Depends(get_db)):
    if db.get(Dataset, asset_id) is None:
        raise HTTPException(404, "Dataset not found")
    upstream = db.execute(select(TableLineage).where(TableLineage.dst_asset_id == asset_id)).scalars().all()
    downstream = db.execute(select(TableLineage).where(TableLineage.src_asset_id == asset_id)).scalars().all()
    ids = {x.src_asset_id for x in upstream} | {x.dst_asset_id for x in downstream}
    datasets = {x.asset_id: x for x in db.execute(select(Dataset).where(Dataset.asset_id.in_(ids))).scalars().all()} if ids else {}

    def edge(x: TableLineage):
        src = datasets.get(x.src_asset_id)
        dst = datasets.get(x.dst_asset_id)
        return {"srcAssetId": x.src_asset_id, "srcName": src.biz_name if src else x.src_asset_id, "dstAssetId": x.dst_asset_id, "dstName": dst.biz_name if dst else x.dst_asset_id, "taskName": x.task_name, "evidence": x.evidence}

    return {"code": "OK", "data": {"upstream": [edge(x) for x in upstream], "downstream": [edge(x) for x in downstream]}}
