from __future__ import annotations

import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete

from backend.app.db.models import Base, Catalog, CodeTable, CodeValue, Column, Dataset, Metric, TableLineage
from backend.app.db.session import SessionLocal, engine
from backend.app.search.engine import SearchEngine

R = random.Random(20260921)
NOW = datetime.now(UTC).replace(tzinfo=None)

CATALOGS = [
    ("FIN.LOAN", "贷款统计"), ("FIN.DEP", "存款统计"), ("FIN.PAY", "支付结算"),
    ("FIN.RISK", "风险监测"), ("FIN.ASSET", "资管产品"), ("FIN.ENT", "企业信息"),
    ("FIN.REG", "监管报送"), ("COMMON.ORG", "公共维度"), ("COMMON.CUST", "客户维度"),
    ("COMMON.PROD", "产品维度"), ("COMMON.DATE", "日期维度"), ("FIN.CARD", "银行卡统计"),
]

# name, Chinese name, type, definition, unit, code table, standard
BASE_COLUMNS = {
    "stat_date": ("统计日期", "date", "数据所属统计日期", None, None, "DS-DATE-001"),
    "stat_month": ("统计月份", "string", "YYYY-MM 格式统计月份", None, None, "DS-MONTH-001"),
    "org_code": ("机构编码", "string", "报送或经营机构唯一编码", None, "CD_ORG", "DS-ORG-001"),
    "region_code": ("地区编码", "string", "国家行政区划代码", None, "CD_REGION", "DS-REGION-001"),
    "customer_type": ("客户类型", "string", "客户分类代码", None, "CD_CUSTOMER_TYPE", "DS-CUSTTYPE-001"),
    "loan_type": ("贷款类型", "string", "贷款业务分类代码", None, "CD_LOAN_TYPE", "DS-LOANTYPE-001"),
    "currency_cd": ("币种", "string", "币种代码", None, "CD_CURRENCY", "DS-CURRENCY-001"),
    "product_code": ("产品编码", "string", "金融产品唯一编码", None, None, None),
    "cust_id": ("客户编号", "string", "脱敏后的客户唯一标识", None, None, None),
    "contract_id": ("合同编号", "string", "贷款或存款合同唯一标识", None, None, None),
    "account_id": ("账户编号", "string", "账户唯一标识", None, None, None),
    "status": ("业务状态", "string", "统一业务状态码", None, "CD_STATUS", "DS-STATUS-001"),
    "risk_level": ("风险等级", "string", "内部风险分类等级", None, "CD_RISK_LEVEL", "DS-RISK-001"),
    "loan_balance": ("贷款余额", "decimal(20,2)", "统计期末尚未结清的贷款本金余额", "元", None, "DS-AMT-001"),
    "inclusive_loan_balance": ("普惠贷款余额", "decimal(20,2)", "统计期末符合普惠口径的贷款余额", "元", None, "DS-AMT-001"),
    "npl_balance": ("不良贷款余额", "decimal(20,2)", "统计期末五级分类后三类贷款余额", "元", None, "DS-AMT-001"),
    "overdue_balance": ("逾期贷款余额", "decimal(20,2)", "统计期末存在逾期状态的贷款余额", "元", None, "DS-AMT-001"),
    "new_loan_amount": ("新增贷款金额", "decimal(20,2)", "统计期内新发放贷款金额", "元", None, "DS-AMT-001"),
    "loan_count": ("贷款笔数", "bigint", "贷款合同或账户数量", "笔", None, None),
    "customer_count": ("客户数", "bigint", "去重客户数量", "户", None, None),
    "deposit_balance": ("存款余额", "decimal(20,2)", "统计期末存款账户余额", "元", None, "DS-AMT-001"),
    "corporate_deposit_balance": ("企业存款余额", "decimal(20,2)", "统计期末企业客户存款余额", "元", None, "DS-AMT-001"),
    "household_deposit_balance": ("住户存款余额", "decimal(20,2)", "统计期末住户客户存款余额", "元", None, "DS-AMT-001"),
    "transaction_amount": ("交易金额", "decimal(20,2)", "统计期内支付交易发生金额", "元", None, "DS-AMT-001"),
    "transaction_count": ("交易笔数", "bigint", "统计期内支付交易笔数", "笔", None, None),
    "risk_event_count": ("风险事件数", "bigint", "统计期内识别的风险事件数量", "件", None, None),
    "risk_exposure": ("风险敞口", "decimal(20,2)", "统计期末风险暴露金额", "元", None, "DS-AMT-001"),
    "aum_balance": ("资管产品余额", "decimal(20,2)", "统计期末资产管理产品余额", "元", None, "DS-AMT-001"),
    "card_count": ("银行卡数量", "bigint", "有效银行卡数量", "张", None, None),
    "update_time": ("更新时间", "datetime", "数据记录最后更新时间", None, None, None),
    "source_system": ("来源系统", "string", "原始业务系统标识", None, None, None),
}


