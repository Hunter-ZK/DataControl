from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from sqlalchemy import delete, or_, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db.models import (
    ChangeLog,
    CodeTable,
    CodeValue,
    Column,
    CommonSql,
    CommonSqlDataset,
    DataStandard,
    Dataset,
    Metric,
    StatisticalSystem,
    TableLineage,
)
from backend.app.db.session import SessionLocal


PORTFOLIO = {
    "FIN.LOAN": [
        ("corporate_credit", "企业贷款"),
        ("inclusive_finance", "普惠小微贷款"),
        ("manufacturing", "制造业贷款"),
        ("green_credit", "绿色贷款"),
        ("agriculture", "涉农贷款"),
        ("consumer", "个人消费贷款"),
        ("mortgage", "个人住房贷款"),
        ("auto", "个人汽车贷款"),
        ("credit_card_installment", "信用卡分期贷款"),
        ("syndicated", "银团贷款"),
        ("guaranteed", "担保贷款"),
        ("overdue", "逾期贷款"),
    ],
    "FIN.DEP": [
        ("corporate_deposit", "企业存款"),
        ("household_deposit", "住户存款"),
        ("fiscal_deposit", "财政性存款"),
        ("nonbank_deposit", "非银行业金融机构存款"),
        ("demand_deposit", "活期存款"),
        ("time_deposit", "定期存款"),
        ("large_cd", "大额存单"),
    ],
    "FIN.PAY": [
        ("transfer", "转账支付"),
        ("mobile_payment", "移动支付"),
        ("internet_payment", "网上支付"),
        ("qr_payment", "条码支付"),
        ("bankcard_payment", "银行卡支付"),
        ("interbank_payment", "跨行支付"),
    ],
    "FIN.RISK": [
        ("npl_monitor", "不良贷款监测"),
        ("overdue_monitor", "逾期贷款监测"),
        ("large_exposure", "大额风险暴露"),
        ("concentration", "授信集中度风险"),
        ("enterprise_alert", "企业风险预警"),
        ("collateral_risk", "抵质押物风险"),
    ],
    "FIN.ASSET": [
        ("wealth_product", "银行理财产品"),
        ("fund_product", "基金产品"),
        ("trust_product", "信托产品"),
        ("securities_product", "证券资管产品"),
        ("asset_allocation", "资管资产配置"),
    ],
    "FIN.ENT": [
        ("enterprise_profile", "企业基本信息"),
        ("enterprise_equity", "企业股权关系"),
        ("enterprise_judicial", "企业司法风险"),
        ("enterprise_operation", "企业经营风险"),
    ],
    "FIN.REG": [
        ("monthly_statistics", "金融统计月报"),
        ("quarterly_statistics", "金融统计季报"),
        ("balance_sheet", "金融机构资产负债统计"),
        ("regulatory_quality", "监管报送质量监测"),
        ("institution_reporting", "机构统计报送"),
    ],
    "FIN.CARD": [
        ("debit_card", "借记卡业务"),
        ("credit_card", "信用卡业务"),
        ("active_card", "活跃银行卡"),
        ("acquiring", "银行卡收单业务"),
    ],
    "COMMON.ORG": [
        ("financial_institution", "金融机构主数据"),
        ("branch_network", "营业网点主数据"),
    ],
    "COMMON.CUST": [
        ("customer_profile", "客户主数据"),
        ("customer_classification", "客户分类主数据"),
    ],
    "COMMON.PROD": [
        ("loan_product", "贷款产品主数据"),
        ("deposit_product", "存款产品主数据"),
    ],
    "COMMON.DATE": [
        ("calendar", "自然日历"),
        ("reporting_calendar", "统计报送日历"),
    ],
}

