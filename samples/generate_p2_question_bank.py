from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".local" / "p2-question-bank.json"


def case(
    category: str,
    question: str,
    *,
    metrics: list[str] | None = None,
    dimensions: list[str] | None = None,
    comparison: str | None = None,
    codes: dict[str, str] | None = None,
    status: str = "resolved",
    sql: bool = True,
    note: str = "",
) -> dict:
    return {
        "category": category,
        "question": question,
        "expectedStatus": status,
        "expectedMetrics": metrics or [],
        "expectedDimensions": dimensions or [],
        "expectedComparison": comparison,
        "expectedCodeValues": codes or {},
        "shouldGenerateSql": sql,
        "note": note,
    }


def build() -> list[dict]:
    cases = [
        # Single governed metrics: vary wording, dimensions and periods.
        case("single_metric", "本期广东各项贷款余额是多少？", metrics=["metric_loan_balance"], dimensions=["region_code"]),
        case("single_metric", "最新一期各机构普惠贷款余额", metrics=["metric_inclusive_loan_balance"], dimensions=["org_code"]),
        case("single_metric", "2026-08 不良贷款余额按地区统计", metrics=["metric_npl_balance"], dimensions=["region_code"]),
        case("single_metric", "本期逾期贷款余额按贷款类型分组", metrics=["metric_overdue_balance"], dimensions=["loan_type"]),
        case("single_metric", "2026-08 新增贷款金额按机构看", metrics=["metric_new_loan_amount"], dimensions=["org_code"]),
        case("single_metric", "最新一期各地区存款余额", metrics=["metric_deposit_balance"], dimensions=["region_code"]),
        case("single_metric", "本期支付交易金额按机构统计", metrics=["metric_payment_amount"], dimensions=["org_code"]),
        case("single_metric", "最新一期各地区风险敞口", metrics=["metric_risk_exposure"], dimensions=["region_code"]),

        # Multi-metric planning.
        case("multi_metric", "本期按地区同时看贷款余额和存款余额", metrics=["metric_loan_balance", "metric_deposit_balance"], dimensions=["region_code"], note="若来源不兼容，应澄清或拆分，不得强行拼接。"),
        case("multi_metric", "各地区贷款余额、新增贷款金额和贷款客户数", metrics=["metric_loan_balance", "metric_new_loan_amount", "metric_loan_customer_count"], dimensions=["region_code"]),
        case("multi_metric", "本期各机构支付交易金额和交易笔数", metrics=["metric_payment_amount", "metric_payment_count"], dimensions=["org_code"]),
        case("multi_metric", "各地区企业存款余额和住户存款余额", metrics=["metric_corporate_deposit_balance", "metric_household_deposit_balance"], dimensions=["region_code"]),
        case("multi_metric", "各地区银行卡交易金额、交易笔数和客户数", metrics=["metric_card_transaction_amount", "metric_card_transaction_count", "metric_card_customer_count"], dimensions=["region_code"]),

        # Ratio metrics.
        case("ratio", "本期各地区不良贷款率", metrics=["metric_npl_ratio"], dimensions=["region_code"]),
        case("ratio", "各机构普惠贷款余额占比", metrics=["metric_inclusive_loan_ratio"], dimensions=["org_code"]),
        case("ratio", "2026-08 各地区逾期贷款余额占比", metrics=["metric_overdue_loan_ratio"], dimensions=["region_code"]),
        case("ratio", "各地区企业存款占全部存款的比重", metrics=["metric_corporate_deposit_share"], dimensions=["region_code"]),
        case("ratio", "各机构笔均支付金额", metrics=["metric_avg_payment_amount"], dimensions=["org_code"]),

        # TopN/ranking.
        case("topn", "贷款余额最高的前10个地区", metrics=["metric_loan_balance"], dimensions=["region_code"], note="DESC + LIMIT 10"),
        case("topn", "不良贷款率最高的前5个地区", metrics=["metric_npl_ratio"], dimensions=["region_code"], note="DESC + LIMIT 5"),
        case("topn", "新增贷款金额最大的前10家机构", metrics=["metric_new_loan_amount"], dimensions=["org_code"]),
        case("topn", "支付交易金额最低的5个地区", metrics=["metric_payment_amount"], dimensions=["region_code"], note="ASC + LIMIT 5"),
        case("topn", "风险敞口最高的前10个地区", metrics=["metric_risk_exposure"], dimensions=["region_code"]),

        # YoY with deterministic period semantics.
        case("yoy", "2026-08 各地区贷款余额同比", metrics=["metric_loan_balance"], dimensions=["region_code"], comparison="yoy"),
        case("yoy", "2026-06 各机构普惠贷款余额同比增长", metrics=["metric_inclusive_loan_balance"], dimensions=["org_code"], comparison="yoy"),
        case("yoy", "2026-09 各地区存款余额同比", metrics=["metric_deposit_balance"], dimensions=["region_code"], comparison="yoy"),
        case("yoy", "2026-03 支付交易金额同比变化", metrics=["metric_payment_amount"], comparison="yoy"),
        case("yoy", "2026-12 各地区银行卡数量同比", metrics=["metric_card_count"], dimensions=["region_code"], comparison="yoy"),

        # MoM includes year-boundary coverage.
        case("mom", "2026-01 各地区贷款余额环比", metrics=["metric_loan_balance"], dimensions=["region_code"], comparison="mom"),
        case("mom", "2026-08 各机构新增贷款金额环比", metrics=["metric_new_loan_amount"], dimensions=["org_code"], comparison="mom"),
        case("mom", "2026-01 存款余额环比变化", metrics=["metric_deposit_balance"], comparison="mom"),
        case("mom", "2026-07 各地区支付交易笔数环比", metrics=["metric_payment_count"], dimensions=["region_code"], comparison="mom"),
        case("mom", "2026-02 风险事件数环比", metrics=["metric_risk_event_count"], comparison="mom"),

        # Code-value resolution.
        case("code_value", "广州市人民币贷款余额", metrics=["metric_loan_balance"], codes={"广州市": "440100", "人民币": "CNY"}),
        case("code_value", "深圳市人民币普惠贷款余额", metrics=["metric_inclusive_loan_balance"], codes={"深圳市": "440300", "人民币": "CNY"}),
        case("code_value", "佛山市美元存款余额", metrics=["metric_deposit_balance"], codes={"佛山市": "440600", "美元": "USD"}),
        case("code_value", "东莞市人民币支付交易金额", metrics=["metric_payment_amount"], codes={"东莞市": "441900", "人民币": "CNY"}),
        case("code_value", "惠州市人民币资管产品余额", metrics=["metric_aum_balance"], codes={"惠州市": "441300", "人民币": "CNY"}),

        # Multiple filters must resolve independently.
        case("multi_filter", "广州市企业客户人民币贷款余额", metrics=["metric_loan_balance"], codes={"广州市": "440100", "企业": "CORP", "人民币": "CNY"}),
        case("multi_filter", "深圳市普惠贷款中小微企业客户余额", metrics=["metric_inclusive_loan_balance"], codes={"深圳市": "440300", "小微企业": "SME"}),
        case("multi_filter", "广州市人民币企业存款余额", metrics=["metric_corporate_deposit_balance"], codes={"广州市": "440100", "人民币": "CNY"}),
        case("multi_filter", "东莞市较高风险企业的风险敞口", metrics=["metric_risk_exposure"], codes={"东莞市": "441900", "较高风险": "D"}),
        case("multi_filter", "佛山市手机银行人民币支付交易金额", metrics=["metric_payment_amount"], codes={"佛山市": "440600", "人民币": "CNY", "手机银行": "MOBILE"}),

        # Ambiguous business wording must stop for a user choice.
        case("ambiguity", "今年贷款增长怎么样？", status="clarification_required", sql=False, note="余额同比 vs 新增贷款金额"),
        case("ambiguity", "帮我看贷款增加情况", status="clarification_required", sql=False, note="增长率与发生额存在口径分歧"),
        case("ambiguity", "存款增长情况怎么样", status="clarification_required", sql=False, note="缺少增长口径和时间范围"),
        case("ambiguity", "风险情况怎么样", status="clarification_required", sql=False, note="风险事件数、风险敞口等多个指标候选"),

        # Invalid dimension should fail closed, not silently group by a nonexistent field.
        case("invalid_dimension", "贷款余额按支付方式统计", metrics=["metric_loan_balance"], dimensions=["payment_method"], status="clarification_required", sql=False),
        case("invalid_dimension", "存款余额按贷款类型统计", metrics=["metric_deposit_balance"], dimensions=["loan_type"], status="clarification_required", sql=False),
        case("invalid_dimension", "银行卡数量按风险等级统计", metrics=["metric_card_count"], dimensions=["risk_level"], status="clarification_required", sql=False),

        # Time non-additivity.
        case("non_additive", "把2026年1到12月的贷款月末余额直接加总", metrics=["metric_loan_balance"], status="clarification_required", sql=False, note="NON_ADDITIVE_OVER_TIME"),
        case("non_additive", "把过去6个月的存款余额求和", metrics=["metric_deposit_balance"], status="clarification_required", sql=False, note="余额快照不可跨期直接 SUM"),
        case("non_additive", "全年资管产品月末余额合计", metrics=["metric_aum_balance"], status="clarification_required", sql=False),

        # Unknown semantics.
        case("unknown_metric", "查询火星资产回报率", status="evidence_insufficient", sql=False),
        case("unknown_metric", "查询量子授信指数", status="evidence_insufficient", sql=False),
        case("unknown_metric", "统计星际客户价值", status="evidence_insufficient", sql=False),

        # Synonym robustness.
        case("synonym", "本期各项贷款是多少", metrics=["metric_loan_balance"]),
        case("synonym", "当前单位存款余额按地区看", metrics=["metric_corporate_deposit_balance"], dimensions=["region_code"]),
        case("synonym", "本月刷卡交易金额", metrics=["metric_card_transaction_amount"]),
        case("synonym", "最新一期风险暴露按地区统计", metrics=["metric_risk_exposure"], dimensions=["region_code"]),

        # Time ambiguity should request clarification rather than invent a cutoff.
        case("time_ambiguity", "今年贷款余额是多少", metrics=["metric_loan_balance"], status="clarification_required", sql=False, note="快照指标的‘今年’需要明确期末或期间口径"),
        case("time_ambiguity", "最近贷款余额", metrics=["metric_loan_balance"], status="clarification_required", sql=False, note="最近需要解析为最新一期或具体时间范围"),
        case("time_ambiguity", "上半年存款情况", metrics=["metric_deposit_balance"], status="clarification_required", sql=False),
        case("time_ambiguity", "近期支付交易金额", metrics=["metric_payment_amount"], status="clarification_required", sql=False),
    ]
    for idx, item in enumerate(cases, 1):
        item["id"] = f"P2Q{idx:03d}"
    return cases


def main() -> None:
    cases = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "2.1",
        "purpose": "DataControl P2 semantic planning regression corpus",
        "count": len(cases),
        "cases": cases,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    categories = sorted({item["category"] for item in cases})
    print(f"Generated P2 question bank: {len(cases)} cases / {len(categories)} categories -> {OUT}")
    print("Categories: " + ", ".join(categories))


if __name__ == "__main__":
    main()
