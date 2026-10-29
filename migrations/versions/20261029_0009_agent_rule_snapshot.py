"""Snapshot active Agent rules with each new run.

Revision ID: 20261029_0009
Revises: 20261029_0008
"""
from alembic import op
import sqlalchemy as sa

revision = "20261029_0009"
down_revision = "20261029_0008"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("sys_agent_turn"):
        columns = {column["name"] for column in inspector.get_columns("sys_agent_turn")}
        if "debug_context_json" not in columns:
            op.add_column("sys_agent_turn", sa.Column("debug_context_json", sa.Text(), nullable=True))


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("sys_agent_turn"):
        columns = {column["name"] for column in inspector.get_columns("sys_agent_turn")}
        if "debug_context_json" in columns:
            with op.batch_alter_table("sys_agent_turn") as batch:
                batch.drop_column("debug_context_json")