DOMAIN_PROFILE = {
    "FIN.LOAN": ("loan", "信贷统计组", "核心信贷业务系统（模拟）", "贷款业务"),
    "FIN.DEP": ("deposit", "存款统计组", "核心存款业务系统（模拟）", "存款业务"),
    "FIN.PAY": ("payment", "支付统计组", "统一支付平台（模拟）", "支付结算业务"),
    "FIN.RISK": ("risk", "风险监测组", "风险监测平台（模拟）", "风险监测业务"),
    "FIN.ASSET": ("asset", "资管统计组", "资产管理平台（模拟）", "资产管理业务"),
    "FIN.ENT": ("enterprise", "调查统计组", "企业信息库（模拟）", "企业信息业务"),
    "FIN.REG": ("regulatory", "监管报送组", "统一监管报送平台（模拟）", "监管统计业务"),
    "FIN.CARD": ("card", "支付统计组", "银行卡业务平台（模拟）", "银行卡业务"),
    "COMMON.ORG": ("org", "数据资产部", "机构主数据平台（模拟）", "机构公共维度"),
    "COMMON.CUST": ("customer", "数据资产部", "客户主数据平台（模拟）", "客户公共维度"),
    "COMMON.PROD": ("product", "数据资产部", "产品主数据平台（模拟）", "产品公共维度"),
    "COMMON.DATE": ("calendar", "数据资产部", "统一日期服务（模拟）", "日期公共维度"),
}

BUSINESS_STAGES = [
    ("ODS", "raw", "原始明细"),
    ("DWD", "detail", "标准明细"),
    ("DWS", "month", "主题汇总"),
    ("ADS", "report", "分析报表"),
]
REFERENCE_STAGES = [
    ("ODS", "raw", "原始数据"),
    ("DWD", "detail", "标准数据"),
    ("DIM", "dim", "公共维度"),
    ("ADS", "service", "查询服务"),
]

FIELD_SPECS = {
    "stat_date": ("统计日期", "date", "数据所属统计日期", None, None, "DS-DATE-001"),
    "stat_month": ("统计月份", "string", "YYYY-MM 格式统计月份", None, None, "DS-MONTH-001"),
    "org_code": ("机构编码", "string", "金融机构统一编码", None, "CD_ORG", "DS-ORG-001"),
    "region_code": ("地区编码", "string", "行政区划代码", None, "CD_REGION", "DS-REGION-001"),
    "customer_type": ("客户类型", "string", "客户统一分类代码", None, "CD_CUSTOMER_TYPE", "DS-CUSTTYPE-001"),
    "loan_type": ("贷款类型", "string", "贷款业务分类代码", None, "CD_LOAN_TYPE", "DS-LOANTYPE-001"),
    "currency_cd": ("币种", "string", "ISO 风格币种代码", None, "CD_CURRENCY", "DS-CURRENCY-001"),
    "status": ("业务状态", "string", "统一业务状态代码", None, "CD_STATUS", "DS-STATUS-001"),
    "risk_level": ("风险等级", "string", "统一风险等级代码", None, "CD_RISK_LEVEL", "DS-RISK-001"),
    "industry_code": ("行业代码", "string", "客户所属国民经济行业分类", None, "CD_INDUSTRY", "DS-INDUSTRY-001"),
    "institution_type": ("机构类型", "string", "金融机构类型代码", None, "CD_INST_TYPE", "DS-INSTTYPE-001"),
    "maturity_bucket": ("期限区间", "string", "业务剩余期限分组", None, "CD_MATURITY", "DS-MATURITY-001"),
    "rate_type": ("利率类型", "string", "固定或浮动利率类型", None, "CD_RATE_TYPE", "DS-RATETYPE-001"),
    "channel_code": ("渠道代码", "string", "业务受理渠道代码", None, "CD_CHANNEL", "DS-CHANNEL-001"),
    "payment_method": ("支付方式", "string", "支付工具或方式代码", None, "CD_PAYMENT_METHOD", "DS-PAYMETHOD-001"),
    "enterprise_type": ("企业类型", "string", "企业规模与组织类型代码", None, "CD_ENTERPRISE_TYPE", "DS-ENTTYPE-001"),
    "product_type": ("产品类型", "string", "金融产品分类代码", None, "CD_PRODUCT_TYPE", "DS-PRODTYPE-001"),
    "card_type": ("银行卡类型", "string", "借记卡或信用卡分类", None, "CD_CARD_TYPE", "DS-CARDTYPE-001"),
    "cust_id": ("客户编号", "string", "脱敏后的客户唯一标识", None, None, "DS-CUST-001"),
    "contract_id": ("合同编号", "string", "业务合同唯一标识", None, None, "DS-CONTRACT-001"),
    "account_id": ("账户编号", "string", "业务账户唯一标识", None, None, "DS-ACCOUNT-001"),
    "product_code": ("产品编码", "string", "金融产品唯一编码", None, None, "DS-PRODUCT-001"),
    "loan_balance": ("贷款余额", "decimal(20,2)", "统计期末尚未结清贷款本金余额", "元", None, "DS-LOAN-BAL-001"),
    "inclusive_loan_balance": ("普惠贷款余额", "decimal(20,2)", "统计期末符合普惠口径的贷款余额", "元", None, "DS-INCL-BAL-001"),
    "npl_balance": ("不良贷款余额", "decimal(20,2)", "统计期末不良贷款余额", "元", None, "DS-NPL-BAL-001"),
    "overdue_balance": ("逾期贷款余额", "decimal(20,2)", "统计期末逾期贷款余额", "元", None, "DS-OVERDUE-BAL-001"),
    "new_loan_amount": ("新增贷款金额", "decimal(20,2)", "统计期内新发放贷款金额", "元", None, "DS-NEWLOAN-AMT-001"),
    "loan_count": ("贷款笔数", "bigint", "有效贷款合同或账户数量", "笔", None, "DS-LOAN-CNT-001"),
    "customer_count": ("客户数", "bigint", "按统计口径去重的客户数量", "户", None, "DS-CUST-CNT-001"),
    "deposit_balance": ("存款余额", "decimal(20,2)", "统计期末有效存款账户余额", "元", None, "DS-DEP-BAL-001"),
    "corporate_deposit_balance": ("企业存款余额", "decimal(20,2)", "统计期末企业客户存款余额", "元", None, "DS-CORPDEP-BAL-001"),
    "household_deposit_balance": ("住户存款余额", "decimal(20,2)", "统计期末住户客户存款余额", "元", None, "DS-HHDEP-BAL-001"),
    "transaction_amount": ("交易金额", "decimal(20,2)", "统计期内支付交易发生金额", "元", None, "DS-TXN-AMT-001"),
    "transaction_count": ("交易笔数", "bigint", "统计期内支付交易笔数", "笔", None, "DS-TXN-CNT-001"),
    "risk_event_count": ("风险事件数", "bigint", "统计期内识别的风险事件数量", "件", None, "DS-RISK-CNT-001"),
    "risk_exposure": ("风险敞口", "decimal(20,2)", "统计期末风险暴露金额", "元", None, "DS-RISK-EXP-001"),
    "aum_balance": ("资管产品余额", "decimal(20,2)", "统计期末资产管理产品余额", "元", None, "DS-AUM-001"),
    "card_count": ("银行卡数量", "bigint", "统计期末有效银行卡数量", "张", None, "DS-CARD-CNT-001"),
    "update_time": ("更新时间", "datetime", "数据记录最后更新时间", None, None, "DS-UPDATE-001"),
    "source_system": ("来源系统", "string", "原始业务系统标识", None, None, None),
}

