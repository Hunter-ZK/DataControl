from agent3.metadata.in_memory import InMemoryMetadataProvider
from agent3.metadata.models import CodeValueMetadata, ColumnMetadata, TableMetadata


def build_demo_metadata() -> InMemoryMetadataProvider:
    tables = (
        TableMetadata(
            full_name="dw.dwd_loan_snapshot",
            description="贷款余额日快照",
            aliases=("贷款快照", "loan balance"),
            partition_fields=("dt",),
            columns=(
                ColumnMetadata("dt", "string", "数据日期"),
                ColumnMetadata("org_id", "string", "机构编号"),
                ColumnMetadata(
                    "region_code",
                    "string",
                    "地区代码",
                    code_table_no="CD_REGION",
                    standard_no="DS-REGION-001",
                ),
                ColumnMetadata("product_id", "string", "产品编号"),
                ColumnMetadata(
                    "currency_cd",
                    "string",
                    "币种代码",
                    code_table_no="CD_CURRENCY",
                    standard_no="DS-CURRENCY-001",
                ),
                ColumnMetadata("balance_amt", "decimal(20,2)", "贷款余额"),
                ColumnMetadata("npl_balance", "decimal(20,2)", "不良贷款余额"),
                ColumnMetadata("new_loan_amt", "decimal(20,2)", "新增贷款金额"),
                ColumnMetadata("status", "string", "贷款状态"),
            ),
        ),
        TableMetadata(
            full_name="dw.dim_org",
            description="机构维表",
            aliases=("机构",),
            columns=(
                ColumnMetadata("org_id", "string", "机构编号"),
                ColumnMetadata("org_name", "string", "机构名称"),
                ColumnMetadata("region_code", "string", "地区代码", code_table_no="CD_REGION"),
            ),
        ),
    )
    code_values = (
        CodeValueMetadata("CD_CURRENCY", "CNY", "人民币", "人民币币种"),
        CodeValueMetadata("CD_CURRENCY", "USD", "美元", "美元币种"),
        CodeValueMetadata("CD_REGION", "440000", "广东省", "广东省行政区划"),
        CodeValueMetadata("CD_REGION", "440300", "深圳市", "深圳市行政区划"),
        CodeValueMetadata("CD_REGION", "440100", "广州市", "广州市行政区划"),
    )
    return InMemoryMetadataProvider(tables, code_values)
