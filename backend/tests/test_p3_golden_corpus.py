from sqlalchemy import func, select

from backend.app.db.models import Column, Dataset, Metric
from backend.app.db.session import SessionLocal


def test_p3_acceptance_corpus_has_real_scale():
    with SessionLocal() as db:
        assert (db.scalar(select(func.count()).select_from(Dataset)) or 0) >= 250
        assert (db.scalar(select(func.count()).select_from(Column)) or 0) >= 2500
        assert (db.scalar(select(func.count()).select_from(Metric)) or 0) >= 70


def test_golden_loan_balance_semantics_are_complete():
    with SessionLocal() as db:
        metric = db.scalar(select(Metric).where(Metric.metric_code == "metric_loan_balance"))
        assert metric is not None
        assert metric.source_dataset_id == "DS000004"
        assert metric.measure_column == "loan_balance"
        assert metric.time_field == "stat_month"
        assert "region_code" in (metric.valid_dimensions or "")
        assert "org_code" in (metric.valid_dimensions or "")
        aliases = metric.aliases or ""
        for phrase in ["贷款余额", "本期贷款余额", "当前贷款余额", "最新贷款余额", "期末贷款余额"]:
            assert phrase in aliases


def test_every_governed_metric_references_existing_semantic_fields():
    with SessionLocal() as db:
        metrics = db.scalars(select(Metric)).all()
        assert metrics
        for metric in metrics:
            table = db.get(Dataset, metric.source_dataset_id)
            assert table is not None, metric.metric_code
            fields = set(db.scalars(select(Column.column_name).where(Column.dataset_id == table.asset_id)).all())
            assert metric.measure_column in fields, (metric.metric_code, metric.measure_column, table.table_name)
            assert metric.time_field in fields, (metric.metric_code, metric.time_field, table.table_name)
            for dimension in [x.strip() for x in (metric.valid_dimensions or "").split(",") if x.strip()]:
                assert dimension in fields, (metric.metric_code, dimension, table.table_name)