EXTRA_CODE_TABLES = {
    "CD_INDUSTRY": ("国民经济行业", [("C", "制造业"), ("F", "批发和零售业"), ("J", "金融业"), ("K", "房地产业"), ("L", "租赁和商务服务业")]),
    "CD_INST_TYPE": ("金融机构类型", [("STATE", "国有大型商业银行"), ("JOINT", "股份制商业银行"), ("CITY", "城市商业银行"), ("RURAL", "农村商业银行")]),
    "CD_MATURITY": ("期限区间", [("M0_6", "6个月以内"), ("M6_12", "6至12个月"), ("Y1_5", "1至5年"), ("GT5Y", "5年以上")]),
    "CD_RATE_TYPE": ("利率类型", [("FIXED", "固定利率"), ("FLOAT", "浮动利率")]),
    "CD_CHANNEL": ("业务渠道", [("COUNTER", "柜面"), ("MOBILE", "手机银行"), ("ONLINE", "网上银行"), ("API", "开放接口")]),
    "CD_PAYMENT_METHOD": ("支付方式", [("TRANSFER", "转账"), ("QUICK", "快捷支付"), ("QR", "条码支付"), ("CARD", "银行卡支付")]),
    "CD_ENTERPRISE_TYPE": ("企业类型", [("LARGE", "大型企业"), ("MEDIUM", "中型企业"), ("SMALL", "小型企业"), ("MICRO", "微型企业")]),
    "CD_PRODUCT_TYPE": ("金融产品类型", [("LOAN", "贷款产品"), ("DEPOSIT", "存款产品"), ("WEALTH", "理财产品"), ("FUND", "基金产品")]),
    "CD_CARD_TYPE": ("银行卡类型", [("DEBIT", "借记卡"), ("CREDIT", "信用卡")]),
}

