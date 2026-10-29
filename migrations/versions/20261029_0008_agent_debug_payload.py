"""Store sanitized Agent tool input/output for the developer workbench.

Revision ID: 20261029_0008
Revises: 20261028_0007
"""
from alembic import op
import sqlalchemy as sa

revision = "20261029_0008"
down_revision = "20261028_0007"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("sys_agent_tool_event"):
        columns = {column["name"] for column in inspector.get_columns("sys_agent_tool_event")}
        if "payload_json" not in columns:
            op.add_column("sys_agent_tool_event", sa.Column("payload_json", sa.Text(), nullable=True))


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("sys_agent_tool_event"):
        columns = {column["name"] for column in inspector.get_columns("sys_agent_tool_event")}
        if "payload_json" in columns:
            with op.batch_alter_table("sys_agent_tool_event") as batch:
                batch.drop_column("payload_json")
