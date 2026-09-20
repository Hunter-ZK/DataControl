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

R = random.Random(20260920)
LAYERS = ["ODS", "DWD", "DWS", "ADS", "DIM"]
DOMAINS = [
    ("FIN.LOAN", "贷款统计", "loan"), ("FIN.DEP", "存款统计", "deposit"),
    ("FIN.ASSET", "资管产品", "asset"), ("FIN.PAY", "支付结算", "payment"),
    ("FIN.RISK", "风险监测", "risk"), ("FIN.ENT", "企业信息", "enterprise"),
    ("FIN.REG", "监管报送", "reg"), ("COMMON.ORG", "公共维度", "dim"),
]
BASE_COLUMNS = [
    ("dt", "数据日期", "date", "统计日期"), ("org_code", "机构编码", "string", "机构唯一编码"),
    ("region_code", "地区编码", "string", "行政区划代码"), ("cust_id", "客户编号", "string", "客户唯一标识"),
    ("contract_id", "合同编号", "string", "合同唯一标识"), ("product_code", "产品编码", "string", "产品唯一编码"),
    ("balance_amt", "余额", "decimal(20,2)", "期末账面余额"), ("amount", "金额", "decimal(20,2)", "业务发生金额"),
    ("status", "状态", "string", "业务状态码"), ("currency_cd", "币种", "string", "交易币种代码"),
    ("rate", "利率", "decimal(12,6)", "年化利率"), ("risk_level", "风险等级", "string", "内部风险分级"),
    ("source_system", "来源系统", "string", "来源业务系统"), ("update_time", "更新时间", "datetime", "记录更新时间"),
]