EXTRA_STANDARDS = [
    ("DS-INDUSTRY-001", "行业代码标准", "industry_code", "客户所属国民经济行业分类", "string", "CD_INDUSTRY"),
    ("DS-INSTTYPE-001", "机构类型标准", "institution_type", "金融机构类型统一分类", "string", "CD_INST_TYPE"),
    ("DS-MATURITY-001", "期限区间标准", "maturity_bucket", "业务期限统一分组", "string", "CD_MATURITY"),
    ("DS-RATETYPE-001", "利率类型标准", "rate_type", "固定与浮动利率分类", "string", "CD_RATE_TYPE"),
    ("DS-CHANNEL-001", "业务渠道标准", "channel_code", "统一业务受理渠道", "string", "CD_CHANNEL"),
    ("DS-PAYMETHOD-001", "支付方式标准", "payment_method", "统一支付工具与方式", "string", "CD_PAYMENT_METHOD"),
    ("DS-ENTTYPE-001", "企业类型标准", "enterprise_type", "企业规模统一分类", "string", "CD_ENTERPRISE_TYPE"),
    ("DS-PRODTYPE-001", "产品类型标准", "product_type", "金融产品统一分类", "string", "CD_PRODUCT_TYPE"),
    ("DS-CARDTYPE-001", "银行卡类型标准", "card_type", "银行卡统一分类", "string", "CD_CARD_TYPE"),
    ("DS-CARD-CNT-001", "银行卡数量标准", "card_count", "统计期末有效银行卡数量", "bigint", None),
]

CURATED_METRICS = [
    ("metric_inclusive_loan_count", "普惠贷款笔数", "普惠贷款数量,普惠贷款合同数", "DS000008", "sum", "loan_count", "stat_month", "NON_ADDITIVE", "region_code,org_code,customer_type", "BASE", None, None, None, "统计期末符合普惠口径的有效贷款笔数。"),
    ("metric_inclusive_loan_customer_count", "普惠贷款客户数", "普惠客户数,普惠贷款户数", "DS000008", "sum", "customer_count", "stat_month", "NON_ADDITIVE", "region_code,org_code,customer_type", "BASE", None, None, None, "统计期末有普惠贷款余额的客户数。"),
    ("metric_npl_loan_count", "不良贷款笔数", "不良贷款数量,不良贷款合同数", "DS000009", "sum", "loan_count", "stat_month", "NON_ADDITIVE", "region_code,org_code,loan_type", "BASE", None, None, None, "统计期末处于不良分类的贷款笔数。"),
    ("metric_deposit_customer_count", "存款客户数", "存款户数,存款客户数量", "DS000013", "sum", "customer_count", "stat_month", "NON_ADDITIVE", "region_code,org_code,customer_type", "BASE", None, None, None, "统计期末有有效存款账户的客户数。"),
    ("metric_payment_customer_count", "支付客户数", "支付用户数,交易客户数", "DS000018", "sum", "customer_count", "stat_month", "NON_ADDITIVE", "region_code,org_code", "BASE", None, None, None, "统计期内发生支付交易的去重客户数。"),
    ("metric_risk_customer_count", "风险客户数", "风险企业数,风险客户数量", "DS000022", "sum", "customer_count", "stat_month", "NON_ADDITIVE", "region_code,org_code,risk_level", "BASE", None, None, None, "统计期末命中风险监测规则的去重客户数。"),
    ("metric_aum_customer_count", "资管客户数", "资管产品客户数,资管客户数量", "DS000024", "sum", "customer_count", "stat_month", "NON_ADDITIVE", "product_code,org_code,region_code", "BASE", None, None, None, "统计期末持有资管产品的客户数。"),
    ("metric_card_customer_count", "银行卡客户数", "持卡客户数,银行卡客户数量", "DS000026", "sum", "customer_count", "stat_month", "NON_ADDITIVE", "region_code,org_code", "BASE", None, None, None, "统计期末持有有效银行卡的客户数。"),
    ("metric_card_transaction_amount", "银行卡交易金额", "银行卡支付金额,刷卡交易金额", "DS000026", "sum", "transaction_amount", "stat_month", "ADDITIVE", "region_code,org_code", "BASE", None, None, None, "统计期内银行卡交易发生金额。"),
    ("metric_card_transaction_count", "银行卡交易笔数", "银行卡支付笔数,刷卡交易笔数", "DS000026", "sum", "transaction_count", "stat_month", "ADDITIVE", "region_code,org_code", "BASE", None, None, None, "统计期内银行卡交易笔数。"),
    ("metric_inclusive_loan_ratio", "普惠贷款余额占比", "普惠贷款占比,普惠贷款比重", "DS000004", "ratio", "inclusive_loan_balance", "stat_month", "NON_ADDITIVE", "region_code,org_code,customer_type,loan_type", "RATIO", "metric_inclusive_loan_balance", "metric_loan_balance", "metric_inclusive_loan_balance / metric_loan_balance", "同一统计期、同一维度下普惠贷款余额占各项贷款余额的比例。"),
    ("metric_overdue_loan_ratio", "逾期贷款余额占比", "逾期贷款占比,逾期率", "DS000004", "ratio", "overdue_balance", "stat_month", "NON_ADDITIVE", "region_code,org_code,loan_type", "RATIO", "metric_overdue_balance", "metric_loan_balance", "metric_overdue_balance / metric_loan_balance", "同一统计期、同一维度下逾期贷款余额占各项贷款余额的比例。"),
    ("metric_corporate_deposit_share", "企业存款占比", "单位存款占比,企业存款比重", "DS000013", "ratio", "corporate_deposit_balance", "stat_month", "NON_ADDITIVE", "region_code,org_code,currency_cd", "RATIO", "metric_corporate_deposit_balance", "metric_deposit_balance", "metric_corporate_deposit_balance / metric_deposit_balance", "同一统计期企业存款余额占各项存款余额的比例。"),
    ("metric_household_deposit_share", "住户存款占比", "居民存款占比,个人存款占比", "DS000013", "ratio", "household_deposit_balance", "stat_month", "NON_ADDITIVE", "region_code,org_code,currency_cd", "RATIO", "metric_household_deposit_balance", "metric_deposit_balance", "metric_household_deposit_balance / metric_deposit_balance", "同一统计期住户存款余额占各项存款余额的比例。"),
    ("metric_avg_payment_amount", "笔均支付金额", "平均每笔支付金额,支付客单价", "DS000018", "ratio", "transaction_amount", "stat_month", "ADDITIVE", "region_code,org_code,currency_cd", "RATIO", "metric_payment_amount", "metric_payment_count", "metric_payment_amount / metric_payment_count", "统计期内支付交易金额除以支付交易笔数。"),
]

