from __future__ import annotations

import re
from dataclasses import dataclass

from sqlglot import exp

from agent3.contracts.authz import AuthzContext
from agent3.metadata.models import TableMetadata
from agent3.metadata.provider import MetadataProvider
from agent3.semantic.models import Additivity, MandatoryFilter
from agent3.semantic.registry import SemanticRegistry
from agent3.sql.analysis.analyzer import SQLAnalysisError, SQLAnalyzer
from agent3.sql.validation.models import (
    IssueAction,
    SQLOperation,
    SQLRiskLevel,
    Severity,
    ValidationIssue,
    ValidationResult,
)


@dataclass(frozen=True, slots=True)
class _ResolvedTable:
    full_name: str
    metadata: TableMetadata
    aliases: tuple[str, ...]


_QUERY_KEYS = {"select", "union", "except", "intersect"}
_DML_KEYS = {"insert", "update", "delete", "merge"}
_DDL_KEYS = {"create", "alter", "drop", "truncate", "truncatetable", "rename"}
_ACCESS_KEYS = {"grant", "revoke"}
_DESTRUCTIVE_KEYS = {"drop", "truncate", "truncatetable"}


class SQLValidator:
    """Deterministic static quality gate for generated MaxCompute SQL.

    Validation answers whether SQL is structurally and semantically trustworthy.
    It does not grant execution permission. DataControl remains generation-only for
    SELECT, DML, DDL and access-control statements alike.
    """

    def __init__(self, metadata: MetadataProvider, semantics: SemanticRegistry) -> None:
        self._metadata = metadata
        self._semantics = semantics
        self._analyzer = SQLAnalyzer()

    def validate(
        self,
        authz: AuthzContext,
        sql: str,
        *,
        dialect: str = "maxcompute",
        metric_id: str | None = None,
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []

        if dialect.strip().casefold() in {"maxcompute", "odps", "dataworks"}:
            normalized_text = " ".join(sql.strip().lower().split())
            if re.search(r"\binsert\s+overwrite\s+(?!table\b)", normalized_text):
                issues.append(
                    ValidationIssue(
                        "MAXCOMPUTE_INSERT_OVERWRITE_TABLE_REQUIRED",
                        Severity.ERROR,
                        "检测到 INSERT OVERWRITE 后未使用 TABLE 关键字。",
                        "改为 INSERT OVERWRITE TABLE 目标表 ...",
                        {"dialect": dialect},
                        IssueAction.AUTO_FIX,
                        True,
                    )
                )

        try:
            statements = self._analyzer.parse_program(sql, dialect=dialect)
        except SQLAnalysisError as exc:
            if issues:
                return ValidationResult(False, dialect, tuple(issues))
            return ValidationResult(
                False,
                dialect,
                (
                    ValidationIssue(
                        "SQL_PARSE_ERROR",
                        Severity.ERROR,
                        str(exc),
                        "检查 SQL 语法与方言",
                        action=IssueAction.BLOCK,
                    ),
                ),
            )

        if len(statements) != 1:
            return ValidationResult(
                False,
                dialect,
                (
                    ValidationIssue(
                        "MULTI_STATEMENT_NOT_ALLOWED",
                        Severity.ERROR,
                        f"一次 validate_sql 只能提交一条语句，当前检测到 {len(statements)} 条",
                        "拆分 SQL 后逐条校验",
                        {"statement_count": len(statements)},
                        IssueAction.BLOCK,
                    ),
                ),
            )

        try:
            analysis = self._analyzer.analyze(sql, dialect=dialect)
            tree = statements[0]
        except SQLAnalysisError as exc:
            return ValidationResult(
                False,
                dialect,
                (
                    ValidationIssue(
                        "SQL_PARSE_ERROR",
                        Severity.ERROR,
                        str(exc),
                        action=IssueAction.BLOCK,
                    ),
                ),
            )

        statement_key = tree.key.casefold()
        operation = self._operation(statement_key)
        risk_level = self._risk_level(statement_key, operation)

        if operation is SQLOperation.UNKNOWN:
            issues.append(
                ValidationIssue(
                    "UNCLASSIFIED_STATEMENT",
                    Severity.ERROR,
                    f"当前静态校验器尚不能可靠识别语句类型 {analysis.statement_type}",
                    "补充该 MaxCompute 语句类型的静态规则后再纳入可信 SQL",
                    {"statement_type": analysis.statement_type},
                    IssueAction.BLOCK,
                )
            )
        elif statement_key in _DESTRUCTIVE_KEYS:
            issues.append(
                ValidationIssue(
                    "DESTRUCTIVE_STATEMENT_GENERATION_ONLY",
                    Severity.WARNING,
                    f"检测到高风险语句 {analysis.statement_type}；DataControl 仅校验和生成，不执行。",
                    "执行前必须在 DataControl 之外走人工变更与审批流程。",
                    {"statement_type": analysis.statement_type},
                    IssueAction.ADVISORY,
                )
            )
        elif operation in {SQLOperation.DML, SQLOperation.DDL, SQLOperation.ACCESS_CONTROL}:
            issues.append(
                ValidationIssue(
                    "MUTATING_STATEMENT_GENERATION_ONLY",
                    Severity.INFO,
                    f"检测到 {analysis.statement_type}；当前结果仅用于代码生成与静态校验，不具备执行能力。",
                    "如需上线执行，请在生产开发平台中按既有变更流程处理。",
                    {"statement_type": analysis.statement_type, "operation": operation.value},
                    IssueAction.ADVISORY,
                )
            )

        cte_outputs = self._cte_outputs(tree)
        target_table = self._target_table_name(tree)
        resolved_tables = self._resolve_tables(
            authz,
            tree,
            analysis.tables,
            operation=operation,
            target_table=target_table,
            cte_outputs=cte_outputs,
            issues=issues,
        )
        self._validate_columns(tree, analysis.columns, resolved_tables, cte_outputs, issues)

        where_node = tree.find(exp.Where)
        where_columns = (
            {column.name.casefold() for column in where_node.find_all(exp.Column)}
            if where_node
            else set()
        )
        for table in resolved_tables:
            if table.metadata.partition_fields and not any(
                partition.casefold() in where_columns
                for partition in table.metadata.partition_fields
            ):
                issues.append(
                    ValidationIssue(
                        "NO_PARTITION_FILTER",
                        Severity.WARNING,
                        f"{table.metadata.full_name} 未命中分区字段 {', '.join(table.metadata.partition_fields)}",
                        "增加明确分区过滤，避免无界扫描",
                        {"table": table.metadata.full_name},
                        IssueAction.ADVISORY,
                    )
                )

        if metric_id:
            issues.extend(self._validate_metric(authz, tree, metric_id))

        return ValidationResult(
            valid=not any(issue.blocking for issue in issues),
            dialect=dialect,
            issues=tuple(issues),
            normalized_sql=analysis.normalized_sql,
            statement_type=analysis.statement_type,
            operation=operation,
            risk_level=risk_level,
            execution_allowed=False,
        )

    @staticmethod
    def _operation(statement_key: str) -> SQLOperation:
        if statement_key in _QUERY_KEYS:
            return SQLOperation.QUERY
        if statement_key in _DML_KEYS:
            return SQLOperation.DML
        if statement_key in _DDL_KEYS:
            return SQLOperation.DDL
        if statement_key in _ACCESS_KEYS:
            return SQLOperation.ACCESS_CONTROL
        return SQLOperation.UNKNOWN

    @staticmethod
    def _risk_level(statement_key: str, operation: SQLOperation) -> SQLRiskLevel:
        if statement_key in _DESTRUCTIVE_KEYS:
            return SQLRiskLevel.CRITICAL
        if operation in {SQLOperation.DML, SQLOperation.ACCESS_CONTROL}:
            return SQLRiskLevel.HIGH
        if operation is SQLOperation.DDL:
            return SQLRiskLevel.MEDIUM
        if operation is SQLOperation.QUERY:
            return SQLRiskLevel.LOW
        return SQLRiskLevel.HIGH

    @staticmethod
    def _table_name(table: exp.Table) -> str:
        parts = [part for part in (table.catalog, table.db, table.name) if part]
        return ".".join(parts)

    @classmethod
    def _table_from_expression(cls, node: exp.Expression | None) -> str | None:
        if isinstance(node, exp.Table):
            return cls._table_name(node)
        if isinstance(node, exp.Schema) and isinstance(node.this, exp.Table):
            return cls._table_name(node.this)
        return None

    @classmethod
    def _target_table_name(cls, tree: exp.Expression) -> str | None:
        if isinstance(
            tree,
            (
                exp.Insert,
                exp.Update,
                exp.Delete,
                exp.Merge,
                exp.Create,
                exp.Alter,
                exp.Drop,
            ),
        ):
            return cls._table_from_expression(tree.this)
        return None

    @staticmethod
    def _cte_outputs(tree: exp.Expression) -> dict[str, set[str]]:
        outputs: dict[str, set[str]] = {}
        for cte in tree.find_all(exp.CTE):
            alias = cte.alias_or_name
            if not alias:
                continue
            columns: set[str] = set()
            query = cte.this
            selections = getattr(query, "selects", None)
            if selections:
                for selection in selections:
                    name = selection.alias_or_name
                    if name and name != "*":
                        columns.add(name.casefold())
            outputs[alias.casefold()] = columns
        return outputs

    def _resolve_tables(
        self,
        authz: AuthzContext,
        tree: exp.Expression,
        table_names: tuple[str, ...],
        *,
        operation: SQLOperation,
        target_table: str | None,
        cte_outputs: dict[str, set[str]],
        issues: list[ValidationIssue],
    ) -> list[_ResolvedTable]:
        aliases_by_full_name: dict[str, set[str]] = {}
        for table in tree.find_all(exp.Table):
            full_name = self._table_name(table)
            if not full_name:
                continue
            aliases = aliases_by_full_name.setdefault(full_name.casefold(), set())
            aliases.add(table.name.casefold())
            if table.alias:
                aliases.add(table.alias.casefold())

        resolved: list[_ResolvedTable] = []
        target_key = target_table.casefold() if target_table else None
        for table_name in table_names:
            table_key = table_name.casefold()
            base_name = table_name.rsplit(".", 1)[-1].casefold()
            if "." not in table_name and base_name in cte_outputs:
                continue

            # CREATE introduces a new target by definition. Validate its source
            # tables, but do not require the target to already exist in metadata.
            if operation is SQLOperation.DDL and tree.key.casefold() == "create" and table_key == target_key:
                continue

            table = self._metadata.get_table(authz, table_name)
            if table is None:
                issues.append(
                    ValidationIssue(
                        "UNKNOWN_TABLE",
                        Severity.ERROR,
                        f"表不存在或元数据不可见: {table_name}",
                        "先调用 search_tables/get_schema 选择已授权表；CREATE 的新目标表除外。",
                        {"table": table_name},
                        IssueAction.BLOCK,
                    )
                )
                continue

            aliases = aliases_by_full_name.get(table_key, {base_name})
            resolved.append(
                _ResolvedTable(
                    full_name=table_name,
                    metadata=table,
                    aliases=tuple(sorted(aliases)),
                )
            )
        return resolved

    @staticmethod
    def _validate_columns(
        tree: exp.Expression,
        columns: tuple,
        resolved_tables: list[_ResolvedTable],
        cte_outputs: dict[str, set[str]],
        issues: list[ValidationIssue],
    ) -> None:
        del tree  # kept in the signature for the next scope-aware adapter step

        alias_map: dict[str, TableMetadata] = {}
        for resolved in resolved_tables:
            for alias in resolved.aliases:
                alias_map[alias.casefold()] = resolved.metadata

        for ref in columns:
            if ref.name == "*":
                continue
            name = ref.name.casefold()
            qualifier = ref.table.casefold() if ref.table else None

            if qualifier and qualifier in cte_outputs:
                known_outputs = cte_outputs[qualifier]
                if known_outputs and name not in known_outputs:
                    issues.append(
                        ValidationIssue(
                            "UNKNOWN_CTE_COLUMN",
                            Severity.ERROR,
                            f"CTE {ref.table} 未输出字段 {ref.name}",
                            "检查 CTE SELECT 输出字段或别名",
                            {"cte": ref.table, "column": ref.name},
                            IssueAction.BLOCK,
                        )
                    )
                continue

            if qualifier and qualifier in alias_map:
                if alias_map[qualifier].column(ref.name) is None:
                    issues.append(
                        ValidationIssue(
                            "UNKNOWN_COLUMN",
                            Severity.ERROR,
                            f"字段不存在: {ref.table}.{ref.name}",
                            "调用 get_schema 获取真实字段",
                            {"table_alias": ref.table, "column": ref.name},
                            IssueAction.BLOCK,
                        )
                    )
                continue

            if any(table.metadata.column(ref.name) is not None for table in resolved_tables):
                continue
            if any(not outputs or name in outputs for outputs in cte_outputs.values()):
                continue

            issues.append(
                ValidationIssue(
                    "UNKNOWN_COLUMN",
                    Severity.ERROR,
                    f"字段不存在: {ref.name}",
                    "调用 get_schema 获取真实字段",
                    {"column": ref.name},
                    IssueAction.BLOCK,
                )
            )

    def _validate_metric(
        self,
        authz: AuthzContext,
        tree: exp.Expression,
        metric_id: str,
    ) -> list[ValidationIssue]:
        metric = self._semantics.get(authz, metric_id)
        if metric is None:
            return [
                ValidationIssue(
                    "UNKNOWN_METRIC",
                    Severity.ERROR,
                    f"未知指标: {metric_id}",
                    "先调用 resolve_metric 获取认证指标",
                    action=IssueAction.BLOCK,
                )
            ]

        issues: list[ValidationIssue] = []
        functions = [node for node in tree.walk() if isinstance(node, exp.AggFunc)]
        matched_agg = False
        for fn in functions:
            if fn.key.casefold() == metric.aggregation.casefold():
                cols = {column.name.casefold() for column in fn.find_all(exp.Column)}
                if metric.measure.casefold() in cols:
                    matched_agg = True
                    break
        if not matched_agg:
            issues.append(
                ValidationIssue(
                    "METRIC_MISMATCH",
                    Severity.ERROR,
                    f"指标 {metric.id} 要求 {metric.aggregation}({metric.measure})",
                    f"使用 {metric.aggregation}({metric.measure})",
                    {
                        "metric_id": metric.id,
                        "aggregation": metric.aggregation,
                        "measure": metric.measure,
                    },
                    IssueAction.BLOCK,
                )
            )

        where = tree.find(exp.Where)
        for required in metric.mandatory_filters:
            if not self._has_filter(where, required):
                issues.append(
                    ValidationIssue(
                        "MISSING_MANDATORY_FILTER",
                        Severity.ERROR,
                        f"指标 {metric.id} 缺少强制过滤 {required.field} {required.op} {required.value}",
                        "按语义模型补充强制过滤",
                        {"metric_id": metric.id, "field": required.field},
                        IssueAction.BLOCK,
                    )
                )

        if metric.additivity_time is Additivity.NON_ADDITIVE and not self._has_single_period(
            where, metric.time_field
        ):
            issues.append(
                ValidationIssue(
                    "NON_ADDITIVE_OVER_TIME",
                    Severity.ERROR,
                    f"指标 {metric.id} 为时间非可加快照指标，必须限定单个 {metric.time_field}",
                    f"限定单个 {metric.time_field}，或使用 MAX({metric.time_field}) 选择最新快照；不要跨期 SUM",
                    {"metric_id": metric.id, "time_field": metric.time_field},
                    IssueAction.BLOCK,
                )
            )
        return issues

    @staticmethod
    def _has_filter(where: exp.Where | None, required: MandatoryFilter) -> bool:
        if where is None:
            return False
        classes = {
            "eq": exp.EQ,
            "ne": exp.NEQ,
            "gt": exp.GT,
            "gte": exp.GTE,
            "lt": exp.LT,
            "lte": exp.LTE,
        }
        target = classes.get(required.op)
        if target is None:
            return False
        for node in where.find_all(target):
            left, right = node.this, node.expression
            if isinstance(left, exp.Column) and left.name.casefold() == required.field.casefold():
                value = right.this if isinstance(right, exp.Literal) else None
                if str(value) == str(required.value):
                    return True
        return False

    @classmethod
    def _has_single_period(cls, where: exp.Where | None, field: str) -> bool:
        """Conservatively prove that every boolean branch selects one snapshot.

        In particular, `dt = 'A' OR dt = 'B'` is rejected, while a literal
        equality, a one-value IN, or `dt = (SELECT MAX(dt) ...)` is accepted.
        """
        if where is None:
            return False
        return cls._period_constraint(where.this, field.casefold()) is not None

    @classmethod
    def _period_constraint(
        cls,
        node: exp.Expression | None,
        target: str,
    ) -> tuple[str, str] | None:
        if node is None:
            return None
        if isinstance(node, exp.Paren):
            return cls._period_constraint(node.this, target)

        if isinstance(node, exp.And):
            left = cls._period_constraint(node.this, target)
            right = cls._period_constraint(node.expression, target)
            if left is None:
                return right
            if right is None:
                return left
            return left if left == right else None

        if isinstance(node, exp.Or):
            left = cls._period_constraint(node.this, target)
            right = cls._period_constraint(node.expression, target)
            if left is None or right is None:
                return None
            return left if left == right else None

        if isinstance(node, exp.EQ):
            left, right = node.this, node.expression
            if isinstance(right, exp.Column) and not isinstance(left, exp.Column):
                left, right = right, left
            if not isinstance(left, exp.Column) or left.name.casefold() != target:
                return None
            if isinstance(right, exp.Literal):
                return ("literal", right.sql())
            for aggregate in right.find_all(exp.Max):
                columns = {
                    column.name.casefold()
                    for column in aggregate.find_all(exp.Column)
                }
                if target in columns:
                    return ("max", target)
            return None

        if isinstance(node, exp.In):
            left = node.this
            if not isinstance(left, exp.Column) or left.name.casefold() != target:
                return None
            expressions = list(node.expressions)
            if len(expressions) == 1 and isinstance(expressions[0], exp.Literal):
                return ("literal", expressions[0].sql())
            return None

        return None
