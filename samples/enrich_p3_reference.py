from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db.models import DataStandard, StatisticalSystem, WordRoot
from backend.app.db.session import SessionLocal

EXTRA_ROOTS = [
    (11,"loan","贷款","loan","贷款,信贷"),(12,"dep","存款","deposit","存款,储蓄"),(13,"txn","交易","transaction","交易,流水"),
    (14,"contract","合同","contract","合同,协议"),(15,"acct","账户","account","账户,账号"),(16,"dt","日期","date","日期,统计日"),
    (17,"month","月份","month","月份,统计月"),(18,"currency","币种","currency","币种,货币"),(19,"inclusive","普惠","inclusive","普惠,小微"),(20,"npl","不良","non-performing loan","不良,次级,可疑,损失"),
]

EXTRA_SYSTEMS = [
    (4,"SS-DEP-2026","存款专项统计制度","统计管理部门","金统〔2026〕13号"),
    (5,"SS-PAY-2026","支付结算统计制度","支付管理部门","支付〔2026〕3号"),
    (6,"SS-INCLUSIVE-2026","普惠金融专项制度","普惠金融部门","普惠〔2026〕5号"),
    (7,"SS-ASSET-2026","资产管理统计制度","资管统计部门","资管〔2026〕2号"),
    (8,"SS-CARD-2026","银行卡统计制度","支付管理部门","卡统〔2026〕2号"),
    (9,"SS-ENT-2026","企业信息统计制度","调查统计部门","企统〔2026〕4号"),
    (10,"SS-COMMON-2026","公共基础数据规范","数据资产部","数标〔2026〕1号"),
]

EXTRA_STANDARDS = [
    (7,"DS-ORG-001","金融机构编码","org_code","机构统一标识代码","string","CD_ORG"),
    (8,"DS-CUSTTYPE-001","客户类型代码","customer_type","统一客户分类编码","string","CD_CUSTOMER_TYPE"),
    (9,"DS-LOANTYPE-001","贷款类型代码","loan_type","统一贷款业务分类编码","string","CD_LOAN_TYPE"),
    (10,"DS-MONTH-001","统计月份标准","stat_month","数据所属统计月份，YYYY-MM","string",None),
    (11,"DS-CUST-001","客户编号标准","cust_id","脱敏客户唯一标识","string",None),
    (12,"DS-CONTRACT-001","合同编号标准","contract_id","业务合同唯一标识","string",None),
    (13,"DS-ACCOUNT-001","账户编号标准","account_id","业务账户唯一标识","string",None),
    (14,"DS-PRODUCT-001","产品编码标准","product_code","金融产品唯一编码","string",None),
    (15,"DS-LOAN-BAL-001","贷款余额字段标准","loan_balance","期末尚未结清贷款本金余额","decimal(20,2)",None),
    (16,"DS-INCL-BAL-001","普惠贷款余额字段标准","inclusive_loan_balance","符合普惠口径的期末贷款余额","decimal(20,2)",None),
    (17,"DS-NPL-BAL-001","不良贷款余额字段标准","npl_balance","五级分类后三类贷款期末余额","decimal(20,2)",None),
    (18,"DS-OVERDUE-BAL-001","逾期贷款余额字段标准","overdue_balance","存在逾期状态的期末贷款余额","decimal(20,2)",None),
    (19,"DS-NEWLOAN-AMT-001","新增贷款金额字段标准","new_loan_amount","统计期内新发放贷款金额","decimal(20,2)",None),
    (20,"DS-DEP-BAL-001","存款余额字段标准","deposit_balance","期末有效存款账户余额","decimal(20,2)",None),
    (21,"DS-CORPDEP-BAL-001","企业存款余额字段标准","corporate_deposit_balance","企业客户期末存款余额","decimal(20,2)",None),
    (22,"DS-HHDEP-BAL-001","住户存款余额字段标准","household_deposit_balance","住户客户期末存款余额","decimal(20,2)",None),
    (23,"DS-TXN-AMT-001","交易金额字段标准","transaction_amount","统计期内交易发生金额","decimal(20,2)",None),
    (24,"DS-TXN-CNT-001","交易笔数字段标准","transaction_count","统计期内交易笔数","bigint",None),
    (25,"DS-CUST-CNT-001","客户数字段标准","customer_count","按统计口径去重的客户数量","bigint",None),
    (26,"DS-LOAN-CNT-001","贷款笔数字段标准","loan_count","有效贷款合同或账户数量","bigint",None),
    (27,"DS-RISK-CNT-001","风险事件数字段标准","risk_event_count","统计期内风险事件数量","bigint",None),
    (28,"DS-RISK-EXP-001","风险敞口字段标准","risk_exposure","统计期末风险暴露金额","decimal(20,2)",None),
    (29,"DS-AUM-001","资管产品余额字段标准","aum_balance","统计期末资产管理产品余额","decimal(20,2)",None),
    (30,"DS-UPDATE-001","更新时间标准","update_time","数据记录最后更新时间","datetime",None),
]


def main() -> None:
    with SessionLocal() as db:
        for idx, root, cn, full, synonyms in EXTRA_ROOTS:
            db.merge(WordRoot(asset_id=f"WR{idx:06d}", root_en=root, cn_name=cn, en_full=full, synonyms=synonyms, description=f"{cn}类字段标准命名词根", status="EFFECTIVE"))
        for idx, code, name, issuer, doc_no in EXTRA_SYSTEMS:
            db.merge(StatisticalSystem(asset_id=f"SS{idx:06d}", stat_system_code=code, stat_system_name=name, version="2026", issuer=issuer, document_no=doc_no, description=f"{name}合成验收制度", status="EFFECTIVE"))
        for idx, no, name, en_name, definition, data_type, code_table in EXTRA_STANDARDS:
            db.merge(DataStandard(asset_id=f"ST{idx:06d}", standard_no=no, standard_name=name, en_name=en_name, category_code="STD.FIELD", business_definition=definition, data_type=data_type, code_table_no=code_table, owner_dept="数据资产部", version="2026.1", status="EFFECTIVE"))
        db.commit()
        print(f"P3 references enriched: +{len(EXTRA_ROOTS)} roots, +{len(EXTRA_SYSTEMS)} systems, +{len(EXTRA_STANDARDS)} standards")


if __name__ == "__main__":
    main()