def cols(*names: str) -> list[str]:
    return list(names)


# Stable IDs 1-32 are semantic goldens. DS000001 -> DS000004 is deliberately preserved for P3 relation acceptance.
GOLDEN_DATASETS = [
    (1, "stat_prod.ods_loan_contract", "贷款合同原始明细", "ODS", "FIN.LOAN", "客户×合同", cols("stat_date","org_code","region_code","cust_id","contract_id","loan_type","currency_cd","status","loan_balance","new_loan_amount","update_time","source_system")),
    (2, "stat_prod.dwd_loan_contract_detail", "贷款合同标准明细", "DWD", "FIN.LOAN", "客户×合同×日", cols("stat_date","org_code","region_code","cust_id","contract_id","loan_type","customer_type","currency_cd","status","loan_balance","inclusive_loan_balance","npl_balance","overdue_balance","new_loan_amount","update_time")),
    (3, "stat_prod.dws_loan_region_day", "地区贷款日汇总", "DWS", "FIN.LOAN", "地区×日", cols("stat_date","region_code","currency_cd","loan_balance","inclusive_loan_balance","npl_balance","overdue_balance","new_loan_amount","loan_count","customer_count","update_time")),
    (4, "stat_prod.dws_loan_region_month", "地区贷款月度汇总", "DWS", "FIN.LOAN", "地区×机构×客户类型×贷款类型×币种×月", cols("stat_month","region_code","org_code","customer_type","loan_type","currency_cd","loan_balance","inclusive_loan_balance","npl_balance","overdue_balance","new_loan_amount","loan_count","customer_count","update_time")),
    (5, "stat_prod.dws_loan_org_month", "机构贷款月度汇总", "DWS", "FIN.LOAN", "机构×月", cols("stat_month","org_code","region_code","currency_cd","loan_balance","inclusive_loan_balance","npl_balance","overdue_balance","new_loan_amount","loan_count","customer_count","update_time")),
    (6, "stat_prod.ads_loan_monthly_report", "金融统计贷款月报", "ADS", "FIN.REG", "地区×月", cols("stat_month","region_code","loan_balance","inclusive_loan_balance","npl_balance","loan_count","customer_count","update_time")),
    (7, "stat_prod.dwd_loan_balance_snapshot", "贷款余额日快照", "DWD", "FIN.LOAN", "账户×日", cols("stat_date","org_code","region_code","cust_id","account_id","contract_id","loan_type","customer_type","currency_cd","status","loan_balance","npl_balance","overdue_balance","update_time")),
    (8, "stat_prod.dws_inclusive_loan_month", "普惠贷款月度汇总", "DWS", "FIN.LOAN", "地区×机构×月", cols("stat_month","region_code","org_code","customer_type","loan_type","inclusive_loan_balance","loan_count","customer_count","update_time")),
    (9, "stat_prod.dws_npl_loan_month", "不良贷款月度汇总", "DWS", "FIN.RISK", "地区×机构×月", cols("stat_month","region_code","org_code","loan_type","npl_balance","overdue_balance","loan_count","update_time")),
    (10, "stat_prod.ads_loan_region_analysis", "地区贷款余额分析", "ADS", "FIN.LOAN", "地区×月", cols("stat_month","region_code","loan_balance","inclusive_loan_balance","npl_balance","new_loan_amount","update_time")),
    (11, "stat_prod.ods_deposit_account", "存款账户原始明细", "ODS", "FIN.DEP", "账户×日", cols("stat_date","org_code","region_code","cust_id","account_id","customer_type","currency_cd","status","deposit_balance","update_time","source_system")),
    (12, "stat_prod.dwd_deposit_account_detail", "存款账户标准明细", "DWD", "FIN.DEP", "账户×日", cols("stat_date","org_code","region_code","cust_id","account_id","customer_type","currency_cd","status","deposit_balance","update_time")),
    (13, "stat_prod.dws_deposit_region_month", "地区存款月度汇总", "DWS", "FIN.DEP", "地区×客户类型×月", cols("stat_month","region_code","org_code","customer_type","currency_cd","deposit_balance","corporate_deposit_balance","household_deposit_balance","customer_count","update_time")),
    (14, "stat_prod.dws_deposit_org_month", "机构存款月度汇总", "DWS", "FIN.DEP", "机构×月", cols("stat_month","org_code","region_code","deposit_balance","corporate_deposit_balance","household_deposit_balance","customer_count","update_time")),
    (15, "stat_prod.ads_deposit_monthly_report", "金融统计存款月报", "ADS", "FIN.REG", "地区×月", cols("stat_month","region_code","deposit_balance","corporate_deposit_balance","household_deposit_balance","update_time")),
    (16, "stat_prod.ods_payment_txn", "支付交易原始流水", "ODS", "FIN.PAY", "交易×日", cols("stat_date","org_code","region_code","cust_id","account_id","currency_cd","status","transaction_amount","update_time","source_system")),
    (17, "stat_prod.dwd_payment_txn_detail", "支付交易标准明细", "DWD", "FIN.PAY", "交易×日", cols("stat_date","org_code","region_code","cust_id","account_id","currency_cd","status","transaction_amount","update_time")),
    (18, "stat_prod.dws_payment_region_month", "地区支付交易月汇总", "DWS", "FIN.PAY", "地区×机构×月", cols("stat_month","region_code","org_code","currency_cd","transaction_amount","transaction_count","customer_count","update_time")),
    (19, "stat_prod.ads_payment_monitor", "支付业务监测月报", "ADS", "FIN.PAY", "地区×月", cols("stat_month","region_code","transaction_amount","transaction_count","update_time")),
    (20, "stat_prod.ods_enterprise_risk_event", "企业风险事件原始明细", "ODS", "FIN.RISK", "企业×事件", cols("stat_date","region_code","cust_id","risk_level","status","risk_event_count","risk_exposure","update_time","source_system")),
    (21, "stat_prod.dwd_enterprise_risk_detail", "企业风险事件标准明细", "DWD", "FIN.RISK", "企业×事件×日", cols("stat_date","region_code","org_code","cust_id","risk_level","status","risk_event_count","risk_exposure","update_time")),
    (22, "stat_prod.dws_risk_region_month", "地区风险事件月汇总", "DWS", "FIN.RISK", "地区×风险等级×月", cols("stat_month","region_code","org_code","risk_level","risk_event_count","risk_exposure","customer_count","update_time")),
    (23, "stat_prod.ads_risk_monitor", "金融风险监测月报", "ADS", "FIN.RISK", "地区×月", cols("stat_month","region_code","risk_event_count","risk_exposure","update_time")),
    (24, "stat_prod.dws_asset_product_month", "资管产品月度汇总", "DWS", "FIN.ASSET", "产品×机构×月", cols("stat_month","product_code","org_code","region_code","currency_cd","aum_balance","customer_count","update_time")),
    (25, "stat_prod.ads_asset_management_report", "资产管理业务月报", "ADS", "FIN.ASSET", "机构×月", cols("stat_month","org_code","aum_balance","customer_count","update_time")),
    (26, "stat_prod.dws_card_region_month", "银行卡地区月度汇总", "DWS", "FIN.CARD", "地区×机构×月", cols("stat_month","region_code","org_code","card_count","customer_count","transaction_amount","transaction_count","update_time")),
    (27, "stat_prod.dim_region", "行政区划维度", "DIM", "COMMON.ORG", "地区", cols("region_code","status","update_time")),
    (28, "stat_prod.dim_org", "金融机构维度", "DIM", "COMMON.ORG", "机构", cols("org_code","region_code","status","update_time")),
    (29, "stat_prod.dim_customer_type", "客户类型维度", "DIM", "COMMON.CUST", "客户类型", cols("customer_type","status","update_time")),
    (30, "stat_prod.dim_loan_type", "贷款类型维度", "DIM", "COMMON.PROD", "贷款类型", cols("loan_type","status","update_time")),
    (31, "stat_prod.dim_currency", "币种维度", "DIM", "COMMON.PROD", "币种", cols("currency_cd","status","update_time")),
    (32, "stat_prod.dim_calendar", "统计日期维度", "DIM", "COMMON.DATE", "日期", cols("stat_date","stat_month","status","update_time")),
]

