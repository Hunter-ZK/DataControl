from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import (
    CodeTable,
    Column,
    DataStandard,
    Dataset,
    Metric,
    StatisticalSystem,
    WordRoot,
)
from backend.app.search.engine import SearchEngine


def rebuild_search_index(db: Session) -> int:
    """Rebuild the read-only search index from persisted asset facts.

    The search index is derivative data only. Stable identity and business facts remain
    in the relational store.
    """

    docs: list[dict[str, str]] = []
    datasets = {x.asset_id: x for x in db.execute(select(Dataset)).scalars().all()}

    for ds in datasets.values():
        docs.append(
            {
                "asset_id": ds.asset_id,
                "asset_type": "TABLE",
                "title": ds.biz_name,
                "technical_name": ds.table_name,
                "body": " ".join(
                    filter(
                        None,
                        [
                            ds.biz_definition,
                            ds.stat_caliber,
                            ds.catalog_code,
                            ds.layer_code,
                            ds.tech_owner,
                            ds.biz_owner,
                            ds.owner_dept,
                        ],
                    )
                ),
            }
        )

    for column in db.execute(select(Column)).scalars().all():
        parent = datasets.get(column.dataset_id)
        technical_name = (
            f"{parent.table_name}.{column.column_name}" if parent else f"{column.dataset_id}.{column.column_name}"
        )
        docs.append(
            {
                "asset_id": column.asset_id,
                "asset_type": "COLUMN",
                "title": column.cn_name or column.column_name,
                "technical_name": technical_name,
                "body": " ".join(
                    filter(
                        None,
                        [
                            column.biz_definition,
                            column.data_type,
                            column.standard_no,
                            column.code_table_no,
                            parent.biz_name if parent else None,
                            parent.catalog_code if parent else None,
                        ],
                    )
                ),
            }
        )

    for metric in db.execute(select(Metric)).scalars().all():
        docs.append(
            {
                "asset_id": metric.asset_id,
                "asset_type": "METRIC",
                "title": metric.metric_name,
                "technical_name": metric.metric_code,
                "body": " ".join(
                    filter(
                        None,
                        [
                            metric.aliases,
                            metric.biz_definition,
                            metric.caliber_desc,
                            metric.aggregation,
                            metric.measure_column,
                            metric.stat_system_code,
                        ],
                    )
                ),
            }
        )

    for table in db.execute(select(CodeTable)).scalars().all():
        docs.append(
            {
                "asset_id": table.asset_id,
                "asset_type": "CODE_TABLE",
                "title": table.code_table_name,
                "technical_name": table.code_table_no,
                "body": " ".join(
                    filter(
                        None,
                        [table.en_name, table.description, table.category_code, table.source_standard, table.owner],
                    )
                ),
            }
        )

    for standard in db.execute(select(DataStandard)).scalars().all():
        docs.append(
            {
                "asset_id": standard.asset_id,
                "asset_type": "STANDARD",
                "title": standard.standard_name,
                "technical_name": standard.standard_no,
                "body": " ".join(
                    filter(
                        None,
                        [
                            standard.en_name,
                            standard.business_definition,
                            standard.business_rule,
                            standard.data_type,
                            standard.code_table_no,
                            standard.owner_dept,
                        ],
                    )
                ),
            }
        )

    for root in db.execute(select(WordRoot)).scalars().all():
        docs.append(
            {
                "asset_id": root.asset_id,
                "asset_type": "WORD_ROOT",
                "title": root.cn_name,
                "technical_name": root.root_en,
                "body": " ".join(filter(None, [root.en_full, root.synonyms, root.description])),
            }
        )

    for system in db.execute(select(StatisticalSystem)).scalars().all():
        docs.append(
            {
                "asset_id": system.asset_id,
                "asset_type": "STAT_SYSTEM",
                "title": system.stat_system_name,
                "technical_name": system.stat_system_code,
                "body": " ".join(
                    filter(None, [system.version, system.issuer, system.document_no, system.description])
                ),
            }
        )

    SearchEngine().rebuild(docs)
    return len(docs)
