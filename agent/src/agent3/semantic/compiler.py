from __future__ import annotations

import re

from agent3.contracts.authz import AuthzContext
from agent3.metadata.provider import MetadataProvider
from agent3.semantic.models import Additivity, ComparisonKind, MandatoryFilter, MetricKind, QueryIR
from agent3.semantic.registry import SemanticRegistry

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
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


def _filter_sql(item: MandatoryFilter) -> str:
    operators = {"eq": "=", "ne": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
    op = operators.get(item.op)
    if op is None:
        raise SemanticCompileError(f"unsupported filter op: {item.op}")
    return f"{_ident(item.field)} {op} {_literal(item.value)}"


def _dedupe_filters(items: tuple[MandatoryFilter, ...]) -> tuple[MandatoryFilter, ...]:
    seen: set[tuple[str, str, str]] = set()
    result: list[MandatoryFilter] = []
    for item in items:
        key = (item.field, item.op, repr(item.value))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return tuple(result)


class SemanticCompiler:
    """Deterministic compiler for governed metric semantics.

    P2 supports governed base metrics, same-source ratio metrics, dimensions,
    snapshot semantics and TopN ordering. YoY/MoM are represented in QueryIR but
    fail closed until their calendar semantics are explicitly governed.
    """

    def __init__(self, registry: SemanticRegistry, metadata: MetadataProvider) -> None:
        self._registry = registry
        self._metadata = metadata

    def _metric_expression(self, authz: AuthzContext, metric) -> tuple[str, tuple[MandatoryFilter, ...]]:
        if metric.kind is MetricKind.BASE:
            return (
                f"{metric.aggregation.upper()}({_ident(metric.measure)}) AS {_ident(metric.id)}",
                metric.mandatory_filters,
            )

        if metric.kind is MetricKind.RATIO:
            numerator = self._registry.get(authz, metric.numerator_metric_id)
            denominator = self._registry.get(authz, metric.denominator_metric_id)
            if numerator is None or denominator is None:
                raise SemanticCompileError("ratio metric dependencies are missing")
            if numerator.source_entity != metric.source_entity or denominator.source_entity != metric.source_entity:
                raise SemanticCompileError("ratio metric dependencies must share the governed source entity")
            numerator_expr = f"{numerator.aggregation.upper()}({_ident(numerator.measure)})"
            denominator_expr = f"{denominator.aggregation.upper()}({_ident(denominator.measure)})"
            expression = (
                f"CASE WHEN {denominator_expr} = 0 THEN NULL "
                f"ELSE {numerator_expr} / {denominator_expr} END AS {_ident(metric.id)}"
            )
            filters = _dedupe_filters(
                (*metric.mandatory_filters, *numerator.mandatory_filters, *denominator.mandatory_filters)
            )
            return expression, filters

        raise SemanticCompileError(
            f"metric kind '{metric.kind.value}' requires a governed derived compiler before SQL generation"
        )

    def compile(self, authz: AuthzContext, ir: QueryIR) -> str:
        metric = self._registry.get(authz, ir.metric_id)
        if metric is None:
            raise SemanticCompileError(f"unknown metric: {ir.metric_id}")
        if ir.comparison is not ComparisonKind.NONE:
            raise SemanticCompileError(
                f"comparison '{ir.comparison.value}' requires governed calendar semantics; clarification/planning must resolve it before compilation"
            )

        table = self._metadata.get_table(authz, metric.source_entity)
        if table is None:
            raise SemanticCompileError(f"unknown source entity: {metric.source_entity}")
        if table.column(metric.measure) is None:
            raise SemanticCompileError(f"unknown measure: {metric.measure}")
        if table.column(metric.time_field) is None:
            raise SemanticCompileError(f"unknown time field: {metric.time_field}")
        for dim in ir.dimensions:
            if metric.valid_dimensions and dim not in metric.valid_dimensions:
                raise SemanticCompileError(f"dimension not valid for metric: {dim}")
            if table.column(dim) is None:
                raise SemanticCompileError(f"unknown dimension: {dim}")
        if metric.additivity_time is Additivity.NON_ADDITIVE and len(ir.time_values) > 1:
            raise SemanticCompileError("non-additive metric cannot aggregate across multiple snapshots")

        metric_expression, governed_filters = self._metric_expression(authz, metric)
        dims = [_ident(dim) for dim in ir.dimensions]
        select = [*dims, metric_expression]
        filters = _dedupe_filters((*governed_filters, *ir.filters))
        for item in filters:
            if table.column(item.field) is None:
                raise SemanticCompileError(f"unknown filter field: {item.field}")
        where_parts = [_filter_sql(item) for item in filters]
        table_name = _table(metric.source_entity)
        time_field = _ident(metric.time_field)

        if len(ir.time_values) == 1:
            value = str(ir.time_values[0]).strip()
            upper = value.upper()
            if upper in _LATEST or value in _LATEST:
                where_parts.append(f"{time_field} = (SELECT MAX({time_field}) FROM {table_name})")
            elif upper in _PREVIOUS or value in _PREVIOUS:
                where_parts.append(
                    f"{time_field} = (SELECT MAX({time_field}) FROM {table_name} "
                    f"WHERE {time_field} < (SELECT MAX({time_field}) FROM {table_name}))"
                )
            else:
                where_parts.append(f"{time_field} = {_literal(value)}")
        elif len(ir.time_values) > 1:
            values = ", ".join(_literal(value) for value in ir.time_values)
            where_parts.append(f"{time_field} IN ({values})")

        sql = f"SELECT {', '.join(select)} FROM {table_name}"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        if dims:
            sql += " GROUP BY " + ", ".join(dims)

        if ir.order:
            order = ir.order.strip().upper()
            if order not in {"ASC", "DESC"}:
                raise SemanticCompileError("order must be ASC or DESC")
            sql += f" ORDER BY {_ident(metric.id)} {order}"
        if ir.limit is not None:
            if ir.limit < 1 or ir.limit > 10000:
                raise SemanticCompileError("limit must be between 1 and 10000")
            sql += f" LIMIT {ir.limit}"
        return sql
