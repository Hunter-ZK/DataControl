from __future__ import annotations

import re

from agent3.contracts.authz import AuthzContext
from agent3.metadata.provider import MetadataProvider
from agent3.semantic.models import (
    Additivity,
    ComparisonKind,
    MandatoryFilter,
    MetricDefinition,
    MetricKind,
    QueryIR,
)
from agent3.semantic.registry import SemanticRegistry

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
_MONTH = re.compile(r"^(\d{4})-(\d{2})$")
_DERIVED_YOY = re.compile(
    r"^\(current\((?P<metric>[A-Za-z_][A-Za-z0-9_]*)\)\s*-\s*yoy\((?P=metric)\)\)\s*/\s*yoy\((?P=metric)\)$",
    re.IGNORECASE,
)
_LATEST = {"LATEST", "CURRENT", "本期", "当期", "当前", "最新", "最近一期"}
_PREVIOUS = {"PREVIOUS", "PRIOR", "上期", "上一期"}


class SemanticCompileError(ValueError):
    pass


def _ident(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise SemanticCompileError(f"invalid identifier: {value}")
    return value


def _table(value: str) -> str:
    if not _TABLE.fullmatch(value):
        raise SemanticCompileError(f"invalid table: {value}")
    return value


def _literal(value: object) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _like_literal(value: object, *, prefix: str = "", suffix: str = "") -> str:
    text = str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return _literal(prefix + text + suffix)


def _filter_sql(item: MandatoryFilter) -> str:
    field = _ident(item.field)
    op = item.op.strip().casefold()
    scalar_ops = {"eq": "=", "ne": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
    if op in scalar_ops:
        return f"{field} {scalar_ops[op]} {_literal(item.value)}"
    if op in {"in", "not_in"}:
        if not isinstance(item.value, (list, tuple, set)) or not item.value:
            raise SemanticCompileError(f"filter '{op}' requires a non-empty list")
        values = ", ".join(_literal(value) for value in item.value)
        keyword = "NOT IN" if op == "not_in" else "IN"
        return f"{field} {keyword} ({values})"
    if op == "between":
        if not isinstance(item.value, (list, tuple)) or len(item.value) != 2:
            raise SemanticCompileError("filter 'between' requires exactly two values")
        return f"{field} BETWEEN {_literal(item.value[0])} AND {_literal(item.value[1])}"
    if op == "contains":
        return f"{field} LIKE {_like_literal(item.value, prefix='%', suffix='%')} ESCAPE '\\\\'"
    if op == "startswith":
        return f"{field} LIKE {_like_literal(item.value, suffix='%')} ESCAPE '\\\\'"
    if op == "endswith":
        return f"{field} LIKE {_like_literal(item.value, prefix='%')} ESCAPE '\\\\'"
    if op == "is_null":
        return f"{field} IS NULL"
    if op == "is_not_null":
        return f"{field} IS NOT NULL"
    raise SemanticCompileError(f"unsupported filter op: {item.op}")


def _dedupe_filters(items: tuple[MandatoryFilter, ...]) -> tuple[MandatoryFilter, ...]:
    seen: set[tuple[str, str, str]] = set()
    result: list[MandatoryFilter] = []
    for item in items:
        key = (item.field.casefold(), item.op.casefold(), repr(item.value))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return tuple(result)


def _previous_month_literal(value: str, offset: int) -> str:
    match = _MONTH.fullmatch(value)
    if not match:
        raise SemanticCompileError(
            "monthly comparison requires an ISO YYYY-MM period or LATEST/PREVIOUS"
        )
    year = int(match.group(1))
    month = int(match.group(2))
    absolute = year * 12 + (month - 1) + offset
    target_year, target_month_zero = divmod(absolute, 12)
    return f"{target_year:04d}-{target_month_zero + 1:02d}"


def _dynamic_month_offset(current_expr: str, offset_months: int) -> str:
    """Return MaxCompute SQL for an ISO YYYY-MM value shifted by whole months.

    This deliberately avoids relying on engine session date parsing. The semantic
    model governs MONTH as ISO YYYY-MM, and the compiler transforms that string
    deterministically using MaxCompute string/numeric functions.
    """
    if offset_months == -12:
        return (
            "CONCAT("
            f"CAST(CAST(SUBSTR({current_expr}, 1, 4) AS BIGINT) - 1 AS STRING), "
            f"SUBSTR({current_expr}, 5)"
            ")"
        )
    if offset_months == -1:
        year = f"CAST(SUBSTR({current_expr}, 1, 4) AS BIGINT)"
        month = f"CAST(SUBSTR({current_expr}, 6, 2) AS BIGINT)"
        return (
            "CONCAT("
            f"CAST(CASE WHEN {month} = 1 THEN {year} - 1 ELSE {year} END AS STRING), "
            "'-', "
            f"LPAD(CAST(CASE WHEN {month} = 1 THEN 12 ELSE {month} - 1 END AS STRING), 2, '0')"
            ")"
        )
    raise SemanticCompileError(f"unsupported governed month offset: {offset_months}")


class SemanticCompiler:
    """Deterministic compiler for governed P2 semantic query plans.

    Supported P2 surface:
    - compatible same-source multi-metric queries;
    - BASE and same-source RATIO metrics;
    - governed derived YoY metrics;
    - explicit YoY/MoM comparison for MONTH metrics;
    - TopN ordering;
    - declarative complex filters (no raw SQL fragments).

    Unsupported or cross-source combinations fail closed instead of asking the
    language model to invent joins or calendar logic.
    """

    def __init__(self, registry: SemanticRegistry, metadata: MetadataProvider) -> None:
        self._registry = registry
        self._metadata = metadata

    def _dependencies(
        self,
        authz: AuthzContext,
        metric: MetricDefinition,
    ) -> tuple[MetricDefinition, ...]:
        if metric.kind is MetricKind.RATIO:
            numerator = self._registry.get(authz, metric.numerator_metric_id)
            denominator = self._registry.get(authz, metric.denominator_metric_id)
            if numerator is None or denominator is None:
                raise SemanticCompileError(f"ratio metric dependencies are missing: {metric.id}")
            return numerator, denominator
        if metric.kind is MetricKind.DERIVED:
            match = _DERIVED_YOY.fullmatch(metric.formula.strip())
            if not match:
                raise SemanticCompileError(
                    f"derived metric '{metric.id}' has no supported governed compiler formula"
                )
            base = self._registry.get(authz, match.group("metric"))
            if base is None:
                raise SemanticCompileError(f"derived metric dependency is missing: {metric.id}")
            return (base,)
        return ()

    def _metric_expression(
        self,
        authz: AuthzContext,
        metric: MetricDefinition,
        *,
        alias: str | None = None,
    ) -> tuple[str, tuple[MandatoryFilter, ...]]:
        output_alias = _ident(alias or metric.id)
        if metric.kind is MetricKind.BASE:
            return (
                f"{metric.aggregation.upper()}({_ident(metric.measure)}) AS {output_alias}",
                metric.mandatory_filters,
            )

        if metric.kind is MetricKind.RATIO:
            numerator, denominator = self._dependencies(authz, metric)
            if numerator.source_entity != metric.source_entity or denominator.source_entity != metric.source_entity:
                raise SemanticCompileError("ratio metric dependencies must share the governed source entity")
            numerator_expr = f"{numerator.aggregation.upper()}({_ident(numerator.measure)})"
            denominator_expr = f"{denominator.aggregation.upper()}({_ident(denominator.measure)})"
            expression = (
                f"CASE WHEN {denominator_expr} = 0 THEN NULL "
                f"ELSE {numerator_expr} / {denominator_expr} END AS {output_alias}"
            )
            filters = _dedupe_filters(
                (*metric.mandatory_filters, *numerator.mandatory_filters, *denominator.mandatory_filters)
            )
            return expression, filters

        raise SemanticCompileError(
            f"metric kind '{metric.kind.value}' requires comparison compilation"
        )

    @staticmethod
    def _conditional_aggregate(metric: MetricDefinition, condition: str) -> str:
        aggregation = metric.aggregation.strip().upper()
        measure = _ident(metric.measure)
        if aggregation == "SUM":
            return f"SUM(CASE WHEN {condition} THEN {measure} ELSE 0 END)"
        if aggregation == "COUNT":
            return f"COUNT(CASE WHEN {condition} THEN {measure} ELSE NULL END)"
        if aggregation in {"AVG", "MAX", "MIN"}:
            return f"{aggregation}(CASE WHEN {condition} THEN {measure} ELSE NULL END)"
        raise SemanticCompileError(
            f"comparison does not support aggregation '{metric.aggregation}' for {metric.id}"
        )

    def _period_metric_expression(
        self,
        authz: AuthzContext,
        metric: MetricDefinition,
        condition: str,
    ) -> tuple[str, tuple[MandatoryFilter, ...]]:
        if metric.kind is MetricKind.BASE:
            return self._conditional_aggregate(metric, condition), metric.mandatory_filters
        if metric.kind is MetricKind.RATIO:
            numerator, denominator = self._dependencies(authz, metric)
            numerator_expr = self._conditional_aggregate(numerator, condition)
            denominator_expr = self._conditional_aggregate(denominator, condition)
            filters = _dedupe_filters(
                (*metric.mandatory_filters, *numerator.mandatory_filters, *denominator.mandatory_filters)
            )
            return (
                f"CASE WHEN {denominator_expr} = 0 THEN NULL "
                f"ELSE {numerator_expr} / {denominator_expr} END",
                filters,
            )
        raise SemanticCompileError(
            f"period comparison is not directly supported for metric kind '{metric.kind.value}'"
        )

    def _validate_metric_table(
        self,
        authz: AuthzContext,
        metric: MetricDefinition,
        *,
        dimensions: tuple[str, ...],
        filters: tuple[MandatoryFilter, ...],
    ):
        table = self._metadata.get_table(authz, metric.source_entity)
        if table is None:
            raise SemanticCompileError(f"unknown source entity: {metric.source_entity}")

        required_columns = {metric.measure, metric.time_field}
        for dependency in self._dependencies(authz, metric):
            required_columns.add(dependency.measure)
            if dependency.source_entity != metric.source_entity:
                raise SemanticCompileError(
                    f"metric dependency source mismatch: {dependency.id} -> {dependency.source_entity}"
                )
        for column_name in required_columns:
            if table.column(column_name) is None:
                raise SemanticCompileError(f"unknown metric field: {column_name}")

        for dim in dimensions:
            if metric.valid_dimensions and dim not in metric.valid_dimensions:
                raise SemanticCompileError(f"dimension not valid for metric {metric.id}: {dim}")
            if table.column(dim) is None:
                raise SemanticCompileError(f"unknown dimension: {dim}")
        for item in filters:
            if table.column(item.field) is None:
                raise SemanticCompileError(f"unknown filter field: {item.field}")
        return table

    @staticmethod
    def _current_period_expression(metric: MetricDefinition, table_name: str, values: tuple[str, ...]) -> str:
        time_field = _ident(metric.time_field)
        if not values:
            return f"(SELECT MAX({time_field}) FROM {table_name})"
        if len(values) != 1:
            raise SemanticCompileError("comparison accepts exactly one current period anchor")
        value = str(values[0]).strip()
        upper = value.upper()
        if upper in _LATEST or value in _LATEST:
            return f"(SELECT MAX({time_field}) FROM {table_name})"
        if upper in _PREVIOUS or value in _PREVIOUS:
            return (
                f"(SELECT MAX({time_field}) FROM {table_name} "
                f"WHERE {time_field} < (SELECT MAX({time_field}) FROM {table_name}))"
            )
        return _literal(value)

    @staticmethod
    def _comparison_period_expression(
        metric: MetricDefinition,
        current_expr: str,
        current_values: tuple[str, ...],
        comparison: ComparisonKind,
    ) -> str:
        grain = metric.time_grain.strip().upper()
        if grain != "MONTH":
            raise SemanticCompileError(
                f"comparison '{comparison.value}' currently requires governed MONTH time_grain"
            )
        offset = -12 if comparison is ComparisonKind.YOY else -1
        if current_values:
            value = str(current_values[0]).strip()
            if value.upper() not in _LATEST | _PREVIOUS and value not in _LATEST | _PREVIOUS:
                return _literal(_previous_month_literal(value, offset))
        return _dynamic_month_offset(current_expr, offset)

    def _compile_comparison(
        self,
        authz: AuthzContext,
        metric: MetricDefinition,
        ir: QueryIR,
        comparison: ComparisonKind,
        *,
        output_alias: str | None = None,
    ) -> str:
        if comparison not in {ComparisonKind.YOY, ComparisonKind.MOM}:
            raise SemanticCompileError(f"unsupported comparison: {comparison.value}")
        if metric.kind is MetricKind.DERIVED:
            raise SemanticCompileError("derived metric must resolve to its governed base metric before comparison")

        table_name = _table(metric.source_entity)
        governed_filters = metric.mandatory_filters
        if metric.kind is MetricKind.RATIO:
            _, governed_filters = self._metric_expression(authz, metric)
        filters = _dedupe_filters((*governed_filters, *ir.filters))
        self._validate_metric_table(
            authz,
            metric,
            dimensions=ir.dimensions,
            filters=filters,
        )

        current_expr = self._current_period_expression(metric, table_name, ir.time_values)
        prior_expr = self._comparison_period_expression(
            metric,
            current_expr,
            ir.time_values,
            comparison,
        )
        time_field = _ident(metric.time_field)
        current_value, _ = self._period_metric_expression(
            authz,
            metric,
            f"{time_field} = {current_expr}",
        )
        prior_value, _ = self._period_metric_expression(
            authz,
            metric,
            f"{time_field} = {prior_expr}",
        )

        dims = [_ident(dim) for dim in ir.dimensions]
        suffix = comparison.value
        alias = _ident(output_alias or f"{metric.id}_{suffix}")
        select = [
            *dims,
            f"{current_value} AS {_ident(metric.id + '_current')}",
            f"{prior_value} AS {_ident(metric.id + '_previous')}",
            (
                f"CASE WHEN {prior_value} IS NULL OR {prior_value} = 0 THEN NULL "
                f"ELSE ({current_value} - {prior_value}) / {prior_value} END AS {alias}"
            ),
        ]
        where_parts = [_filter_sql(item) for item in filters]
        where_parts.append(f"{time_field} IN ({current_expr}, {prior_expr})")
        sql = f"SELECT {', '.join(select)} FROM {table_name} WHERE " + " AND ".join(where_parts)
        if dims:
            sql += " GROUP BY " + ", ".join(dims)
        order_alias = alias
        if ir.order:
            direction = ir.order.strip().upper()
            if direction not in {"ASC", "DESC"}:
                raise SemanticCompileError("order must be ASC or DESC")
            sql += f" ORDER BY {order_alias} {direction}"
        if ir.limit is not None:
            if ir.limit < 1 or ir.limit > 10000:
                raise SemanticCompileError("limit must be between 1 and 10000")
            sql += f" LIMIT {ir.limit}"
        return sql

    def _compile_derived(self, authz: AuthzContext, metric: MetricDefinition, ir: QueryIR) -> str:
        match = _DERIVED_YOY.fullmatch(metric.formula.strip())
        if not match:
            raise SemanticCompileError(
                f"derived metric '{metric.id}' has no supported governed compiler formula"
            )
        base = self._registry.get(authz, match.group("metric"))
        if base is None:
            raise SemanticCompileError(f"derived metric dependency is missing: {metric.id}")
        if base.source_entity != metric.source_entity:
            raise SemanticCompileError("derived metric and base metric must share source entity")
        merged = QueryIR(
            metric_id=base.id,
            dimensions=ir.dimensions,
            filters=_dedupe_filters((*metric.mandatory_filters, *ir.filters)),
            time_values=ir.time_values,
            comparison=ComparisonKind.YOY,
            order=ir.order,
            order_metric_id=metric.id,
            limit=ir.limit,
        )
        return self._compile_comparison(
            authz,
            base,
            merged,
            ComparisonKind.YOY,
            output_alias=metric.id,
        )

    def compile(self, authz: AuthzContext, ir: QueryIR) -> str:
        metric_ids = ir.all_metric_ids()
        if not metric_ids:
            raise SemanticCompileError("at least one metric is required")
        metrics: list[MetricDefinition] = []
        for metric_id in metric_ids:
            metric = self._registry.get(authz, metric_id)
            if metric is None:
                raise SemanticCompileError(f"unknown metric: {metric_id}")
            metrics.append(metric)

        primary = metrics[0]
        if primary.kind is MetricKind.DERIVED:
            if len(metrics) > 1:
                raise SemanticCompileError("derived comparison metrics cannot be combined with other metrics in one query")
            if ir.comparison is not ComparisonKind.NONE:
                raise SemanticCompileError("derived metric already defines its governed comparison semantics")
            return self._compile_derived(authz, primary, ir)

        if ir.comparison is not ComparisonKind.NONE:
            if len(metrics) > 1:
                raise SemanticCompileError("multi-metric comparison is not yet a governed single-query operation")
            return self._compile_comparison(authz, primary, ir, ir.comparison)

        source = primary.source_entity
        time_field = primary.time_field
        for metric in metrics[1:]:
            if metric.source_entity != source:
                raise SemanticCompileError(
                    "multi-metric query requires metrics from the same governed source entity"
                )
            if metric.time_field != time_field:
                raise SemanticCompileError(
                    "multi-metric query requires metrics with the same governed time field"
                )

        if any(metric.additivity_time is Additivity.NON_ADDITIVE for metric in metrics) and len(ir.time_values) > 1:
            raise SemanticCompileError("non-additive metrics cannot aggregate across multiple snapshots")

        expressions: list[str] = []
        governed_filters: tuple[MandatoryFilter, ...] = ()
        for metric in metrics:
            expression, metric_filters = self._metric_expression(authz, metric)
            expressions.append(expression)
            governed_filters = _dedupe_filters((*governed_filters, *metric_filters))

        filters = _dedupe_filters((*governed_filters, *ir.filters))
        for metric in metrics:
            self._validate_metric_table(
                authz,
                metric,
                dimensions=ir.dimensions,
                filters=filters,
            )

        dims = [_ident(dim) for dim in ir.dimensions]
        table_name = _table(source)
        where_parts = [_filter_sql(item) for item in filters]
        period_field = _ident(time_field)

        if len(ir.time_values) == 1:
            value = str(ir.time_values[0]).strip()
            upper = value.upper()
            if upper in _LATEST or value in _LATEST:
                where_parts.append(
                    f"{period_field} = (SELECT MAX({period_field}) FROM {table_name})"
                )
            elif upper in _PREVIOUS or value in _PREVIOUS:
                where_parts.append(
                    f"{period_field} = (SELECT MAX({period_field}) FROM {table_name} "
                    f"WHERE {period_field} < (SELECT MAX({period_field}) FROM {table_name}))"
                )
            else:
                where_parts.append(f"{period_field} = {_literal(value)}")
        elif len(ir.time_values) > 1:
            values = ", ".join(_literal(value) for value in ir.time_values)
            where_parts.append(f"{period_field} IN ({values})")

        sql = f"SELECT {', '.join([*dims, *expressions])} FROM {table_name}"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        if dims:
            sql += " GROUP BY " + ", ".join(dims)

        if ir.order:
            direction = ir.order.strip().upper()
            if direction not in {"ASC", "DESC"}:
                raise SemanticCompileError("order must be ASC or DESC")
            order_metric = ir.order_metric_id or primary.id
            if order_metric not in metric_ids:
                raise SemanticCompileError("order_metric_id must be one of the compiled metrics")
            sql += f" ORDER BY {_ident(order_metric)} {direction}"
        if ir.limit is not None:
            if ir.limit < 1 or ir.limit > 10000:
                raise SemanticCompileError("limit must be between 1 and 10000")
            sql += f" LIMIT {ir.limit}"
        return sql