GUANGDONG_REGIONS = [
    ("440000", "广东省"), ("440100", "广州市"), ("440200", "韶关市"), ("440300", "深圳市"),
    ("440400", "珠海市"), ("440500", "汕头市"), ("440600", "佛山市"), ("440700", "江门市"),
    ("440800", "湛江市"), ("440900", "茂名市"), ("441200", "肇庆市"), ("441300", "惠州市"),
    ("441400", "梅州市"), ("441500", "汕尾市"), ("441600", "河源市"), ("441700", "阳江市"),
    ("441800", "清远市"), ("441900", "东莞市"), ("442000", "中山市"), ("445100", "潮州市"),
    ("445200", "揭阳市"), ("445300", "云浮市"),
]


def _fields_for(catalog: str, layer: str) -> list[str]:
    time_field = "stat_month" if layer in {"DWS", "ADS"} else "stat_date"
    detail = layer in {"ODS", "DWD"}
    if catalog == "FIN.LOAN":
        identifiers = ["cust_id", "contract_id", "account_id"] if detail else []
        return [time_field, "org_code", "region_code", *identifiers, "customer_type", "loan_type", "industry_code", "maturity_bucket", "rate_type", "currency_cd", "status", "loan_balance", "inclusive_loan_balance", "npl_balance", "overdue_balance", "new_loan_amount", "loan_count", "customer_count", "update_time"]
    if catalog == "FIN.DEP":
        identifiers = ["cust_id", "account_id"] if detail else []
        return [time_field, "org_code", "region_code", *identifiers, "customer_type", "industry_code", "currency_cd", "status", "deposit_balance", "corporate_deposit_balance", "household_deposit_balance", "customer_count", "update_time"]
    if catalog == "FIN.PAY":
        identifiers = ["cust_id", "account_id"] if detail else []
        return [time_field, "org_code", "region_code", *identifiers, "channel_code", "payment_method", "currency_cd", "status", "transaction_amount", "transaction_count", "customer_count", "update_time"]
    if catalog == "FIN.RISK":
        identifiers = ["cust_id"] if detail else []
        return [time_field, "org_code", "region_code", *identifiers, "industry_code", "risk_level", "status", "npl_balance", "overdue_balance", "risk_event_count", "risk_exposure", "customer_count", "update_time"]
    if catalog == "FIN.ASSET":
        return [time_field, "org_code", "region_code", "product_code", "product_type", "currency_cd", "status", "aum_balance", "customer_count", "update_time"]
    if catalog == "FIN.ENT":
        identifiers = ["cust_id"] if detail else []
        return [time_field, "region_code", *identifiers, "enterprise_type", "industry_code", "risk_level", "status", "risk_event_count", "risk_exposure", "customer_count", "update_time"]
    if catalog == "FIN.REG":
        return [time_field, "org_code", "region_code", "institution_type", "currency_cd", "loan_balance", "deposit_balance", "risk_exposure", "transaction_amount", "customer_count", "update_time"]
    if catalog == "FIN.CARD":
        identifiers = ["cust_id", "account_id"] if detail else []
        return [time_field, "org_code", "region_code", *identifiers, "card_type", "channel_code", "status", "card_count", "transaction_amount", "transaction_count", "customer_count", "update_time"]
    if catalog == "COMMON.ORG":
        return ["org_code", "region_code", "institution_type", "status", "update_time"]
    if catalog == "COMMON.CUST":
        return ["customer_type", "enterprise_type", "industry_code", "status", "update_time"]
    if catalog == "COMMON.PROD":
        return ["product_code", "product_type", "loan_type", "currency_cd", "status", "update_time"]
    return ["stat_date", "stat_month", "status", "update_time"]


