from __future__ import annotations

from typing import Any

from agent3.adapters.mcp.authz import AuthzProvider
from agent3.semantic.models import ComparisonKind, MandatoryFilter, QueryIR
from agent3.services.core import Agent3Core


class MCPToolAdapter:
    """Thin protocol projection. No business rules belong here."""

    def __init__(self, core: Agent3Core, authz_provider: AuthzProvider) -> None:
        self._core = core
        self._authz = authz_provider

    def search_tables(self, query: str, limit: int = 8) -> dict[str, Any]:
        return self._core.search_tables(self._authz(), query, limit=limit)

    def search_assets(self, query: str, limit: int = 12) -> dict[str, Any]:
        return self._core.search_assets(self._authz(), query, limit=limit)

    def get_asset(self, asset_type: str, asset_id: str) -> dict[str, Any]:
        return self._core.get_asset(self._authz(), asset_type, asset_id)

    def find_references(self, asset_type: str, asset_id: str) -> dict[str, Any]:
        return self._core.find_references(self._authz(), asset_type, asset_id)

    def get_lineage_summary(self, asset_type: str, asset_id: str, depth: int = 1) -> dict[str, Any]:
        return self._core.get_lineage_summary(self._authz(), asset_type, asset_id, depth=depth)

    def revise_query(self, semantic_plan: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
        return self._core.revise_query(self._authz(), semantic_plan, changes)

    def get_schema(self, table_name: str) -> dict[str, Any]:
        return self._core.get_schema(self._authz(), table_name)

    def resolve_code_value(
        self,
        table_name: str,
        field: str,
        phrase: str,
        limit: int = 8,
    ) -> dict[str, Any]:
        return self._core.resolve_code_value(
            self._authz(),
            table_name,
            field,
            phrase,
            limit=limit,
        )

    def get_semantic_model(self, metric_id: str) -> dict[str, Any]:
        return self._core.get_semantic_model(self._authz(), metric_id)

    def resolve_metric(self, phrase: str) -> dict[str, Any]:
        return self._core.resolve_metric(self._authz(), phrase)

    def plan_metric(self, phrase: str, limit: int = 5) -> dict[str, Any]:
        return self._core.plan_metric(self._authz(), phrase, limit=limit)

    def search_verified_sql(self, query: str, limit: int = 5) -> dict[str, Any]:
        return self._core.search_verified_sql(self._authz(), query, limit=limit)

    def validate_sql(
        self,
        sql: str,
        dialect: str = "maxcompute",
        metric_id: str | None = None,
    ) -> dict[str, Any]:
        return self._core.validate_sql(
            self._authz(),
            sql,
            dialect=dialect,
            metric_id=metric_id,
        )

    def explain_sql(self, sql: str, dialect: str = "maxcompute") -> dict[str, Any]:
        return self._core.explain_sql(self._authz(), sql, dialect=dialect)

    def compile_query(
        self,
        metric_id: str,
        metric_ids: list[str] | None = None,
        dimensions: list[str] | None = None,
        time_values: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        comparison: str = "none",
        order: str = "",
        order_metric_id: str = "",
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Compile a governed P2 query plan.

        ``metric_id`` is the primary metric. ``metric_ids`` may contain compatible
        secondary metrics from the same source. Filters are declarative objects;
        raw SQL filter fragments are intentionally not accepted.
        """
        try:
            comparison_kind = ComparisonKind(comparison.casefold())
        except ValueError as exc:
            raise ValueError("comparison must be one of: none, yoy, mom") from exc
        ir = QueryIR(
            metric_id=metric_id,
            metric_ids=tuple(metric_ids or ()),
            dimensions=tuple(dimensions or ()),
            time_values=tuple(time_values or ()),
            filters=tuple(
                MandatoryFilter(
                    field=str(item["field"]),
                    op=str(item["op"]),
                    value=item.get("value"),
                )
                for item in (filters or ())
            ),
            comparison=comparison_kind,
            order=order,
            order_metric_id=order_metric_id,
            limit=limit,
        )
        return self._core.compile_query(self._authz(), ir)

    def check_naming(self, name: str) -> dict[str, Any]:
        return self._core.check_naming(self._authz(), name)

    def generate_ddl(self, table: str, columns: list[dict[str, Any]],
                     comment: str = "", partition_key: str | None = None) -> dict[str, Any]:
        return self._core.generate_ddl(self._authz(), table, columns,
                                       comment=comment, partition_key=partition_key)

    def generate_etl(self, source_table: str, target_table: str,
                     mappings: list[dict[str, str]],
                     source_partition: str | None = None) -> dict[str, Any]:
        return self._core.generate_etl(self._authz(), source_table, target_table, mappings,
                                       source_partition=source_partition)

    def generate_dq_checks(self, table_name: str, required_columns: list[str] | None = None,
                           unique_keys: list[str] | None = None) -> dict[str, Any]:
        return self._core.generate_dq_checks(self._authz(), table_name, required_columns,
                                             unique_keys)

    def submit_ddl(self, ddl: str) -> dict[str, Any]:
        return self._core.submit_ddl(self._authz(), ddl)
