"""Add persisted field-level lineage facts.

Revision ID: 20260921_0003
Revises: 20260920_0002
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa

revision = "20260921_0003"
down_revision = "20260920_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rel_column_lineage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("src_dataset_id", sa.String(length=32), nullable=False),
        sa.Column("src_column_id", sa.String(length=40), nullable=False),
        sa.Column("dst_dataset_id", sa.String(length=32), nullable=False),
        sa.Column("dst_column_id", sa.String(length=40), nullable=False),
        sa.Column("transformation", sa.Text(), nullable=True),
        sa.Column("task_name", sa.String(length=128), nullable=True),
        sa.Column("evidence", sa.String(length=16), nullable=False, server_default="CONFIRMED"),
        sa.Column("relation_type", sa.String(length=24), nullable=False, server_default="DIRECT"),
        sa.ForeignKeyConstraint(["src_dataset_id"], ["ast_dataset.asset_id"]),
        sa.ForeignKeyConstraint(["src_column_id"], ["ast_column.asset_id"]),
        sa.ForeignKeyConstraint(["dst_dataset_id"], ["ast_dataset.asset_id"]),
        sa.ForeignKeyConstraint(["dst_column_id"], ["ast_column.asset_id"]),
        sa.UniqueConstraint("src_column_id", "dst_column_id", "task_name", name="uq_column_lineage_edge"),
    )
    op.create_index("ix_rel_column_lineage_src_dataset_id", "rel_column_lineage", ["src_dataset_id"])
    op.create_index("ix_rel_column_lineage_dst_dataset_id", "rel_column_lineage", ["dst_dataset_id"])
    op.create_index("ix_rel_column_lineage_src_column_id", "rel_column_lineage", ["src_column_id"])
    op.create_index("ix_rel_column_lineage_dst_column_id", "rel_column_lineage", ["dst_column_id"])


def downgrade() -> None:
    op.drop_index("ix_rel_column_lineage_dst_column_id", table_name="rel_column_lineage")
    op.drop_index("ix_rel_column_lineage_src_column_id", table_name="rel_column_lineage")
    op.drop_index("ix_rel_column_lineage_dst_dataset_id", table_name="rel_column_lineage")
    op.drop_index("ix_rel_column_lineage_src_dataset_id", table_name="rel_column_lineage")
    op.drop_table("rel_column_lineage")
