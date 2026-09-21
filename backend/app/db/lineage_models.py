from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.models import Base


class ColumnLineage(Base):
    """Persisted field-level lineage fact.

    Dataset ids are duplicated intentionally so table-scoped lineage queries do not
    need to re-join columns merely to decide whether an edge enters/leaves a table.
    Source/target column ids remain the authoritative field identities.
    """

    __tablename__ = "rel_column_lineage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    src_dataset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"), index=True)
    src_column_id: Mapped[str] = mapped_column(ForeignKey("ast_column.asset_id"), index=True)
    dst_dataset_id: Mapped[str] = mapped_column(ForeignKey("ast_dataset.asset_id"), index=True)
    dst_column_id: Mapped[str] = mapped_column(ForeignKey("ast_column.asset_id"), index=True)
    transformation: Mapped[str | None] = mapped_column(Text)
    task_name: Mapped[str | None] = mapped_column(String(128))
    evidence: Mapped[str] = mapped_column(String(16), default="CONFIRMED")
    relation_type: Mapped[str] = mapped_column(String(24), default="DIRECT")

    __table_args__ = (
        UniqueConstraint(
            "src_column_id",
            "dst_column_id",
            "task_name",
            name="uq_column_lineage_edge",
        ),
    )