def _grain(catalog: str, layer: str) -> str:
    if catalog.startswith("COMMON."):
        return "主数据代码值"
    if layer == "ODS":
        return "业务记录×日"
    if layer == "DWD":
        return "机构×客户×业务记录×日"
    if layer == "DWS":
        return "地区×机构×月"
    return "地区×月"


def _upsert_code_table(db, code: str, name: str, values: list[tuple[str, str]], asset_id: str) -> None:
    table = db.execute(select(CodeTable).where(CodeTable.code_table_no == code)).scalar_one_or_none()
    if table is None:
        table = CodeTable(asset_id=asset_id, code_table_no=code, code_table_name=name)
        db.add(table)
    table.code_table_name = name
    table.description = f"{name}统一代码表"
    table.version = "2026.1"
    table.owner = "数据资产部"
    table.status = "EFFECTIVE"
    db.execute(delete(CodeValue).where(CodeValue.code_table_no == code))
    for value, label in values:
        db.add(CodeValue(code_table_no=code, code_value=value, code_name=label, description=f"{label}标准码值"))


def _upsert_standard(db, spec: tuple[str, str, str, str, str, str | None], idx: int) -> None:
    no, name, en_name, definition, data_type, code_table = spec
    standard = db.execute(select(DataStandard).where(DataStandard.standard_no == no)).scalar_one_or_none()
    if standard is None:
        standard = DataStandard(asset_id=f"ST8{idx:05d}", standard_no=no, standard_name=name)
        db.add(standard)
    standard.standard_name = name
    standard.en_name = en_name
    standard.category_code = "STD.FIELD"
    standard.business_definition = definition
    standard.business_rule = "字段值应符合统一标准定义；有码表时必须使用有效码值。"
    standard.data_type = data_type
    standard.code_table_no = code_table
    standard.owner_dept = "数据资产部"
    standard.version = "2026.1"
    standard.status = "EFFECTIVE"


def _metric_filters(source_dataset_id: str) -> str | None:
    if source_dataset_id in {"DS000004", "DS000013", "DS000018"}:
        return json.dumps([{"field": "currency_cd", "op": "eq", "value": "CNY", "label": "人民币"}], ensure_ascii=False)
    return None