CORE_METRICS = [
    ("metric_loan_balance", "各项贷款余额", "贷款余额,本期贷款余额,当前贷款余额,最新贷款余额,期末贷款余额,贷款规模,各项贷款", 4, "sum", "loan_balance", "stat_month", "NON_ADDITIVE", "region_code,org_code,customer_type,loan_type,currency_cd", "统计期末有效贷款本金余额；本期/当前/最新均取可用统计期最大值。"),
    ("metric_inclusive_loan_balance", "普惠贷款余额", "普惠余额,本期普惠贷款余额,普惠贷款规模", 4, "sum", "inclusive_loan_balance", "stat_month", "NON_ADDITIVE", "region_code,org_code,customer_type,loan_type", "统计期末符合普惠金融专项统计口径的贷款余额。"),
    ("metric_npl_balance", "不良贷款余额", "不良余额,本期不良贷款余额,不良贷款规模", 4, "sum", "npl_balance", "stat_month", "NON_ADDITIVE", "region_code,org_code,loan_type", "统计期末五级分类中次级、可疑、损失类贷款余额。"),
    ("metric_overdue_balance", "逾期贷款余额", "逾期余额,本期逾期贷款余额", 4, "sum", "overdue_balance", "stat_month", "NON_ADDITIVE", "region_code,org_code,loan_type", "统计期末存在逾期状态的贷款余额。"),
    ("metric_new_loan_amount", "新增贷款金额", "贷款新增额,本期新增贷款,新发放贷款金额", 4, "sum", "new_loan_amount", "stat_month", "ADDITIVE", "region_code,org_code,customer_type,loan_type", "统计期内新发放贷款金额，可按期间累加。"),
    ("metric_loan_count", "贷款笔数", "贷款数量,贷款合同数,本期贷款笔数", 4, "sum", "loan_count", "stat_month", "NON_ADDITIVE", "region_code,org_code,customer_type,loan_type", "统计期末有效贷款合同/账户笔数。"),
    ("metric_loan_customer_count", "贷款客户数", "贷款户数,贷款人数,本期贷款客户数", 4, "sum", "customer_count", "stat_month", "NON_ADDITIVE", "region_code,org_code,customer_type,loan_type", "统计期末有有效贷款余额的客户数。"),
    ("metric_deposit_balance", "各项存款余额", "存款余额,本期存款余额,当前存款余额,期末存款余额,存款规模", 13, "sum", "deposit_balance", "stat_month", "NON_ADDITIVE", "region_code,org_code,customer_type,currency_cd", "统计期末有效存款账户余额。"),
    ("metric_corporate_deposit_balance", "企业存款余额", "公司存款余额,单位存款余额,本期企业存款余额", 13, "sum", "corporate_deposit_balance", "stat_month", "NON_ADDITIVE", "region_code,org_code,currency_cd", "统计期末企业客户存款余额。"),
    ("metric_household_deposit_balance", "住户存款余额", "个人存款余额,居民存款余额,本期住户存款余额", 13, "sum", "household_deposit_balance", "stat_month", "NON_ADDITIVE", "region_code,org_code,currency_cd", "统计期末住户客户存款余额。"),
    ("metric_payment_amount", "支付交易金额", "支付金额,交易金额,本期支付交易金额", 18, "sum", "transaction_amount", "stat_month", "ADDITIVE", "region_code,org_code,currency_cd", "统计期内支付交易发生金额。"),
    ("metric_payment_count", "支付交易笔数", "交易笔数,支付笔数,本期交易笔数", 18, "sum", "transaction_count", "stat_month", "ADDITIVE", "region_code,org_code", "统计期内支付交易笔数。"),
    ("metric_risk_event_count", "企业风险事件数", "风险事件数,本期风险事件,企业风险数量", 22, "sum", "risk_event_count", "stat_month", "ADDITIVE", "region_code,org_code,risk_level", "统计期内归集的企业风险事件数量。"),
    ("metric_risk_exposure", "风险敞口", "风险暴露,本期风险敞口", 22, "sum", "risk_exposure", "stat_month", "NON_ADDITIVE", "region_code,org_code,risk_level", "统计期末风险暴露金额。"),
    ("metric_aum_balance", "资管产品余额", "资产管理余额,理财余额,本期资管余额", 24, "sum", "aum_balance", "stat_month", "NON_ADDITIVE", "product_code,org_code,region_code,currency_cd", "统计期末资产管理产品余额。"),
    ("metric_card_count", "银行卡数量", "银行卡张数,本期银行卡数量", 26, "sum", "card_count", "stat_month", "NON_ADDITIVE", "region_code,org_code", "统计期末有效银行卡数量。"),
]

