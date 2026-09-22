from __future__ import annotations

from sqlglot import exp, parse, parse_one
from sqlglot.errors import ParseError

from agent3.sql.analysis.models import SQLAnalysis, SQLColumnRef

_DIALECTS = {"maxcompute": "hive", "odps": "hive", "dataworks": "hive"}


class SQLAnalysisError(ValueError):
    pass


def _dialect(name: str) -> str:
    return _DIALECTS.get(name.casefold(), name)


def _table_name(table: exp.Table) -> str:
    parts = [part for part in (table.catalog, table.db, table.name) if part]
    return ".".join(parts)


def _top_level_projection_aliases(tree: exp.Expression) -> frozenset[str]:
    """Return aliases produced by the outer query projection.

    ORDER BY may legally refer to a SELECT alias. Such a reference is not a
    source-column dependency and must not be sent to metadata validation as one.
    """
    select = tree if isinstance(tree, exp.Select) else tree.find(exp.Select)
    if select is None:
        return frozenset()
    return frozenset(
        selection.alias_or_name.casefold()
        for selection in select.selects
        if selection.alias_or_name and selection.alias_or_name != "*"
    )


def _is_order_alias_reference(column: exp.Column, projection_aliases: frozenset[str]) -> bool:
    if column.table or column.name.casefold() not in projection_aliases:
        return False
    parent = column.parent
    while parent is not None:
        if isinstance(parent, exp.Order):
            return True
        # Once another SELECT is reached this column belongs to a nested scope,
        # not the outer ORDER BY that owns the projection alias.
        if isinstance(parent, exp.Select):
            return False
        parent = parent.parent
    return False


class SQLAnalyzer:
    """Thin SQLGlot adapter; owns dialect mapping and parse-error translation only."""

    def analyze(self, sql: str, *, dialect: str = "maxcompute") -> SQLAnalysis:
        tree = self.parse(sql, dialect=dialect)
        tables = tuple(sorted({_table_name(table) for table in tree.find_all(exp.Table)}))
        projection_aliases = _top_level_projection_aliases(tree)
        columns = tuple(
            SQLColumnRef(table=(column.table or None), name=column.name)
            for column in tree.find_all(exp.Column)
            if not _is_order_alias_reference(column, projection_aliases)
        )
        where = tree.find(exp.Where)
        return SQLAnalysis(
            sql=sql,
            dialect=dialect,
            statement_type=tree.key.upper(),
            tables=tables,
            columns=columns,
            where_sql=where.sql(dialect=_dialect(dialect)) if where else None,
            # normalized_sql is also the product-facing canonical rendering after
            # validation. Keep semantics unchanged while making generated SQL
            # readable enough to review/copy directly from the DataAgent UI.
            normalized_sql=tree.sql(dialect=_dialect(dialect), pretty=True),
        )

    def parse_program(
        self,
        sql: str,
        *,
        dialect: str = "maxcompute",
    ) -> tuple[exp.Expression, ...]:
        normalized = sql.strip()
        if not normalized:
            raise SQLAnalysisError("SQL cannot be empty")
        try:
            statements = tuple(parse(normalized, read=_dialect(dialect)))
        except ParseError as exc:
            raise SQLAnalysisError(str(exc)) from exc
        if not statements:
            raise SQLAnalysisError("SQL cannot be empty")
        return statements

    def parse(self, sql: str, *, dialect: str = "maxcompute") -> exp.Expression:
        normalized = sql.strip()
        if not normalized:
            raise SQLAnalysisError("SQL cannot be empty")
        try:
            return parse_one(normalized, read=_dialect(dialect))
        except ParseError as exc:
            raise SQLAnalysisError(str(exc)) from exc
