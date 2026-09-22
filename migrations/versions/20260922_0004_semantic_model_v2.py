"""Extend governed metrics for Semantic Model V2.

Revision ID: 20260922_0004
Revises: 20260921_0003
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20260922_0004"
down_revision = "20260921_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("biz_metric") as batch:
        batch.add_column(sa.Column("metric_kind", sa.String(length=16), nullable=False, server_default="BASE"))
        batch.add_column(sa.Column("numerator_metric_code", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("denominator_metric_code", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("formula", sa.Text(), nullable=True))
        batch.add_column(sa.Column("time_grain", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("latest_strategy", sa.String(length=32), nullable=False, server_default="MAX"))
        batch.add_column(sa.Column("mandatory_filters", sa.Text(), nullable=True))
        batch.add_column(sa.Column("semantic_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("biz_metric") as batch:
        batch.drop_column("semantic_notes")
        batch.drop_column("mandatory_filters")
        batch.drop_column("latest_strategy")
        batch.drop_column("time_grain")
        batch.drop_column("formula")
        batch.drop_column("denominator_metric_code")
        batch.drop_column("numerator_metric_code")
        batch.drop_column("metric_kind")
