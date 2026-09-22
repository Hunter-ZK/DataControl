from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agent3.contracts.authz import AuthzContext
from agent3.metadata.provider import MetadataProvider
from agent3.semantic.models import Additivity, ComparisonKind, MetricKind, QueryIR
from agent3.semantic.registry import SemanticRegistry

_SUPPORTED_FILTERS = {
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "not_in",
    "between",
    "contains",
    "startswith",
    "endswith",
    "is_null",
    "is_not_null",
}


@dataclass(frozen=True, slots=True)
class SemanticIssue:
    code: str
    message: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class SemanticValidationResult:
    valid: bool
    issues: tuple[SemanticIssue, ...]
    metric_ids: tuple[str, ...]
    source_entity: str | None
    time_field: str | None
    research_policy: str = "internal_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [asdict(issue) for issue in self.issues],
            "metricIds": list(self.metric_ids),
            "sourceEntity": self.source_entity,
            "timeField": self.time_field,
            "researchPolicy": self.research_policy,
        }


class SemanticPlanValidator:
    """Validate P2 QueryIR before deterministic SQL compilation.

    This validator owns semantic compatibility rules. It does not parse SQL and
    it never tries to repair missing business meaning with model guesses.
    """

    def __init__(self, semantics: SemanticRegistry, metadata: MetadataProvider) -> None:
        self._semantics = semantics
        self._metadata = metadata

    def validate(self, authz: AuthzContext, ir: QueryIR) -> SemanticValidationResult:
        issues: list[SemanticIssue] = []
        metric_ids = ir.all_metric_ids()
        metrics = []
        for metric_id in metric_ids:
            metric = self._semantics.get(authz, metric_id)
            if metric is None:
                issues.append(SemanticIssue("UNKNOWN_METRIC", f"未知指标: {metric_id}"))
            else:
                metrics.append(metric)

        if not metrics:
            return SemanticValidationResult(False, tuple(issues), metric_ids, None, None)

        primary = metrics[0]
        source_entity = primary.source_entity
        time_field = primary.time_field
        table = self._metadata.get_table(authz, source_entity)
        if table is None:
            issues.append(
                SemanticIssue(
                    "UNKNOWN_SOURCE_ENTITY",
                    f"指标来源表不存在或不可见: {source_entity}",
                    {"sourceEntity": source_entity},
                )
            )

        for metric in metrics:
            if metric.source_entity != source_entity:
                issues.append(
                    SemanticIssue(
                        "CROSS_SOURCE_METRICS",
                        "多指标查询必须来自同一治理来源表；P2 不自动发明跨表关联。",
                        {"metric": metric.id, "sourceEntity": metric.source_entity},
                    )
                )
            if metric.time_field != time_field:
                issues.append(
                    SemanticIssue(
                        "INCOMPATIBLE_TIME_FIELD",
                        "多指标查询必须使用同一治理时间字段。",
                        {"metric": metric.id, "timeField": metric.time_field},
                    )
                )
            if table is not None:
                if table.column(metric.measure) is None:
                    issues.append(
                        SemanticIssue(
                            "UNKNOWN_MEASURE",
                            f"指标度量字段不存在: {metric.measure}",
                            {"metric": metric.id, "measure": metric.measure},
                        )
                    )
                if table.column(metric.time_field) is None:
                    issues.append(
                        SemanticIssue(
                            "UNKNOWN_TIME_FIELD",
                            f"指标时间字段不存在: {metric.time_field}",
                            {"metric": metric.id, "timeField": metric.time_field},
                        )
                    )

            if metric.kind is MetricKind.RATIO:
                numerator = self._semantics.get(authz, metric.numerator_metric_id)
                denominator = self._semantics.get(authz, metric.denominator_metric_id)
                if numerator is None or denominator is None:
                    issues.append(
                        SemanticIssue(
                            "RATIO_DEPENDENCY_MISSING",
                            f"比例指标 {metric.id} 缺少治理后的分子或分母指标。",
                        )
                    )
                elif (
                    numerator.source_entity != metric.source_entity
                    or denominator.source_entity != metric.source_entity
                ):
                    issues.append(
                        SemanticIssue(
                            "RATIO_SOURCE_MISMATCH",
                            f"比例指标 {metric.id} 的分子分母来源不一致。",
                        )
                    )

        if len(metrics) > 1 and any(metric.kind is MetricKind.DERIVED for metric in metrics):
            issues.append(
                SemanticIssue(
                    "DERIVED_MULTI_METRIC_UNSUPPORTED",
                    "派生比较指标不能与其他指标在同一 P2 SQL 中混合编译。",
                )
            )

        if ir.comparison is not ComparisonKind.NONE:
            if len(metrics) != 1:
                issues.append(
                    SemanticIssue(
                        "MULTI_METRIC_COMPARISON_UNSUPPORTED",
                        "同比/环比当前要求单一指标；请拆分为独立治理查询。",
                    )
                )
            if primary.kind is MetricKind.DERIVED:
                issues.append(
                    SemanticIssue(
                        "DERIVED_COMPARISON_DUPLICATED",
                        "派生指标已经定义比较语义，不能再次叠加同比/环比。",
                    )
                )
            if primary.time_grain.strip().upper() != "MONTH":
                issues.append(
                    SemanticIssue(
                        "COMPARISON_TIME_GRAIN_UNGOVERNED",
                        "P2 同比/环比要求指标治理为 MONTH 时间粒度。",
                        {"timeGrain": primary.time_grain},
                    )
                )
            if len(ir.time_values) > 1:
                issues.append(
                    SemanticIssue(
                        "COMPARISON_MULTIPLE_ANCHORS",
                        "同比/环比只能指定一个本期锚点。",
                    )
                )
        elif any(metric.additivity_time is Additivity.NON_ADDITIVE for metric in metrics):
            if len(ir.time_values) > 1:
                issues.append(
                    SemanticIssue(
                        "NON_ADDITIVE_OVER_TIME",
                        "时间非可加指标不能在普通查询中跨多个快照聚合。",
                    )
                )

        if table is not None:
            for dimension in ir.dimensions:
                if table.column(dimension) is None:
                    issues.append(
                        SemanticIssue(
                            "UNKNOWN_DIMENSION",
                            f"维度字段不存在: {dimension}",
                            {"dimension": dimension},
                        )
                    )
                for metric in metrics:
                    if metric.valid_dimensions and dimension not in metric.valid_dimensions:
                        issues.append(
                            SemanticIssue(
                                "INVALID_METRIC_DIMENSION",
                                f"指标 {metric.id} 不允许维度 {dimension}",
                                {"metric": metric.id, "dimension": dimension},
                            )
                        )

            for item in ir.filters:
                op = item.op.strip().casefold()
                if op not in _SUPPORTED_FILTERS:
                    issues.append(
                        SemanticIssue(
                            "UNSUPPORTED_FILTER_OPERATOR",
                            f"不支持的筛选操作: {item.op}",
                            {"operator": item.op},
                        )
                    )
                if table.column(item.field) is None:
                    issues.append(
                        SemanticIssue(
                            "UNKNOWN_FILTER_FIELD",
                            f"筛选字段不存在: {item.field}",
                            {"field": item.field},
                        )
                    )
                if op in {"in", "not_in"} and (
                    not isinstance(item.value, (list, tuple, set)) or not item.value
                ):
                    issues.append(
                        SemanticIssue(
                            "INVALID_FILTER_VALUE",
                            f"筛选 {item.field} {item.op} 需要非空列表。",
                        )
                    )
                if op == "between" and (
                    not isinstance(item.value, (list, tuple)) or len(item.value) != 2
                ):
                    issues.append(
                        SemanticIssue(
                            "INVALID_FILTER_VALUE",
                            f"筛选 {item.field} between 需要两个边界值。",
                        )
                    )

        if ir.order:
            direction = ir.order.strip().upper()
            if direction not in {"ASC", "DESC"}:
                issues.append(SemanticIssue("INVALID_ORDER", "排序方向只能是 ASC 或 DESC。"))
            order_metric = ir.order_metric_id or ir.metric_id
            if order_metric not in metric_ids:
                issues.append(
                    SemanticIssue(
                        "ORDER_METRIC_NOT_COMPILED",
                        "排序指标必须属于本次已编译指标。",
                        {"orderMetricId": order_metric},
                    )
                )
        if ir.limit is not None and not 1 <= ir.limit <= 10000:
            issues.append(
                SemanticIssue("INVALID_LIMIT", "TopN/Limit 必须在 1 到 10000 之间。")
            )

        return SemanticValidationResult(
            valid=not issues,
            issues=tuple(issues),
            metric_ids=metric_ids,
            source_entity=source_entity,
            time_field=time_field,
        )
