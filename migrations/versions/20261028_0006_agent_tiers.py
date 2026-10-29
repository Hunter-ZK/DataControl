"""Distinguish standard and multi-step Agent conversations.

Revision ID: 20261028_0006
Revises: 20261028_0005
"""
from alembic import op
import sqlalchemy as sa

revision = "20261028_0006"
down_revision = "20261028_0005"
branch_labels = None
depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table("sys_agent_conversation"):
        raise RuntimeError("R1-B conversation schema must exist before tier migration")
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("sys_agent_conversation")}
    if "task_tier" not in cols:
        op.add_column("sys_agent_conversation",
                      sa.Column("task_tier", sa.String(16), nullable=False,
                                server_default="standard"))


def downgrade():
    if "task_tier" in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("sys_agent_conversation")}:
        with op.batch_alter_table("sys_agent_conversation") as batch:
            batch.drop_column("task_tier")
