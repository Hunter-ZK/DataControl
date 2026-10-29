"""User-owned naming workbench export history.

Revision ID: 20261028_0007
Revises: 20261028_0006
"""
from alembic import op
import sqlalchemy as sa

revision = "20261028_0007"
down_revision = "20261028_0006"
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table("sys_naming_run"):
        return
    op.create_table(
        "sys_naming_run",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("sys_user.id"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("item_count", sa.Integer, nullable=False),
        sa.Column("result_json", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_sys_naming_run_user_id", "sys_naming_run", ["user_id"])
    op.create_index("ix_sys_naming_run_created_at", "sys_naming_run", ["created_at"])


def downgrade():
    op.drop_index("ix_sys_naming_run_created_at", table_name="sys_naming_run")
    op.drop_index("ix_sys_naming_run_user_id", table_name="sys_naming_run")
    op.drop_table("sys_naming_run")