def aid(prefix: str, n: int, width: int = 6) -> str:
    return f"{prefix}{n:0{width}d}"


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for model in [TableLineage, Column, Metric, CodeValue, CodeTable, Dataset, Catalog]:
            db.execute(delete(model))
        for code, name, _ in DOMAINS:
            db.add(Catalog(catalog_code=code, parent_code=None, catalog_name=name, description=f"{name}主题资产目录"))

        datasets: list[Dataset] = []
        field_id = 1
        for i in range(1, 1362):
            catalog_code, catalog_name, stem = DOMAINS[(i - 1) % len(DOMAINS)]
            layer = LAYERS[(i - 1) % len(LAYERS)]
            suffix = ["detail", "snapshot", "region_d", "summary_m", "report_q"][LAYERS.index(layer)]
            biz_subject = ["余额", "合同", "客户", "产品", "风险", "交易", "机构", "报送"][i % 8]
            ds = Dataset(
                asset_id=aid("DS", i),
                table_name=f"stat_prod.{layer.lower()}_{stem}_{i:04d}_{suffix}",
                biz_name=f"{catalog_name}{biz_subject}{['明细','快照','地区汇总','月度汇总','报送结果'][LAYERS.index(layer)]}",
                workspace_code="stat_prod", layer_code=layer, catalog_code=catalog_code,
                biz_definition=f"{catalog_name}主题下的{biz_subject}资产，用于开发、统计分析与监管报送验证。",
                stat_caliber="按有效统计日取数，剔除 cancelled/invalid 状态；余额类指标按期末时点口径计算。",
                data_source_desc="核心业务系统、外部企业风险库及公共维度经数仓标准化加工形成。",
                grain=R.choice(["机构×日", "机构×产品×日", "客户×合同×日", "地区×机构×月"]),
                usage_notes=R.choice(["月末使用最后一个有效统计日。", "余额类指标不可跨期直接相加。", "历史口径变更请查看变更说明。"]),
                tech_owner=R.choice(["李明", "周晨", "陈宇", "王璐", "赵凯", "林浩", "许婷"]),
                biz_owner=R.choice(["张敏", "刘洋", "许然", "高宁", None]),
                owner_dept=R.choice(["数据资产部", "统计监测部", "调查统计部", "风险监测部"]),
                update_freq=R.choice(["DAILY", "DAILY", "WEEKLY", "MONTHLY", "QUARTERLY"]),
                schedule_desc=R.choice(["每日 02:30", "每周一 04:00", "每月 1 日 03:10", "季末次日 05:00"]),
                schedule_node=f"dw_{layer.lower()}_{stem}_{i:04d}",
                status="DEPRECATED" if i % 41 == 0 else ("OFFLINE" if i % 67 == 0 else "ONLINE"),
                is_common=(i <= 40 or i % 17 == 0), storage_bytes=R.randint(10_000_000, 200_000_000_000),
                row_count=R.randint(5_000, 500_000_000), data_updated_at=datetime.now(UTC).replace(tzinfo=None)-timedelta(hours=R.randint(1,360)),
                updated_at=datetime.now(UTC).replace(tzinfo=None)-timedelta(days=R.randint(0,180)),
            )
            db.add(ds)
            datasets.append(ds)
            fields = list(BASE_COLUMNS)
            for extra in range(26):
                fields.append((f"attr_{extra+1:02d}", f"扩展属性{extra+1:02d}", R.choice(["string", "bigint", "decimal(20,2)", "date"]), f"用于压力测试与复杂检索验证的扩展业务属性 {extra+1:02d}"))
            for pos, (name, cn, typ, definition) in enumerate(fields, 1):
                db.add(Column(asset_id=aid("FD", field_id, 7), dataset_id=ds.asset_id, column_name=name, ordinal_no=pos,
                              cn_name=cn, data_type=typ, biz_definition=definition, unit="元" if name in {"balance_amt","amount"} else None,
                              code_table_no="CD_STATUS" if name == "status" else ("CD_REGION" if name == "region_code" else None),
                              standard_no="DS-REGION-001" if name == "region_code" else None))
                field_id += 1

        for i in range(1, 1361):
            if i % 5 != 0:
                db.add(TableLineage(src_asset_id=aid("DS", i), dst_asset_id=aid("DS", i + 1), task_name=f"etl_task_{i:04d}", evidence="INFERRED" if i % 11 == 0 else "CONFIRMED"))
            if i + 8 <= 1361 and i % 3 == 0:
                db.add(TableLineage(src_asset_id=aid("DS", i), dst_asset_id=aid("DS", i + 8), task_name=f"cross_domain_{i:04d}", evidence="CONFIRMED"))

        core_codes = {
            "CD_STATUS": [("normal","正常"),("overdue","逾期"),("settled","结清"),("cancelled","已取消")],
            "CD_REGION": [("440100","广州市"),("440300","深圳市"),("440600","佛山市"),("441900","东莞市"),("440500","汕头市")],
            "CD_CURRENCY": [("CNY","人民币"),("USD","美元"),("EUR","欧元"),("JPY","日元"),("HKD","港币")],
            "CD_RISK_LEVEL": [("A","低风险"),("B","较低风险"),("C","中风险"),("D","较高风险"),("E","高风险")],
        }
        for idx, (no, values) in enumerate(core_codes.items(), 1):
            db.add(CodeTable(asset_id=aid("CT", idx), code_table_no=no, code_table_name=no.removeprefix("CD_") + "标准码表", description="核心合成码表"))
            for value, name in values:
                db.add(CodeValue(code_table_no=no, code_value=value, code_name=name, description="核心测试码值"))
        for idx in range(5, 41):
            no = f"CD_TEST_{idx:03d}"
            db.add(CodeTable(asset_id=aid("CT", idx), code_table_no=no, code_table_name=f"测试分类码表{idx:03d}", description="用于码表列表、检索与分页压力验证"))
            for value in range(1, R.randint(8, 25)):
                db.add(CodeValue(code_table_no=no, code_value=f"V{value:03d}", code_name=f"分类值{value:03d}", description="合成测试码值"))

        metric_prefixes = ["贷款", "存款", "普惠", "不良", "企业", "住户", "资管", "支付", "风险", "监管"]
        metric_types = ["余额", "发生额", "客户数", "合同数", "户均余额", "增长率", "逾期率"]
        for i in range(1, 127):
            name = metric_prefixes[i % len(metric_prefixes)] + metric_types[i % len(metric_types)]
            src = datasets[(i * 9) % len(datasets)]
            count_metric = name.endswith("数")
            db.add(Metric(asset_id=aid("MT", i), metric_code=f"metric_{i:03d}", metric_name=name, aliases=f"{name},指标{i:03d}",
                          biz_definition=f"{name}的标准业务指标定义与统计用途。", source_dataset_id=src.asset_id,
                          aggregation="count_distinct" if count_metric else "sum", measure_column="cust_id" if count_metric else "balance_amt",
                          time_field="dt", caliber_desc="按有效统计日归集，剔除 cancelled 状态；时点余额不得跨期直接相加。"))
        db.commit()

        docs = []
        for ds in db.query(Dataset).all():
            docs.append({"asset_id": ds.asset_id, "asset_type": "TABLE", "title": ds.biz_name, "technical_name": ds.table_name,
                         "body": " ".join(filter(None, [ds.biz_definition, ds.stat_caliber, ds.catalog_code, ds.tech_owner, ds.owner_dept]))})
        for column in db.query(Column).all():
            docs.append({"asset_id": column.asset_id, "asset_type": "COLUMN", "title": column.cn_name or column.column_name,
                         "technical_name": f"{column.dataset_id}.{column.column_name}", "body": " ".join(filter(None, [column.biz_definition, column.data_type, column.standard_no, column.code_table_no]))})
        for metric in db.query(Metric).all():
            docs.append({"asset_id": metric.asset_id, "asset_type": "METRIC", "title": metric.metric_name, "technical_name": metric.metric_code,
                         "body": " ".join(filter(None, [metric.aliases, metric.biz_definition, metric.caliber_desc]))})
        for code in db.query(CodeTable).all():
            docs.append({"asset_id": code.asset_id, "asset_type": "CODE_TABLE", "title": code.code_table_name, "technical_name": code.code_table_no,
                         "body": code.description or ""})
        SearchEngine().rebuild(docs)
        print(f"FULL SCALE GENERATED: {len(datasets)} datasets, {field_id-1} fields, 126 metrics, 40 code tables, {len(docs)} search docs")


if __name__ == "__main__":
    main()
