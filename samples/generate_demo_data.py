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
    ("FIN.LOAN", "贷款统计", ["贷款余额", "贷款合同", "客户授信", "普惠贷款", "不良贷款"]),
    ("FIN.DEP", "存款统计", ["存款余额", "存款账户", "客户存款", "结构性存款"]),
    ("FIN.ASSET", "资管产品", ["理财产品", "资产管理", "产品持仓", "净值"]),
    ("FIN.PAY", "支付结算", ["支付流水", "账户交易", "渠道交易", "清算"]),
    ("FIN.RISK", "风险监测", ["企业风险", "信用风险", "风险预警", "逾期"]),
    ("FIN.ENT", "企业信息", ["企业基本信息", "股东信息", "工商变更", "司法风险"]),
    ("FIN.REG", "监管报送", ["金融统计", "监管指标", "报送汇总", "机构统计"]),
    ("COMMON.ORG", "公共维度", ["机构维度", "地区维度", "日期维度", "产品维度"]),
]
COLUMN_POOL = [
    ("dt", "数据日期", "date", "统计日期"),
    ("org_code", "机构编码", "string", "机构唯一编码"),
    ("region_code", "地区编码", "string", "行政区划代码"),
    ("cust_id", "客户编号", "string", "客户唯一标识"),
    ("contract_id", "合同编号", "string", "合同唯一标识"),
    ("product_code", "产品编码", "string", "产品唯一编码"),
    ("balance_amt", "余额", "decimal(20,2)", "期末账面余额"),
    ("amount", "金额", "decimal(20,2)", "业务发生金额"),
    ("status", "状态", "string", "业务状态码"),
    ("currency_cd", "币种", "string", "交易币种代码"),
    ("rate", "利率", "decimal(12,6)", "年化利率"),
    ("term_days", "期限天数", "bigint", "合同期限天数"),
    ("risk_level", "风险等级", "string", "内部风险分级"),
    ("update_time", "更新时间", "datetime", "记录更新时间"),
    ("source_system", "来源系统", "string", "来源业务系统"),
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
        col_id = 1
        for i in range(1, 181):
            code, catalog_name, topics = DOMAINS[(i - 1) % len(DOMAINS)]
            layer = LAYERS[(i - 1) % len(LAYERS)]
            topic = topics[(i // len(DOMAINS)) % len(topics)]
            suffix = ["detail", "snapshot", "region_d", "summary_m", "report_q"][LAYERS.index(layer)]
            stem = ["loan", "deposit", "asset", "payment", "risk", "enterprise", "reg", "dim"][(i - 1) % 8]
            table = f"stat_prod.{layer.lower()}_{stem}_{i:03d}_{suffix}"
            biz = f"{topic}{['明细', '快照', '地区汇总', '月度汇总', '报送结果'][LAYERS.index(layer)]}"
            ds = Dataset(
                asset_id=aid("DS", i),
                table_name=table,
                biz_name=biz,
                workspace_code="stat_prod",
                layer_code=layer,
                catalog_code=code,
                biz_definition=f"用于{catalog_name}场景的{biz}，覆盖机构、地区、产品及客户等核心分析维度。",
                stat_caliber=f"按数据日期取有效记录；剔除 cancelled/invalid 状态；金额统一折算为人民币。{topic}按制度口径归集。",
                data_source_desc="核心业务系统、企业风险库及统一机构维度，经数仓标准化加工形成。",
                grain=R.choice(["机构×日", "机构×产品×日", "客户×合同×日", "地区×机构×月"]),
                usage_notes=R.choice(["月末使用最后一个有效统计日。", "余额类指标不可跨期直接相加。", "历史口径变更前请查看变更记录。"]),
                tech_owner=R.choice(["李明", "周晨", "陈宇", "王璐", "赵凯"]),
                biz_owner=R.choice(["张敏", "刘洋", "许然", None]),
                owner_dept=R.choice(["数据资产部", "统计监测部", "调查统计部"]),
                update_freq=R.choice(["DAILY", "DAILY", "MONTHLY", "WEEKLY"]),
                schedule_desc=R.choice(["每日 02:30", "每月 1 日 03:10", "每周一 04:00"]),
                schedule_node=f"dw_{layer.lower()}_{stem}_{i:03d}",
                status="DEPRECATED" if i % 37 == 0 else ("OFFLINE" if i % 59 == 0 else "ONLINE"),
                is_common=(i % 7 == 0 or i < 12),
                storage_bytes=R.randint(10_000_000, 80_000_000_000),
                row_count=R.randint(5_000, 200_000_000),
                data_updated_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=R.randint(1, 180)),
                updated_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=R.randint(0, 120)),
            )
            db.add(ds)
            datasets.append(ds)

            chosen = list(COLUMN_POOL)
            R.shuffle(chosen)
            chosen = (COLUMN_POOL[:5] + chosen)[: R.randint(12, 24)]
            seen: set[str] = set()
            for pos, (name, cn, typ, definition) in enumerate(chosen, 1):
                if name in seen:
                    continue
                seen.add(name)
                db.add(
                    Column(
                        asset_id=aid("FD", col_id, 7),
                        dataset_id=ds.asset_id,
                        column_name=name,
                        ordinal_no=pos,
                        cn_name=cn,
                        data_type=typ,
                        biz_definition=definition,
                        unit="元" if name in ("balance_amt", "amount") else None,
                        code_table_no="CD_STATUS" if name == "status" else ("CD_REGION" if name == "region_code" else None),
                        standard_no="DS-REGION-001" if name == "region_code" else None,
                    )
                )
                col_id += 1

        for i in range(1, 180):
            if i % 5 != 0:
                db.add(
                    TableLineage(
                        src_asset_id=aid("DS", i),
                        dst_asset_id=aid("DS", i + 1),
                        task_name=f"etl_task_{i:03d}",
                        evidence="CONFIRMED" if i % 6 else "INFERRED",
                    )
                )

        code_specs = {
            "CD_STATUS": ["normal", "overdue", "settled", "cancelled"],
            "CD_REGION": ["440100", "440300", "440600", "441900", "440500"],
            "CD_CURRENCY": ["CNY", "USD", "EUR", "JPY", "HKD"],
            "CD_RISK_LEVEL": ["A", "B", "C", "D", "E"],
        }
        names = {"CD_STATUS": "业务状态", "CD_REGION": "行政地区", "CD_CURRENCY": "币种", "CD_RISK_LEVEL": "风险等级"}
        translations = {"normal": "正常", "overdue": "逾期", "settled": "结清", "cancelled": "已取消"}
        for idx, (no, vals) in enumerate(code_specs.items(), 1):
            db.add(CodeTable(asset_id=aid("CT", idx), code_table_no=no, code_table_name=names[no], description="合成测试码表"))
            for value in vals:
                db.add(CodeValue(code_table_no=no, code_value=value, code_name=translations.get(value, value), description="测试码值"))

        metric_names = ["各项贷款余额", "普惠贷款余额", "不良贷款余额", "企业存款余额", "住户存款余额", "贷款客户数", "新增贷款金额", "逾期合同数", "资管产品余额", "支付交易金额", "企业风险事件数", "监管报送机构数"]
        for i, name in enumerate(metric_names, 1):
            src = datasets[(i * 7) % len(datasets)]
            db.add(
                Metric(
                    asset_id=aid("MT", i),
                    metric_code=f"metric_{i:03d}",
                    metric_name=name,
                    aliases=name.replace("各项", ""),
                    biz_definition=f"{name}的标准指标定义",
                    source_dataset_id=src.asset_id,
                    aggregation="sum" if "数" not in name else "count_distinct",
                    measure_column="balance_amt" if "余额" in name or "金额" in name else "cust_id",
                    time_field="dt",
                    caliber_desc="剔除 cancelled 状态并按统计日期归集。",
                )
            )
        db.commit()

        docs: list[dict] = []
        for ds in db.query(Dataset).all():
            docs.append({"asset_id": ds.asset_id, "asset_type": "TABLE", "title": ds.biz_name, "technical_name": ds.table_name, "body": " ".join(filter(None, [ds.biz_definition, ds.stat_caliber, ds.catalog_code, ds.tech_owner]))})
        for column in db.query(Column).all():
            docs.append({"asset_id": column.asset_id, "asset_type": "COLUMN", "title": column.cn_name or column.column_name, "technical_name": f"{column.dataset_id}.{column.column_name}", "body": " ".join(filter(None, [column.biz_definition, column.data_type, column.standard_no, column.code_table_no]))})
        for metric in db.query(Metric).all():
            docs.append({"asset_id": metric.asset_id, "asset_type": "METRIC", "title": metric.metric_name, "technical_name": metric.metric_code, "body": " ".join(filter(None, [metric.aliases, metric.biz_definition, metric.caliber_desc]))})
        SearchEngine().rebuild(docs)
        print(f"Generated: {len(datasets)} datasets, {col_id - 1} columns, {len(metric_names)} metrics, {len(docs)} search docs")


if __name__ == "__main__":
    main()
