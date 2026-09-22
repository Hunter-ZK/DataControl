from __future__ import annotations

from dataclasses import asdict
from typing import Any

from agent3.contracts.authz import AuthzContext
from agent3.knowledge.injection import scan_retrieved_evidence
from agent3.knowledge.verified_sql import InMemoryVerifiedSQLStore
from agent3.metadata.provider import MetadataProvider
from agent3.semantic.compiler import SemanticCompiler
from agent3.semantic.models import (
    ClarificationOption,
    ClarificationRequest,
    ComparisonKind,
    MetricKind,
    QueryIR,
    SelectionMode,
)
from agent3.semantic.registry import SemanticRegistry
from agent3.sql.analysis.analyzer import SQLAnalysisError, SQLAnalyzer
from agent3.sql.validation.validator import SQLValidator


class Agent3Core:
    """Harness-agnostic service facade. Every public method takes AuthzContext first."""

    def __init__(
        self,
        *,
        metadata: MetadataProvider,
        semantics: SemanticRegistry,
        verified_sql: InMemoryVerifiedSQLStore | None = None,
    ) -> None:
        self.metadata = metadata
        self.semantics = semantics
        self.verified_sql = verified_sql or InMemoryVerifiedSQLStore()
        self.validator = SQLValidator(metadata, semantics)
        self.analyzer = SQLAnalyzer()
        self.compiler = SemanticCompiler(semantics, metadata)

    def search_tables(self, authz: AuthzContext, query: str, *, limit: int = 8) -> dict[str, Any]:
        tables = self.metadata.search_tables(authz, query, limit=limit)
        return {
            "tables": [
                {
                    "full_name": table.full_name,
                    "description": table.description,
                    "partition_fields": list(table.partition_fields),
                    "row_count_estimate": table.row_count_estimate,
                    "warnings": list(scan_retrieved_evidence(table.description)),
                }
                for table in tables
            ]
        }

    def get_schema(self, authz: AuthzContext, table_name: str) -> dict[str, Any]:
        table = self.metadata.get_table(authz, table_name)
        if table is None:
            return {"found": False, "table": table_name}
        return {
            "found": True,
            "table": table.full_name,
            "description": table.description,
            "partition_fields": list(table.partition_fields),
            "columns": [asdict(column) for column in table.columns],
            "warnings": list(
                scan_retrieved_evidence(
                    "\n".join([table.description, *(column.description for column in table.columns)])
                )
            ),
        }

    def resolve_code_value(
        self,
        authz: AuthzContext,
        table_name: str,
        field: str,
        phrase: str,
        *,
        limit: int = 8,
    ) -> dict[str, Any]:
        """Resolve a business label such as 人民币 to a governed code value.

        The field -> code-table association comes from DataControl metadata. No
        external source is consulted and no code is guessed when the association
        or value is missing.
        """
        table = self.metadata.get_table(authz, table_name)
        if table is None:
            return {
                "status": "table_not_found",
                "table": table_name,
                "field": field,
                "matches": [],
                "researchPolicy": "internal_only",
            }
        column = table.column(field)
        if column is None:
            return {
                "status": "field_not_found",
                "table": table.full_name,
                "field": field,
                "matches": [],
                "researchPolicy": "internal_only",
            }
        if not column.code_table_no:
            return {
                "status": "code_table_not_governed",
                "table": table.full_name,
                "field": field,
                "matches": [],
                "researchPolicy": "internal_only",
            }
        matches = self.metadata.resolve_code_values(
            authz,
            column.code_table_no,
            phrase,
            limit=limit,
        )
        return {
            "status": "resolved" if matches else "value_not_found",
            "table": table.full_name,
            "field": field,
            "codeTableNo": column.code_table_no,
            "matches": [asdict(item) for item in matches],
            "researchPolicy": "internal_only",
        }

    def get_semantic_model(self, authz: AuthzContext, metric_id: str) -> dict[str, Any]:
        metric = self.semantics.get(authz, metric_id)
        return {"found": metric is not None, "metric": asdict(metric) if metric else None}

    def resolve_metric(self, authz: AuthzContext, phrase: str) -> dict[str, Any]:
        metric = self.semantics.resolve(authz, phrase)
        return {"resolved": metric is not None, "metric": asdict(metric) if metric else None}

    def plan_metric(self, authz: AuthzContext, phrase: str, *, limit: int = 5) -> dict[str, Any]:
        """Resolve a metric or return structured, user-selectable clarification.

        P2 deliberately uses DataControl's internal governed evidence only. When
        the semantic evidence is insufficient, the caller must clarify with the
        user instead of falling back to external web research or inventing a
        business meaning.
        """
        resolved = self.semantics.resolve(authz, phrase)
        if resolved is not None:
            return {
                "status": "resolved",
                "phrase": phrase,
                "metric": asdict(resolved),
                "clarification": None,
                "researchPolicy": "internal_only",
            }

        candidates = self.semantics.candidates(authz, phrase, limit=limit)
        if candidates:
            options = tuple(
                ClarificationOption(
                    id=metric.id,
                    label=metric.name,
                    description=metric.caveats or f"来源：{metric.source_entity}",
                    value=metric.id,
                    metadata={
                        "metricKind": metric.kind.value,
                        "sourceEntity": metric.source_entity,
                        "measure": metric.measure,
                        "timeField": metric.time_field,
                    },
                )
                for _, metric in candidates
            )
            clarification = ClarificationRequest(
                id="metric_choice",
                question=f"“{phrase}”存在多个可用统计口径，请选择本次要使用的指标。",
                selection_mode=SelectionMode.SINGLE,
                options=options,
                allow_custom_input=True,
            )
            return {
                "status": "clarification_required",
                "phrase": phrase,
                "metric": None,
                "clarification": asdict(clarification),
                "researchPolicy": "internal_only",
            }

        return {
            "status": "evidence_insufficient",
            "phrase": phrase,
            "metric": None,
            "clarification": {
                "id": "metric_missing",
                "question": f"DataControl 内部可信语义中暂未找到“{phrase}”对应指标，请补充业务口径或换一个指标名称。",
                "selection_mode": "single",
                "options": [],
                "allow_custom_input": True,
            },
            "researchPolicy": "internal_only",
        }

    def search_verified_sql(self, authz: AuthzContext, query: str, *, limit: int = 5) -> dict[str, Any]:
        return {"items": [asdict(item) for item in self.verified_sql.search(authz, query, limit=limit)]}

    def validate_sql(
        self,
        authz: AuthzContext,
        sql: str,
        *,
        dialect: str = "maxcompute",
        metric_id: str | None = None,
    ) -> dict[str, Any]:
        return self.validator.validate(authz, sql, dialect=dialect, metric_id=metric_id).to_dict()

    def explain_sql(self, authz: AuthzContext, sql: str, *, dialect: str = "maxcompute") -> dict[str, Any]:
        _ = authz
        try:
            analysis = self.analyzer.analyze(sql, dialect=dialect)
        except SQLAnalysisError as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "statement_type": analysis.statement_type,
            "tables": list(analysis.tables),
            "columns": [{"table": column.table, "name": column.name} for column in analysis.columns],
            "where": analysis.where_sql,
            "normalized_sql": analysis.normalized_sql,
            "cost_estimate": None,
            "cost_estimate_status": "not_available_without_execution_backend",
        }

    def compile_query(self, authz: AuthzContext, ir: QueryIR) -> dict[str, Any]:
        metric_ids = ir.all_metric_ids()
        metrics = [self.semantics.get(authz, metric_id) for metric_id in metric_ids]
        if any(metric is None for metric in metrics):
            missing = [
                metric_id
                for metric_id, metric in zip(metric_ids, metrics, strict=True)
                if metric is None
            ]
            raise ValueError(f"unknown metric(s): {', '.join(missing)}")

        sql = self.compiler.compile(authz, ir)
        # The deterministic semantic compiler itself enforces governed metric,
        # dimension, filter, time, ratio and comparison contracts. The SQL
        # validator then checks syntax/metadata/risk. For the legacy single BASE
        # metric path we additionally retain metric-shape validation.
        single_base = (
            len(metric_ids) == 1
            and metrics[0] is not None
            and metrics[0].kind is MetricKind.BASE
            and ir.comparison is ComparisonKind.NONE
        )
        validation = self.validator.validate(
            authz,
            sql,
            metric_id=ir.metric_id if single_base else None,
        )
        return {
            "sql": sql,
            "validation": validation.to_dict(),
            "semanticPlan": {
                "metrics": list(metric_ids),
                "dimensions": list(ir.dimensions),
                "filters": [asdict(item) for item in ir.filters],
                "timeValues": list(ir.time_values),
                "comparison": ir.comparison.value,
                "order": ir.order,
                "orderMetricId": ir.order_metric_id or ir.metric_id,
                "limit": ir.limit,
                "researchPolicy": "internal_only",
                "semanticValidated": True,
            },
        }

    def register_verified_sql(
        self,
        authz: AuthzContext,
        *,
        question: str,
        sql: str,
        tables: tuple[str, ...],
        metrics: tuple[str, ...] = (),
        human_approved: bool = False,
    ) -> dict[str, Any]:
        if not human_approved:
            raise PermissionError("register_verified_sql requires explicit human approval")
        return asdict(
            self.verified_sql.register(
                authz,
                question=question,
                sql_text=sql,
                tables=tables,
                metrics=metrics,
            )
        )

    def submit_ddl(self, authz: AuthzContext, ddl: str) -> dict[str, Any]:
        _ = authz, ddl
        return {
            "accepted": False,
            "approval_required": True,
            "execution_enabled": False,
            "reason": "Production DDL execution is outside V1 and cannot be bypassed by an adapter.",
        }
