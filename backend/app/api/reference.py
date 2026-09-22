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
            "topCatalogs": [
                {"code": code, "name": name, "tableCount": count}
                for code, name, count in catalog_rows
            ],
        },
    }


@router.get("/catalogs")
def catalogs(db: Session = Depends(get_db)):
    rows = db.execute(select(Catalog).order_by(Catalog.catalog_code)).scalars().all()
    return {
        "code": "OK",
        "data": [
            {
                "code": row.catalog_code,
                "parentCode": row.parent_code,
                "name": row.catalog_name,
                "description": row.description,
            }
            for row in rows
        ],
    }


@router.get("/code-tables")
def code_tables(
    keyword: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(CodeTable)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(CodeTable.code_table_no.like(like), CodeTable.code_table_name.like(like))
        )
    rows = db.execute(stmt.order_by(CodeTable.code_table_no).limit(limit)).scalars().all()
    return {
        "code": "OK",
        "data": [
            {
                "assetId": row.asset_id,
                "codeTableNo": row.code_table_no,
                "name": row.code_table_name,
                "version": row.version,
                "status": row.status,
                "description": row.description,
            }
            for row in rows
        ],
    }


@router.get("/code-tables/{code_table_no}")
def code_table_detail(code_table_no: str, db: Session = Depends(get_db)):
    row = db.execute(
        select(CodeTable).where(CodeTable.code_table_no == code_table_no)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Code table not found")
    values = db.execute(
        select(CodeValue)
        .where(CodeValue.code_table_no == code_table_no)
        .order_by(CodeValue.id)
    ).scalars().all()
    return {
        "code": "OK",
        "data": {
            "assetId": row.asset_id,
            "codeTableNo": row.code_table_no,
            "name": row.code_table_name,
            "description": row.description,
            "status": row.status,
            "values": [
                {"value": value.code_value, "name": value.code_name, "description": value.description}
                for value in values
            ],
        },
    }


@router.get("/data-standards")
def data_standards(keyword: str | None = None, db: Session = Depends(get_db)):
    stmt = select(DataStandard)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(DataStandard.standard_no.like(like), DataStandard.standard_name.like(like))
        )
    rows = db.execute(stmt.order_by(DataStandard.standard_no)).scalars().all()
    return {
        "code": "OK",
        "data": [
            {
                "assetId": row.asset_id,
                "standardNo": row.standard_no,
                "name": row.standard_name,
                "definition": row.business_definition,
                "codeTableNo": row.code_table_no,
                "status": row.status,
            }
            for row in rows
        ],
    }


@router.get("/word-roots")
def word_roots(keyword: str | None = None, db: Session = Depends(get_db)):
    stmt = select(WordRoot)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(WordRoot.root_en.like(like), WordRoot.cn_name.like(like), WordRoot.synonyms.like(like))
        )
    rows = db.execute(stmt.order_by(WordRoot.root_en)).scalars().all()
    return {
        "code": "OK",
        "data": [
            {
                "assetId": row.asset_id,
                "root": row.root_en,
                "cnName": row.cn_name,
                "enFull": row.en_full,
                "synonyms": row.synonyms,
                "description": row.description,
                "status": row.status,
            }
            for row in rows
        ],
    }


@router.get("/metrics")
def metrics(keyword: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Metric)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            or_(Metric.metric_code.like(like), Metric.metric_name.like(like), Metric.aliases.like(like))
        )
    rows = db.execute(stmt.order_by(Metric.metric_code)).scalars().all()
    return {
        "code": "OK",
        "data": [
            {
                "assetId": row.asset_id,
                "metricCode": row.metric_code,
                "name": row.metric_name,
                "aliases": row.aliases,
                "definition": row.biz_definition,
                "sourceDatasetId": row.source_dataset_id,
                "statSystemCode": row.stat_system_code,
                "aggregation": row.aggregation,
                "measureColumn": row.measure_column,
                "timeField": row.time_field,
                "timeAdditivity": row.time_additivity,
                "validDimensions": row.valid_dimensions,
                "caliber": row.caliber_desc,
                "metricKind": row.metric_kind,
                "numeratorMetricCode": row.numerator_metric_code,
                "denominatorMetricCode": row.denominator_metric_code,
                "formula": row.formula,
                "timeGrain": row.time_grain,
                "latestStrategy": row.latest_strategy,
                "mandatoryFilters": row.mandatory_filters,
                "semanticNotes": row.semantic_notes,
                "status": row.status,
            }
            for row in rows
        ],
    }


@router.get("/stat-systems")
def stat_systems(db: Session = Depends(get_db)):
    rows = db.execute(
        select(StatisticalSystem).order_by(StatisticalSystem.stat_system_code)
    ).scalars().all()
    return {
        "code": "OK",
        "data": [
            {
                "assetId": row.asset_id,
                "code": row.stat_system_code,
                "name": row.stat_system_name,
                "version": row.version,
                "issuer": row.issuer,
                "documentNo": row.document_no,
                "status": row.status,
            }
            for row in rows
        ],
    }


@router.get("/relations/tables/{asset_id}")
def table_relations(asset_id: str, db: Session = Depends(get_db)):
    if db.get(Dataset, asset_id) is None:
        raise HTTPException(404, "Dataset not found")
    upstream = db.execute(
        select(TableLineage).where(TableLineage.dst_asset_id == asset_id)
    ).scalars().all()
    downstream = db.execute(
        select(TableLineage).where(TableLineage.src_asset_id == asset_id)
    ).scalars().all()
    ids = {item.src_asset_id for item in upstream} | {item.dst_asset_id for item in downstream}
    datasets = (
        {
            item.asset_id: item
            for item in db.execute(select(Dataset).where(Dataset.asset_id.in_(ids))).scalars().all()
        }
        if ids
        else {}
    )

    def edge(item: TableLineage):
        src = datasets.get(item.src_asset_id)
        dst = datasets.get(item.dst_asset_id)
        return {
            "srcAssetId": item.src_asset_id,
            "srcName": src.biz_name if src else item.src_asset_id,
            "dstAssetId": item.dst_asset_id,
            "dstName": dst.biz_name if dst else item.dst_asset_id,
            "taskName": item.task_name,
            "evidence": item.evidence,
        }

    return {
        "code": "OK",
        "data": {
            "upstream": [edge(item) for item in upstream],
            "downstream": [edge(item) for item in downstream],
        },
    }
