from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select

from backend.app.db.lineage_models import ColumnLineage
from backend.app.db.models import Base, Column, Dataset, TableLineage
from backend.app.db.session import SessionLocal, engine

MEASURE_HINTS = (
    "balance",
    "amount",
    "count",
    "exposure",
)


def _column_map(columns: list[Column]) -> dict[str, dict[str, Column]]:
    grouped: dict[str, dict[str, Column]] = defaultdict(dict)
    for column in columns:
        grouped[column.dataset_id][column.column_name] = column
    return grouped


def _transformation(name: str, src_layer: str, dst_layer: str) -> tuple[str, str]:
    is_measure = any(token in name for token in MEASURE_HINTS)
    if is_measure and dst_layer in {"DWS", "ADS"} and src_layer != dst_layer:
        return f"SUM({name})", "AGGREGATED"
    return name, "DIRECT"


def main() -> None:
    # Importing ColumnLineage registers the model so create_all remains useful for
    # standalone sample execution. Normal development setup still upgrades Alembic first.
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.execute(delete(ColumnLineage))
        datasets = {item.asset_id: item for item in db.execute(select(Dataset)).scalars().all()}
        columns = db.execute(select(Column)).scalars().all()
        columns_by_dataset = _column_map(columns)
        table_edges = db.execute(select(TableLineage).order_by(TableLineage.id)).scalars().all()

        created = 0
        derived = 0
        for edge in table_edges:
            src_dataset = datasets.get(edge.src_asset_id)
            dst_dataset = datasets.get(edge.dst_asset_id)
            if src_dataset is None or dst_dataset is None:
                continue
            src_columns = columns_by_dataset.get(edge.src_asset_id, {})
            dst_columns = columns_by_dataset.get(edge.dst_asset_id, {})

            for name in sorted(set(src_columns) & set(dst_columns)):
                src_column = src_columns[name]
                dst_column = dst_columns[name]
                transformation, relation_type = _transformation(
                    name,
                    src_dataset.layer_code,
                    dst_dataset.layer_code,
                )
                db.add(
                    ColumnLineage(
                        src_dataset_id=edge.src_asset_id,
                        src_column_id=src_column.asset_id,
                        dst_dataset_id=edge.dst_asset_id,
                        dst_column_id=dst_column.asset_id,
                        transformation=transformation,
                        task_name=edge.task_name,
                        evidence=edge.evidence,
                        relation_type=relation_type,
                    )
                )
                created += 1

            if "stat_date" in src_columns and "stat_month" in dst_columns:
                db.add(
                    ColumnLineage(
                        src_dataset_id=edge.src_asset_id,
                        src_column_id=src_columns["stat_date"].asset_id,
                        dst_dataset_id=edge.dst_asset_id,
                        dst_column_id=dst_columns["stat_month"].asset_id,
                        transformation="DATE_FORMAT(stat_date, 'yyyy-MM')",
                        task_name=edge.task_name,
                        evidence=edge.evidence,
                        relation_type="DERIVED",
                    )
                )
                created += 1
                derived += 1

        db.commit()
        print(
            f"Next-P1 field lineage enriched: {created} edges "
            f"({derived} derived date mappings) across {len(table_edges)} table relations"
        )


if __name__ == "__main__":
    main()
