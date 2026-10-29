"""Persist developer-only Agent runtime trace events.

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
    if not sa.inspect(op.get_bind()).has_table("sys_agent_debug_event"):
        op.create_table(
            "sys_agent_debug_event",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("turn_id", sa.String(36), sa.ForeignKey("sys_agent_turn.id"), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("source", sa.String(32)),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sys_agent_debug_event_turn_id "
        "ON sys_agent_debug_event (turn_id)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_sys_agent_debug_event_turn_id")
    op.drop_table("sys_agent_debug_event")
