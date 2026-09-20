from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select

from backend.app.core.security import hash_password
from backend.app.db.application_models import AuditLog, SearchHistory
from backend.app.db.models import (
    Base,
    ChangeLog,
    CommonSql,
    CommonSqlDataset,
    DataStandard,
    Dataset,
    DatasetTag,
    Favorite,
    StandardCategory,
    StatisticalSystem,
    Tag,
    User,
    ViewLog,
    WordRoot,
)
from backend.app.db.session import SessionLocal, engine


ROOTS = [
    ("bal", "余额", "balance", "余额,结余"),
    ("amt", "金额", "amount", "金额,发生额"),
    ("cnt", "数量", "count", "数量,户数,笔数"),
    ("cust", "客户", "customer", "客户,用户"),
    ("org", "机构", "organization", "机构,组织"),
    ("region", "地区", "region", "地区,区域"),
    ("prod", "产品", "product", "产品"),
    ("rate", "比率", "rate", "比率,比例,利率"),
    ("risk", "风险", "risk", "风险"),
    ("status", "状态", "status", "状态"),
]


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for model in [
            AuditLog,
            SearchHistory,
            Favorite,
            ViewLog,
            CommonSqlDataset,
            CommonSql,
            ChangeLog,
            DatasetTag,
            Tag,
            DataStandard,
            WordRoot,
            StatisticalSystem,
            StandardCategory,
            User,
        ]:
            db.execute(delete(model))

        db.add_all([
            StandardCategory(category_code="STD.CODE", category_type="CODE_TABLE", category_name="标准码值"),
            StandardCategory(category_code="STD.FIELD", category_type="STANDARD", category_name="字段标准"),
            StandardCategory(category_code="STD.ROOT", category_type="WORD_ROOT", category_name="命名词根"),
        ])

        for i, (root, cn, full, synonyms) in enumerate(ROOTS, 1):
            db.add(WordRoot(asset_id=f"WR{i:06d}", root_en=root, cn_name=cn, en_full=full, synonyms=synonyms, description=f"{cn}类字段的标准命名词根"))

        systems = [
            ("SS-FIN-2026", "金融统计制度", "2026", "统计管理部门", "金统〔2026〕1号"),
            ("SS-LOAN-2026", "贷款专项统计制度", "2026", "统计管理部门", "金统〔2026〕12号"),
            ("SS-RISK-2026", "风险监测统计制度", "2026", "风险管理部门", "风险〔2026〕8号"),
        ]
        for i, (code, name, version, issuer, no) in enumerate(systems, 1):
            db.add(StatisticalSystem(asset_id=f"SS{i:06d}", stat_system_code=code, stat_system_name=name, version=version, issuer=issuer, document_no=no, description=f"{name}测试制度"))

        standards = [
            ("DS-REGION-001", "行政区划代码", "region_code", "行政区划标准编码", "CD_REGION"),
            ("DS-STATUS-001", "业务状态代码", "status", "统一业务状态编码", "CD_STATUS"),
            ("DS-CURRENCY-001", "币种代码", "currency_cd", "统一币种编码", "CD_CURRENCY"),
            ("DS-RISK-001", "风险等级代码", "risk_level", "统一风险等级编码", "CD_RISK_LEVEL"),
            ("DS-AMT-001", "金额字段标准", "amount", "人民币金额，单位元", None),
            ("DS-DATE-001", "数据日期标准", "dt", "统计数据所属日期", None),
        ]
        for i, (no, name, en_name, definition, code_table) in enumerate(standards, 1):
            db.add(DataStandard(asset_id=f"ST{i:06d}", standard_no=no, standard_name=name, en_name=en_name, category_code="STD.FIELD", business_definition=definition, data_type="string" if code_table else "decimal/date", code_table_no=code_table, owner_dept="数据资产部", version="1.0"))

        tags = [
            ("F_DETAIL", "明细", "FEATURE"), ("F_SNAPSHOT", "快照", "FEATURE"), ("F_SUMMARY", "汇总", "FEATURE"),
            ("S_REGULATORY", "监管报送", "SCENE"), ("S_ANALYSIS", "经营分析", "SCENE"), ("S_RISK", "风险监测", "SCENE"),
        ]
        for code, name, group in tags:
            db.add(Tag(tag_code=code, tag_name=name, tag_group=group))

        datasets = db.execute(select(Dataset).order_by(Dataset.asset_id).limit(40)).scalars().all()
        for idx, ds in enumerate(datasets):
            db.add(DatasetTag(dataset_id=ds.asset_id, tag_code=tags[idx % len(tags)][0]))
            if idx < 18:
                db.add(ChangeLog(dataset_id=ds.asset_id, change_type=["CREATE", "DESCRIPTION", "CALIBER", "MODIFY_COLUMN"][idx % 4], content=f"{ds.biz_name}测试变更记录 #{idx + 1}", changed_by=["李明", "王璐", "周晨"][idx % 3]))

        for idx, ds in enumerate(datasets[:12], 1):
            code = f"SQL-DEMO-{idx:03d}"
            db.add(CommonSql(sql_code=code, title=f"{ds.biz_name}常用查询", question=f"如何查询{ds.biz_name}？", sql_text=f"SELECT * FROM {ds.table_name} WHERE dt='2026-09-19' LIMIT 100;", description="合成测试 SQL，仅用于页面与检索验证"))
            db.add(CommonSqlDataset(sql_code=code, dataset_id=ds.asset_id))

        user = User(username="demo", display_name="演示用户", password_hash=hash_password("DataControl123!"), role="USER", status="ENABLED")
        admin = User(username="admin", display_name="平台管理员", password_hash=hash_password("DataControlAdmin123!"), role="ADMIN", status="ENABLED")
        db.add_all([user, admin])
        db.flush()
        for idx, ds in enumerate(datasets[:8]):
            db.add(Favorite(user_id=user.id, asset_type="TABLE", asset_id=ds.asset_id))
            db.add(ViewLog(user_id=user.id, asset_type="TABLE", asset_id=ds.asset_id))
            db.add(SearchHistory(user_id=user.id, keyword=["贷款余额", "region_code", "企业风险", "监管报送"][idx % 4]))
        db.add(AuditLog(user_id=admin.id, action="P1_SEED", target_type="SYSTEM", target_id="P1", detail="Synthetic P1 application data initialized"))

        db.commit()
        print("P1 enriched: 10 word roots, 3 statistical systems, 6 standards, 6 tags, 18 changes, 12 common SQLs, demo users/favorites/views/search-history/audit")
        print("Demo login: demo / DataControl123! | admin / DataControlAdmin123!")


if __name__ == "__main__":
    main()
