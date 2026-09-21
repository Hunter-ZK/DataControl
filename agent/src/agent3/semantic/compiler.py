from __future__ import annotations

import re
from agent3.contracts.authz import AuthzContext
from agent3.metadata.provider import MetadataProvider
from agent3.semantic.models import Additivity, MandatoryFilter, QueryIR
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


class SemanticCompiler:
    """Deterministic compiler for one governed metric plus dimensions and time semantics."""
    def __init__(self, registry: SemanticRegistry, metadata: MetadataProvider) -> None:
        self._registry = registry
        self._metadata = metadata

    def compile(self, authz: AuthzContext, ir: QueryIR) -> str:
        metric = self._registry.get(authz, ir.metric_id)
        if metric is None:
            raise SemanticCompileError(f"unknown metric: {ir.metric_id}")
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

        dims = [_ident(dim) for dim in ir.dimensions]
        select = [*dims, f"{metric.aggregation.upper()}({_ident(metric.measure)}) AS {_ident(metric.id)}"]
        filters = [*metric.mandatory_filters, *ir.filters]
        where_parts = [_filter_sql(item) for item in filters]
        table_name = _table(metric.source_entity)
        time_field = _ident(metric.time_field)

        if len(ir.time_values) == 1:
            value = str(ir.time_values[0]).strip()
            upper = value.upper()
            if upper in _LATEST or value in _LATEST:
                where_parts.append(
                    f"{time_field} = (SELECT MAX({time_field}) FROM {table_name})"
                )
            elif upper in _PREVIOUS or value in _PREVIOUS:
                where_parts.append(
                    f"{time_field} = (SELECT MAX({time_field}) FROM {table_name} "
                    f"WHERE {time_field} < (SELECT MAX({time_field}) FROM {table_name}))"
                )
            else:
                where_parts.append(f"{time_field} = {_literal(value)}")
        elif len(ir.time_values) > 1:
            values = ", ".join(_literal(v) for v in ir.time_values)
            where_parts.append(f"{time_field} IN ({values})")

        sql = f"SELECT {', '.join(select)} FROM {table_name}"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        if dims:
            sql += " GROUP BY " + ", ".join(dims)
        return sql
