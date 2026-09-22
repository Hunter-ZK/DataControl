from sqlalchemy import func, select

from backend.app.db.models import Column, Dataset, Metric
from backend.app.db.session import SessionLocal


def test_acceptance_corpus_has_realistic_scale_without_metric_fillers():
    with SessionLocal() as db:
        dataset_count = db.scalar(select(func.count()).select_from(Dataset)) or 0
        column_count = db.scalar(select(func.count()).select_from(Column)) or 0
        metrics = db.scalars(select(Metric)).all()

        assert dataset_count >= 250
        assert column_count >= 2400
        # P2.1 intentionally removed dozens of near-duplicate metrics that existed
        # only to satisfy a volume target. Thirty distinct governed metrics are a
        # stronger corpus than seventy copy variants.
        assert len(metrics) >= 30
        assert len({metric.metric_code for metric in metrics}) == len(metrics)
        assert len({metric.metric_name for metric in metrics}) == len(metrics)

        kinds = {metric.metric_kind for metric in metrics}
        assert {"BASE", "RATIO", "DERIVED"} <= kinds
        assert sum(metric.metric_kind == "RATIO" for metric in metrics) >= 5
        assert not any(
            metric.metric_name.endswith(suffix)
            for metric in metrics
            for suffix in ("总量", "机构口径", "地区口径", "监管口径", "经营口径", "分析口径")
        )


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