CODE_TABLES = {
    "CD_REGION": [("440100","广州市"),("440300","深圳市"),("440600","佛山市"),("441900","东莞市"),("440500","汕头市"),("440700","江门市"),("440800","湛江市"),("441300","惠州市")],
    "CD_ORG": [("ORG001","深圳分行"),("ORG002","广州分行"),("ORG003","佛山分行"),("ORG004","东莞分行")],
    "CD_STATUS": [("normal","正常"),("overdue","逾期"),("settled","结清"),("cancelled","已取消"),("invalid","无效")],
    "CD_CURRENCY": [("CNY","人民币"),("USD","美元"),("EUR","欧元"),("HKD","港币")],
    "CD_RISK_LEVEL": [("A","低风险"),("B","较低风险"),("C","中风险"),("D","较高风险"),("E","高风险")],
    "CD_CUSTOMER_TYPE": [("CORP","企业"),("SME","小微企业"),("PERSONAL","个人"),("GOV","政府及事业单位")],
    "CD_LOAN_TYPE": [("GENERAL","一般贷款"),("INCLUSIVE","普惠贷款"),("MORTGAGE","按揭贷款"),("CONSUMER","消费贷款"),("AGRI","涉农贷款")],
}


def aid(prefix: str, n: int, width: int = 6) -> str:
    return f"{prefix}{n:0{width}d}"


