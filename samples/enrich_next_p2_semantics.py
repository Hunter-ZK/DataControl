from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from backend.app.db.models import Metric
from backend.app.db.session import SessionLocal


def _merge_aliases(current: str | None, *extra: str) -> str:
    items: list[str] = []
    for raw in [current or "", *extra]:
        for token in raw.replace("，", ",").split(","):
            value = token.strip()
            if value and value not in items:
                items.append(value)
    return ",".join(items)


def main() -> None:
    with SessionLocal() as db:
        metrics = {
            row.metric_code: row
            for row in db.execute(select(Metric)).scalars().all()
        }

        for metric in metrics.values():
            metric.metric_kind = metric.metric_kind or "BASE"
            metric.time_grain = "MONTH" if metric.time_field == "stat_month" else "DAY"
            metric.latest_strategy = "MAX"
            metric.semantic_notes = metric.semantic_notes or "由 DataControl 内部治理语义维护；证据不足时必须澄清，不使用外部网络补全。"

        loan_balance = metrics["metric_loan_balance"]
        loan_balance.mandatory_filters = json.dumps(
            [{"field": "currency_cd", "op": "eq", "value": "CNY", "label": "人民币"}],
            ensure_ascii=False,
        )
        loan_balance.semantic_notes = "月末余额快照，不跨月相加；本期取 stat_month 最大可用值。默认人民币口径。"

        new_loan = metrics["metric_new_loan_amount"]
        new_loan.aliases = _merge_aliases(new_loan.aliases, "贷款增长", "贷款增加")
        new_loan.semantic_notes = "期间发生额，可按月份累加；“贷款增长”存在余额同比与新增发生额两种解释时必须让用户选择。"

        if "metric_npl_ratio" not in metrics:
            db.add(
                Metric(
                    asset_id="MT009001",
                    metric_code="metric_npl_ratio",
                    metric_name="不良贷款率",
                    aliases="不良率,不良贷款占比,NPL率",
                    biz_definition="不良贷款余额占各项贷款余额的比例。",
                    source_dataset_id="DS000004",
                    stat_system_code="SS-FIN-2026",
                    aggregation="ratio",
                    measure_column="npl_balance",
                    time_field="stat_month",
                    time_additivity="NON_ADDITIVE",
                    caliber_desc="同一统计期内，不良贷款余额除以各项贷款余额。",
                    valid_dimensions="region_code,org_code,loan_type",
                    metric_kind="RATIO",
                    numerator_metric_code="metric_npl_balance",
                    denominator_metric_code="metric_loan_balance",
                    formula="metric_npl_balance / metric_loan_balance",
                    time_grain="MONTH",
                    latest_strategy="MAX",
                    mandatory_filters=json.dumps(
                        [{"field": "currency_cd", "op": "eq", "value": "CNY", "label": "人民币"}],
                        ensure_ascii=False,
                    ),
                    semantic_notes="分子与分母必须使用同一统计期、同一维度粒度。",
                    status="ONLINE",
                )
            )

        if "metric_loan_balance_yoy" not in metrics:
            db.add(
                Metric(
                    asset_id="MT009002",
                    metric_code="metric_loan_balance_yoy",
                    metric_name="贷款余额同比增长率",
                    aliases="贷款增长,贷款同比,贷款余额增长,贷款同比增长",
                    biz_definition="各项贷款余额较上年同期的增长率。",
                    source_dataset_id="DS000004",
                    stat_system_code="SS-FIN-2026",
                    aggregation="derived",
                    measure_column="loan_balance",
                    time_field="stat_month",
                    time_additivity="NON_ADDITIVE",
                    caliber_desc="(本期贷款余额 - 上年同期贷款余额) / 上年同期贷款余额。",
                    valid_dimensions="region_code,org_code,customer_type,loan_type,currency_cd",
                    metric_kind="DERIVED",
                    formula="(current(metric_loan_balance) - yoy(metric_loan_balance)) / yoy(metric_loan_balance)",
                    time_grain="MONTH",
                    latest_strategy="MAX",
                    mandatory_filters=json.dumps(
                        [{"field": "currency_cd", "op": "eq", "value": "CNY", "label": "人民币"}],
                        ensure_ascii=False,
                    ),
                    semantic_notes="比较期必须与本期保持相同维度和口径；“贷款增长”歧义时与新增贷款金额并列供用户选择。",
                    status="ONLINE",
                )
            )

        db.commit()
        print("Next-P2 semantics enriched: BASE metric semantics + NPL ratio + loan YoY ambiguity fixture")


if __name__ == "__main__":
    main()
