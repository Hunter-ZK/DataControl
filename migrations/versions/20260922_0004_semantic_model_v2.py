"""Extend governed metrics for Semantic Model V2.

Revision ID: 20260922_0004
Revises: 20260921_0003
Create Date: 2026-09-22

The historical P1 baseline calls ``Base.metadata.create_all``. On a fresh
checkout that baseline therefore sees the *current* ORM model and may already
create newer columns before this revision is reached. Existing pre-P2 databases,
on the other hand, genuinely need these columns added. This revision must support
both paths and is intentionally idempotent.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260922_0004"
down_revision = "20260921_0003"
branch_labels = None
depends_on = None


_COLUMNS = (
    sa.Column("metric_kind", sa.String(length=16), nullable=False, server_default="BASE"),
    sa.Column("numerator_metric_code", sa.String(length=64), nullable=True),
    sa.Column("denominator_metric_code", sa.String(length=64), nullable=True),
    sa.Column("formula", sa.Text(), nullable=True),
    sa.Column("time_grain", sa.String(length=16), nullable=True),
    sa.Column("latest_strategy", sa.String(length=32), nullable=False, server_default="MAX"),
    sa.Column("mandatory_filters", sa.Text(), nullable=True),
    sa.Column("semantic_notes", sa.Text(), nullable=True),
)


def _column_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("biz_metric"):
        return set()
    return {column["name"] for column in inspector.get_columns("biz_metric")}


def upgrade() -> None:
    existing = _column_names()
    for column in _COLUMNS:
        if column.name not in existing:
            op.add_column("biz_metric", column)
            existing.add(column.name)


def downgrade() -> None:
    existing = _column_names()
    removable = [column.name for column in reversed(_COLUMNS) if column.name in existing]
    if not removable:
        return
    # batch mode keeps SQLite downgrade support while also working on MySQL.
    with op.batch_alter_table("biz_metric") as batch:
        for name in removable:
            batch.drop_column(name)