def add_column(db, dataset_id: str, column_id: int, ordinal: int, name: str) -> int:
    cn, typ, definition, unit, code_table, standard = BASE_COLUMNS[name]
    db.add(Column(asset_id=aid("FD", column_id, 7), dataset_id=dataset_id, column_name=name,
                  ordinal_no=ordinal, cn_name=cn, data_type=typ, biz_definition=definition,
                  unit=unit, code_table_no=code_table, standard_no=standard))
    return column_id + 1


def add_dataset(db, spec, column_id: int) -> tuple[Dataset, int]:
    num, table, biz, layer, catalog, grain, column_names = spec
    is_monthly = "stat_month" in column_names
    ds = Dataset(
        asset_id=aid("DS", num), table_name=table, biz_name=biz, workspace_code="stat_prod",
        layer_code=layer, catalog_code=catalog,
        biz_definition=f"{biz}。这是 DataControl P3 验收语义资产，字段、指标、统计周期和维度已做一致性约束。",
        stat_caliber="按有效业务状态归集；金额统一为人民币。月度余额类指标为期末快照，不跨月直接相加。" if is_monthly else "按统计日期归集有效记录；金额统一为人民币。",
        data_source_desc="由上游核心业务数据经标准化加工形成；仅用于合成测试与 Agent 能力验收。",
        grain=grain, usage_notes="本期、当前、最新一期统一解释为该表可用统计期最大值。" if is_monthly else "日粒度查询应显式指定统计日期或使用最新可用日期。",
        tech_owner="数据资产部", biz_owner="统计业务组", owner_dept="数据资产部",
        update_freq="MONTHLY" if is_monthly else "DAILY", schedule_desc="每月1日03:10" if is_monthly else "每日02:30",
        schedule_node=f"dw_{table.split('.')[-1]}", status="ONLINE", is_common=num <= 32,
        storage_bytes=R.randint(50_000_000, 12_000_000_000), row_count=R.randint(20_000, 50_000_000),
        data_updated_at=NOW - timedelta(hours=R.randint(2, 72)), updated_at=NOW - timedelta(days=R.randint(0, 15)),
    )
    db.add(ds)
    for ordinal, name in enumerate(column_names, 1):
        column_id = add_column(db, ds.asset_id, column_id, ordinal, name)
    return ds, column_id


