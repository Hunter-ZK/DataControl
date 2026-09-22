from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db.lineage_models import ColumnLineage
from backend.app.db.models import (
    CodeTable,
    CodeValue,
    Column,
    DataStandard,
    Dataset,
    Metric,
    TableLineage,
)
from backend.app.db.session import SessionLocal

QUESTION_BANK = ROOT / ".local" / "p2-question-bank.json"
PLACEHOLDER = re.compile(r"scenario|合成测试|测试指标|P3\s*验收|测试码值|测试制度", re.IGNORECASE)
NUMBERED_FILLER = re.compile(r"(?:原始明细|标准明细|主题汇总|应用报表|参考维度)\d{3}$")
REQUIRED_CATALOGS = {
    "FIN.LOAN", "FIN.DEP", "FIN.PAY", "FIN.RISK", "FIN.ASSET", "FIN.ENT", "FIN.REG", "FIN.CARD",
    "COMMON.ORG", "COMMON.CUST", "COMMON.PROD", "COMMON.DATE",
}
REQUIRED_QUESTION_CATEGORIES = {
    "single_metric", "multi_metric", "ratio", "topn", "yoy", "mom", "code_value",
    "multi_filter", "ambiguity", "invalid_dimension", "non_additive", "unknown_metric", "synonym", "time_ambiguity",
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> None:
    errors: list[str] = []
    metric_by_code: dict[str, Metric] = {}
    code_pairs: set[tuple[str, str]] = set()

    with SessionLocal() as db:
        datasets = db.execute(select(Dataset)).scalars().all()
        columns = db.execute(select(Column)).scalars().all()
        metrics = db.execute(select(Metric)).scalars().all()
        code_tables = db.execute(select(CodeTable)).scalars().all()
        code_values = db.execute(select(CodeValue)).scalars().all()
        standards = db.execute(select(DataStandard)).scalars().all()
        table_edges = db.execute(select(TableLineage)).scalars().all()
        column_edges = db.execute(select(ColumnLineage)).scalars().all()

        metric_by_code = {item.metric_code: item for item in metrics}
        code_pairs = {(item.code_name, item.code_value) for item in code_values}

        if len(datasets) < 260:
            fail(errors, f"dataset coverage too small: {len(datasets)} < 260")
        if len(metrics) < 30:
            fail(errors, f"metric coverage too small: {len(metrics)} < 30")
        if len(column_edges) < 500:
            fail(errors, f"field-lineage coverage too small: {len(column_edges)} < 500")

        catalogs = {item.catalog_code for item in datasets}
        missing_catalogs = REQUIRED_CATALOGS - catalogs
        if missing_catalogs:
            fail(errors, f"missing business catalogs: {sorted(missing_catalogs)}")

        dataset_by_id = {item.asset_id: item for item in datasets}
        columns_by_dataset: dict[str, dict[str, Column]] = {}
        for column in columns:
            columns_by_dataset.setdefault(column.dataset_id, {})[column.column_name] = column

        for dataset in datasets:
            visible_text = " ".join(
                filter(None, [dataset.table_name, dataset.biz_name, dataset.biz_definition, dataset.stat_caliber, dataset.data_source_desc])
            )
            if PLACEHOLDER.search(visible_text):
                fail(errors, f"placeholder copy remains on {dataset.asset_id}: {visible_text[:140]}")
            if NUMBERED_FILLER.search(dataset.biz_name):
                fail(errors, f"numbered filler asset remains: {dataset.asset_id} {dataset.biz_name}")
            if not dataset.biz_definition or len(dataset.biz_definition) < 20:
                fail(errors, f"business definition too weak: {dataset.asset_id}")
            if not dataset.grain:
                fail(errors, f"missing grain: {dataset.asset_id}")

        code_set = {item.code_table_no for item in code_tables}
        standard_set = {item.standard_no for item in standards}
        for column in columns:
            if column.code_table_no and column.code_table_no not in code_set:
                fail(errors, f"column {column.asset_id} references missing code table {column.code_table_no}")
            if column.standard_no and column.standard_no not in standard_set:
                fail(errors, f"column {column.asset_id} references missing standard {column.standard_no}")

        for metric in metrics:
            source = dataset_by_id.get(metric.source_dataset_id)
            if source is None:
                fail(errors, f"metric {metric.metric_code} references missing source {metric.source_dataset_id}")
                continue
            source_columns = columns_by_dataset.get(source.asset_id, {})
            if metric.measure_column not in source_columns:
                fail(errors, f"metric {metric.metric_code} measure {metric.measure_column} missing from {source.table_name}")
            if metric.time_field not in source_columns:
                fail(errors, f"metric {metric.metric_code} time field {metric.time_field} missing from {source.table_name}")
            for dimension in [item.strip() for item in (metric.valid_dimensions or "").split(",") if item.strip()]:
                if dimension not in source_columns:
                    fail(errors, f"metric {metric.metric_code} dimension {dimension} missing from {source.table_name}")
            if PLACEHOLDER.search(" ".join(filter(None, [metric.metric_name, metric.biz_definition, metric.caliber_desc]))):
                fail(errors, f"placeholder metric copy remains: {metric.metric_code}")

        edge_keys: set[tuple[str, str]] = set()
        for edge in table_edges:
            if edge.src_asset_id not in dataset_by_id or edge.dst_asset_id not in dataset_by_id:
                fail(errors, f"lineage references missing dataset: {edge.src_asset_id}->{edge.dst_asset_id}")
                continue
            if edge.src_asset_id == edge.dst_asset_id:
                fail(errors, f"self lineage detected: {edge.src_asset_id}")
            key = (edge.src_asset_id, edge.dst_asset_id)
            if key in edge_keys:
                fail(errors, f"duplicate table lineage edge: {key}")
            edge_keys.add(key)
            src_num = int(edge.src_asset_id[2:]) if edge.src_asset_id.startswith("DS") else 0
            dst_num = int(edge.dst_asset_id[2:]) if edge.dst_asset_id.startswith("DS") else 0
            if src_num >= 33 and dst_num >= 33:
                src = dataset_by_id[edge.src_asset_id]
                dst = dataset_by_id[edge.dst_asset_id]
                if src.catalog_code != dst.catalog_code:
                    fail(errors, f"portfolio lineage crosses unrelated catalogs: {src.asset_id}->{dst.asset_id}")

    if not QUESTION_BANK.exists():
        fail(errors, f"missing P2 question bank: {QUESTION_BANK}")
    else:
        payload = json.loads(QUESTION_BANK.read_text(encoding="utf-8"))
        cases = payload.get("cases", [])
        if len(cases) < 50:
            fail(errors, f"P2 question corpus too small: {len(cases)} < 50")
        questions = [str(case.get("question") or "") for case in cases]
        if len(set(questions)) != len(questions):
            fail(errors, "P2 question corpus contains duplicate questions")
        categories = {str(case.get("category") or "") for case in cases}
        missing_categories = REQUIRED_QUESTION_CATEGORIES - categories
        if missing_categories:
            fail(errors, f"P2 question corpus missing categories: {sorted(missing_categories)}")

        for item in cases:
            case_id = str(item.get("id") or "unknown")
            expected_status = str(item.get("expectedStatus") or "")
            expected_metrics = [str(code) for code in item.get("expectedMetrics", []) if code]
            expected_dimensions = [str(name) for name in item.get("expectedDimensions", []) if name]
            for metric_code in expected_metrics:
                metric = metric_by_code.get(metric_code)
                if metric is None:
                    fail(errors, f"{case_id} expects unknown metric {metric_code}")
                    continue
                if expected_status == "resolved":
                    valid_dimensions = {
                        name.strip() for name in (metric.valid_dimensions or "").split(",") if name.strip()
                    }
                    for dimension in expected_dimensions:
                        if dimension not in valid_dimensions:
                            fail(errors, f"{case_id} expects unsupported dimension {dimension} for {metric_code}")

            for phrase, value in (item.get("expectedCodeValues") or {}).items():
                if (str(phrase), str(value)) not in code_pairs:
                    fail(errors, f"{case_id} expects missing code value {phrase!r}->{value!r}")

    if errors:
        print("P2 CORPUS QUALITY GATE FAILED")
        for item in errors[:80]:
            print(f"- {item}")
        raise SystemExit(1)

    print("P2 CORPUS QUALITY GATE PASSED")
    print("260+ assets / 30+ governed metrics / 500+ field-lineage edges / 50+ evaluation questions")
    print("No numbered scenario fillers; metadata, metric, code-value and evaluation expectations are mutually consistent")


if __name__ == "__main__":
    main()