def main() -> None:
    assert sum(len(items) for items in PORTFOLIO.values()) == 57
    with SessionLocal() as db:
        # Expand reference data first so every new field points at an existing governed object.
        region_table = db.execute(select(CodeTable).where(CodeTable.code_table_no == "CD_REGION")).scalar_one()
        _upsert_code_table(db, "CD_REGION", "行政区划", GUANGDONG_REGIONS, region_table.asset_id)
        for idx, (code, (name, values)) in enumerate(EXTRA_CODE_TABLES.items(), 1):
            _upsert_code_table(db, code, name, values, f"CT8{idx:05d}")
        for idx, spec in enumerate(EXTRA_STANDARDS, 1):
            _upsert_standard(db, spec, idx)

        # Replace generated filler assets with coherent four-stage business pipelines.
        portfolio_ids = [f"DS{num:06d}" for num in range(33, 261)]
        db.execute(delete(Column).where(Column.dataset_id.in_(portfolio_ids)))
        db.execute(
            delete(TableLineage).where(
                or_(TableLineage.src_asset_id.in_(portfolio_ids), TableLineage.dst_asset_id.in_(portfolio_ids))
            )
        )

        num = 33
        pipeline_edges: list[tuple[str, str, str]] = []
        for catalog, subjects in PORTFOLIO.items():
            token, owner, source_name, business_area = DOMAIN_PROFILE[catalog]
            stages = REFERENCE_STAGES if catalog.startswith("COMMON.") else BUSINESS_STAGES
            for slug, subject_name in subjects:
                stage_ids: list[str] = []
                for layer, suffix, role_name in stages:
                    dataset_id = f"DS{num:06d}"
                    dataset = db.get(Dataset, dataset_id)
                    if dataset is None:
                        raise RuntimeError(f"missing generated dataset {dataset_id}")
                    stage_ids.append(dataset_id)
                    dataset.table_name = f"stat_prod.{layer.lower()}_{token}_{slug}_{suffix}"
                    dataset.biz_name = f"{subject_name}{role_name}"
                    dataset.layer_code = layer
                    dataset.catalog_code = catalog
                    dataset.biz_definition = f"沉淀{subject_name}相关的{business_area}数据，用于统一统计、分析与数据服务。"
                    dataset.stat_caliber = (
                        "按统计期末有效业务记录归集；余额类字段为时点值，不跨期直接求和；发生额类字段按统计期累计。"
                        if layer in {"DWS", "ADS"}
                        else "按业务发生记录归集，保留统一机构、地区、客户和产品分类，异常及无效记录按状态字段识别。"
                    )
                    dataset.data_source_desc = f"来源：{source_name}；经 DataControl 标准字段与码表口径映射后形成。"
                    dataset.grain = _grain(catalog, layer)
                    dataset.usage_notes = (
                        "用于月度统计与趋势分析；余额指标查询应指定统计月份或使用最新可用月份。"
                        if layer in {"DWS", "ADS"}
                        else "用于明细追溯和主题加工，不建议直接作为跨期汇总口径。"
                    )
                    dataset.tech_owner = "数据资产部"
                    dataset.biz_owner = owner
                    dataset.owner_dept = owner
                    dataset.update_freq = "MONTHLY" if layer in {"DWS", "ADS"} else "DAILY"
                    dataset.schedule_desc = "每月1日 03:10" if layer in {"DWS", "ADS"} else "每日 02:30"
                    dataset.schedule_node = f"dw_{token}_{slug}_{suffix}"
                    dataset.status = "ONLINE"
                    dataset.is_common = catalog.startswith("COMMON.")

                    fields = _fields_for(catalog, layer)
                    for ordinal, field_name in enumerate(fields, 1):
                        cn_name, data_type, definition, unit, code_table, standard_no = FIELD_SPECS[field_name]
                        db.add(
                            Column(
                                asset_id=f"RF{num:06d}{ordinal:02d}",
                                dataset_id=dataset_id,
                                column_name=field_name,
                                ordinal_no=ordinal,
                                cn_name=cn_name,
                                data_type=data_type,
                                biz_definition=definition,
                                unit=unit,
                                code_table_no=code_table,
                                standard_no=standard_no,
                            )
                        )
                    num += 1
                for left, right in zip(stage_ids, stage_ids[1:]):
                    pipeline_edges.append((left, right, f"etl_{token}_{slug}_{left[-3:]}_{right[-3:]}"))

        if num != 261:
            raise RuntimeError(f"portfolio allocation ended at {num}, expected 261")
        for src, dst, task_name in pipeline_edges:
            db.add(TableLineage(src_asset_id=src, dst_asset_id=dst, task_name=task_name, evidence="CONFIRMED"))

        # Improve the 32 golden assets as well: remove acceptance/demo wording from the product surface.
        golden = db.execute(select(Dataset).where(Dataset.asset_id.not_in(portfolio_ids))).scalars().all()
        for dataset in golden:
            dataset.biz_definition = f"{dataset.biz_name}，按统一字段标准、统计口径和维度定义维护。"
            dataset.data_source_desc = "来源：对应业务系统（模拟）；经标准化加工后进入统计数仓。"
            if dataset.layer_code in {"DWS", "ADS"}:
                dataset.usage_notes = "适用于受治理指标计算与月度分析；余额类指标必须限定单个统计期。"

        # Remove the former volume-only duplicate metrics and replace them with distinct business metrics.
        generated = db.execute(select(Metric)).scalars().all()
        for metric in generated:
            if re.fullmatch(r"metric_(?:loan_balance|loan_count|customer_count)_\d{3}", metric.metric_code):
                db.delete(metric)

        for idx, spec in enumerate(CURATED_METRICS, 1):
            (
                code, name, aliases, source_id, aggregation, measure, time_field, additivity,
                dimensions, kind, numerator, denominator, formula, caliber,
            ) = spec
            existing = db.execute(select(Metric).where(Metric.metric_code == code)).scalar_one_or_none()
            metric = existing or Metric(asset_id=f"MT8{idx:05d}", metric_code=code, metric_name=name, source_dataset_id=source_id, aggregation=aggregation, measure_column=measure, time_field=time_field)
            if existing is None:
                db.add(metric)
            metric.metric_name = name
            metric.aliases = aliases
            metric.biz_definition = f"{name}，由受治理数据资产按统一统计口径计算。"
            metric.source_dataset_id = source_id
            metric.stat_system_code = "SS-FIN-2026"
            metric.aggregation = aggregation
            metric.measure_column = measure
            metric.time_field = time_field
            metric.time_additivity = additivity
            metric.caliber_desc = caliber
            metric.valid_dimensions = dimensions
            metric.metric_kind = kind
            metric.numerator_metric_code = numerator
            metric.denominator_metric_code = denominator
            metric.formula = formula
            metric.time_grain = "MONTH"
            metric.latest_strategy = "MAX"
            metric.mandatory_filters = _metric_filters(source_id)
            metric.semantic_notes = "仅使用 DataControl 内部治理语义；维度、时间和码值必须来自已登记元数据。"
            metric.status = "ONLINE"

        # Clean seed artifacts that are visible in dataset/reference detail pages.
        systems = db.execute(select(StatisticalSystem)).scalars().all()
        for system in systems:
            system.description = f"{system.stat_system_name}的口径、指标和报送要求。"

        code_values = db.execute(select(CodeValue)).scalars().all()
        for value in code_values:
            value.description = f"{value.code_name}标准码值"
        code_tables = db.execute(select(CodeTable)).scalars().all()
        for table in code_tables:
            table.description = f"{table.code_table_name}统一代码表"

        datasets = {item.asset_id: item for item in db.execute(select(Dataset)).scalars().all()}
        common_links = db.execute(select(CommonSqlDataset)).scalars().all()
        sql_to_dataset = {link.sql_code: link.dataset_id for link in common_links}
        common_sqls = db.execute(select(CommonSql)).scalars().all()
        for item in common_sqls:
            dataset = datasets.get(sql_to_dataset.get(item.sql_code, ""))
            if dataset is None:
                continue
            time_field = "stat_month" if any(column.column_name == "stat_month" for column in db.execute(select(Column).where(Column.dataset_id == dataset.asset_id)).scalars()) else "stat_date"
            item.title = f"{dataset.biz_name}常用查询"
            item.question = f"如何查询{dataset.biz_name}的最新可用数据？"
            item.sql_text = f"SELECT * FROM {dataset.table_name} WHERE {time_field} = '${{bizdate}}' LIMIT 100;"
            item.description = "常用查询模板；运行前应根据统计期和业务口径补充筛选条件。"

        changes = db.execute(select(ChangeLog)).scalars().all()
        for change in changes:
            dataset = datasets.get(change.dataset_id)
            if dataset is not None:
                change.content = f"{dataset.biz_name}完成{change.change_type.lower()}类元数据维护，已同步资产目录。"

        db.commit()
        print(
            "P2 realistic corpus enriched: 57 coherent business subjects / 228 portfolio assets, "
            f"{len(pipeline_edges)} confirmed pipeline edges, {len(CURATED_METRICS)} curated extra metrics"
        )


if __name__ == "__main__":
    main()