def build_noise_spec(num: int):
    catalog, catalog_name = CATALOGS[(num - 33) % len(CATALOGS)]
    layer = ["ODS", "DWD", "DWS", "ADS", "DIM"][(num - 33) % 5]
    stem = catalog.split(".")[-1].lower()
    monthly = layer in {"DWS", "ADS"}
    metric_pool = {
        "FIN.LOAN": ["loan_balance","new_loan_amount","loan_count","customer_count"],
        "FIN.DEP": ["deposit_balance","customer_count"],
        "FIN.PAY": ["transaction_amount","transaction_count","customer_count"],
        "FIN.RISK": ["risk_event_count","risk_exposure","customer_count"],
        "FIN.ASSET": ["aum_balance","customer_count"],
        "FIN.CARD": ["card_count","transaction_amount","transaction_count"],
    }.get(catalog, ["customer_count"])
    dimensions = ["region_code","org_code","status","currency_cd","update_time","source_system"]
    column_names = ["stat_month" if monthly else "stat_date", *dimensions, *metric_pool]
    if layer in {"ODS", "DWD"}:
        column_names.extend(["cust_id","account_id"])
    column_names = list(dict.fromkeys(column_names))
    table = f"stat_prod.{layer.lower()}_{stem}_scenario_{num:03d}"
    biz = f"{catalog_name}{['原始明细','标准明细','主题汇总','应用报表','参考维度'][(num - 33) % 5]}{num:03d}"
    grain = "地区×机构×月" if monthly else "客户×日"
    return (num, table, biz, layer, catalog, grain, column_names)


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for model in [TableLineage, Column, Metric, CodeValue, CodeTable, Dataset, Catalog]:
            db.execute(delete(model))

        for code, name in CATALOGS:
            db.add(Catalog(catalog_code=code, parent_code=None, catalog_name=name, description=f"{name}主题资产目录"))

        datasets: dict[int, Dataset] = {}
        column_id = 1
        for spec in GOLDEN_DATASETS:
            ds, column_id = add_dataset(db, spec, column_id)
            datasets[spec[0]] = ds
        for num in range(33, 261):
            spec = build_noise_spec(num)
            ds, column_id = add_dataset(db, spec, column_id)
            datasets[num] = ds

        # Curated golden lineage first; this is meaningful enough for graph/path/impact testing.
        golden_edges = [
            (1,2),(2,3),(3,4),(4,6),(4,10),(7,3),(7,4),(2,8),(2,9),
            (11,12),(12,13),(13,15),(12,14),(16,17),(17,18),(18,19),
            (20,21),(21,22),(22,23),(24,25),(27,3),(27,4),(28,4),(29,4),(30,4),(31,4),(32,4),
        ]
        for src, dst in golden_edges:
            db.add(TableLineage(src_asset_id=aid("DS", src), dst_asset_id=aid("DS", dst), task_name=f"golden_etl_{src:03d}_{dst:03d}", evidence="CONFIRMED"))
        # Scale lineage remains domain-local and deterministic.
        for num in range(33, 260):
            if (num - 33) % len(CATALOGS) == (num + 1 - 33) % len(CATALOGS):
                continue
            if num % 4 != 0:
                db.add(TableLineage(src_asset_id=aid("DS", num), dst_asset_id=aid("DS", num + 1), task_name=f"scale_etl_{num:03d}", evidence="CONFIRMED" if num % 7 else "INFERRED"))

        for idx, (code, values) in enumerate(CODE_TABLES.items(), 1):
            db.add(CodeTable(asset_id=aid("CT", idx), code_table_no=code, code_table_name={
                "CD_REGION":"行政区划","CD_ORG":"机构","CD_STATUS":"业务状态","CD_CURRENCY":"币种","CD_RISK_LEVEL":"风险等级","CD_CUSTOMER_TYPE":"客户类型","CD_LOAN_TYPE":"贷款类型"
            }[code], description="DataControl P3 语义验收码表", version="2026", owner="数据资产部"))
            for value, name in values:
                db.add(CodeValue(code_table_no=code, code_value=value, code_name=name, description=f"{name}测试码值"))

        metric_id = 1
        for code, name, aliases, source_num, agg, measure, time_field, additivity, valid_dims, caliber in CORE_METRICS:
            db.add(Metric(asset_id=aid("MT", metric_id), metric_code=code, metric_name=name, aliases=aliases,
                          biz_definition=f"{name}标准业务指标", source_dataset_id=aid("DS", source_num), stat_system_code="SS-FIN-2026",
                          aggregation=agg, measure_column=measure, time_field=time_field, time_additivity=additivity,
                          caliber_desc=caliber, valid_dimensions=valid_dims, status="ONLINE"))
            metric_id += 1

        # Additional governed metrics provide breadth without breaking source/measure consistency.
        derived_specs = [
            (3,"地区贷款日余额","loan_balance","stat_date","region_code,currency_cd"),
            (5,"机构贷款余额","loan_balance","stat_month","org_code,region_code"),
            (8,"普惠贷款客户数","customer_count","stat_month","region_code,org_code,customer_type"),
            (9,"不良贷款笔数","loan_count","stat_month","region_code,org_code,loan_type"),
            (13,"存款客户数","customer_count","stat_month","region_code,org_code,customer_type"),
            (18,"支付客户数","customer_count","stat_month","region_code,org_code"),
            (22,"风险客户数","customer_count","stat_month","region_code,org_code,risk_level"),
            (24,"资管客户数","customer_count","stat_month","product_code,org_code,region_code"),
            (26,"银行卡客户数","customer_count","stat_month","region_code,org_code"),
        ]
        metric_variants = ["总量","机构口径","地区口径","监管口径","经营口径","分析口径"]
        for source_num, base_name, measure, time_field, dims in derived_specs:
            for variant in metric_variants:
                code = f"metric_{measure}_{metric_id:03d}"
                db.add(Metric(asset_id=aid("MT", metric_id), metric_code=code, metric_name=f"{base_name}{variant}", aliases=f"{base_name}{variant}",
                              biz_definition=f"{base_name}{variant}测试指标", source_dataset_id=aid("DS", source_num), stat_system_code="SS-FIN-2026",
                              aggregation="sum", measure_column=measure, time_field=time_field,
                              time_additivity="NON_ADDITIVE" if ("balance" in measure or time_field == "stat_month" and "amount" not in measure) else "ADDITIVE",
                              caliber_desc=f"基于{datasets[source_num].biz_name}形成的{variant}，用于 P3 Agent 泛化测试。",
                              valid_dimensions=dims, status="ONLINE"))
                metric_id += 1

        db.commit()

        docs: list[dict] = []
        for ds in db.query(Dataset).all():
            docs.append({"asset_id": ds.asset_id, "asset_type": "TABLE", "title": ds.biz_name, "technical_name": ds.table_name,
                         "body": " ".join(filter(None, [ds.biz_definition, ds.stat_caliber, ds.usage_notes, ds.catalog_code, ds.tech_owner]))})
        for column in db.query(Column).all():
            docs.append({"asset_id": column.asset_id, "asset_type": "COLUMN", "title": column.cn_name or column.column_name,
                         "technical_name": f"{column.dataset_id}.{column.column_name}",
                         "body": " ".join(filter(None, [column.biz_definition, column.data_type, column.standard_no, column.code_table_no]))})
        for metric in db.query(Metric).all():
            docs.append({"asset_id": metric.asset_id, "asset_type": "METRIC", "title": metric.metric_name, "technical_name": metric.metric_code,
                         "body": " ".join(filter(None, [metric.aliases, metric.biz_definition, metric.caliber_desc, metric.valid_dimensions]))})
        SearchEngine().rebuild(docs)
        print(f"Generated P3 corpus: {len(datasets)} datasets, {column_id - 1} columns, {metric_id - 1} governed metrics, {len(docs)} search docs")
        print("Golden query anchor: metric_loan_balance -> DS000004 / stat_prod.dws_loan_region_month")


if __name__ == "__main__":
    main()
