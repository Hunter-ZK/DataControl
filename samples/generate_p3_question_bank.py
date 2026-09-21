from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".local" / "p3-question-bank.json"

METRICS = [
    ("metric_loan_balance", "贷款余额"),
    ("metric_inclusive_loan_balance", "普惠贷款余额"),
    ("metric_npl_balance", "不良贷款余额"),
    ("metric_overdue_balance", "逾期贷款余额"),
    ("metric_new_loan_amount", "新增贷款金额"),
    ("metric_loan_count", "贷款笔数"),
    ("metric_loan_customer_count", "贷款客户数"),
    ("metric_deposit_balance", "存款余额"),
    ("metric_corporate_deposit_balance", "企业存款余额"),
    ("metric_household_deposit_balance", "住户存款余额"),
    ("metric_payment_amount", "支付交易金额"),
    ("metric_payment_count", "支付交易笔数"),
    ("metric_risk_event_count", "企业风险事件数"),
    ("metric_risk_exposure", "风险敞口"),
    ("metric_aum_balance", "资管产品余额"),
    ("metric_card_count", "银行卡数量"),
]


def build() -> list[dict]:
    cases: list[dict] = []
    seq = 1
    for code, name in METRICS:
        for period in ("本期", "当前", "最新一期"):
            for dimension_phrase, dimensions in (("", []), ("按地区", ["region_code"])):
                cases.append({
                    "id": f"Q{seq:03d}",
                    "kind": "query",
                    "question": f"{period}{dimension_phrase}{name}，生成并校验 SQL",
                    "expectedMetric": code,
                    "expectedTime": "LATEST",
                    "expectedDimensions": dimensions,
                })
                seq += 1
    for code, name in METRICS[:8]:
        for dimension_phrase, dimensions in (("", []), ("按地区", ["region_code"]), ("按机构", ["org_code"])):
            cases.append({
                "id": f"Q{seq:03d}",
                "kind": "query",
                "question": f"上期{dimension_phrase}{name}，生成并校验 SQL",
                "expectedMetric": code,
                "expectedTime": "PREVIOUS",
                "expectedDimensions": dimensions,
            })
            seq += 1
    metadata_questions = [
        ("贷款余额使用哪张数据表？", "metric_loan_balance"),
        ("贷款余额的统计口径是什么？", "metric_loan_balance"),
        ("普惠贷款余额使用哪些维度？", "metric_inclusive_loan_balance"),
        ("不良贷款余额来源表是什么？", "metric_npl_balance"),
        ("存款余额的时间字段是什么？", "metric_deposit_balance"),
        ("支付交易金额按什么口径统计？", "metric_payment_amount"),
        ("风险敞口使用哪张表？", "metric_risk_exposure"),
        ("资管产品余额的指标定义是什么？", "metric_aum_balance"),
    ]
    for question, code in metadata_questions:
        cases.append({
            "id": f"Q{seq:03d}",
            "kind": "metadata",
            "question": question,
            "expectedMetric": code,
            "expectedTime": None,
            "expectedDimensions": [],
        })
        seq += 1
    return cases


def main() -> None:
    cases = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"count": len(cases), "cases": cases}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated P3 Agent question bank: {len(cases)} cases -> {OUT}")


if __name__ == "__main__":
    main()
