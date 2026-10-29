"""Server-side Agent conversations and bounded execution audit.

Revision ID: 20261028_0005
Revises: 20260922_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20261028_0005"
down_revision = "20260922_0004"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("sys_agent_conversation"):
        op.create_table(
            "sys_agent_conversation",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("sys_user.id"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("model_mode", sa.String(16), nullable=False),
            sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("session_id", sa.String(200)),
            sa.Column("legacy_messages_json", sa.Text()),
            sa.Column("context_asset_json", sa.Text()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    if not inspector.has_table("sys_agent_turn"):
        op.create_table(
            "sys_agent_turn",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("conversation_id", sa.String(36), sa.ForeignKey("sys_agent_conversation.id"), nullable=False),
            sa.Column("model_mode", sa.String(16), nullable=False),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("display_question", sa.Text()),
            sa.Column("status", sa.String(24), nullable=False),
            sa.Column("result_json", sa.Text()),
            sa.Column("error", sa.String(240)),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime()),
        )
    elif "display_question" not in {c["name"] for c in inspector.get_columns("sys_agent_turn")}:
        op.add_column("sys_agent_turn", sa.Column("display_question", sa.Text()))
    if not inspector.has_table("sys_agent_tool_event"):
        op.create_table(
            "sys_agent_tool_event",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("turn_id", sa.String(36), sa.ForeignKey("sys_agent_turn.id"), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(16), nullable=False),
            sa.Column("call_id", sa.String(128)),
            sa.Column("tool", sa.String(64), nullable=False),
            sa.Column("status", sa.String(16)),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    for name, table, column in (
        ("ix_sys_agent_conversation_user_id", "sys_agent_conversation", "user_id"),
        ("ix_sys_agent_turn_conversation_id", "sys_agent_turn", "conversation_id"),
        ("ix_sys_agent_turn_status", "sys_agent_turn", "status"),
        ("ix_sys_agent_tool_event_turn_id", "sys_agent_tool_event", "turn_id"),
    ):
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({column})")
    # SQLite guarantees one unfinished turn per conversation across Portal workers.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_one_open_turn "
        "ON sys_agent_turn (conversation_id) "
        "WHERE status IN ('queued','running','cancel_requested')"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_agent_one_open_turn")
    op.drop_table("sys_agent_tool_event")
    op.drop_table("sys_agent_turn")
    op.drop_table("sys_agent_conversation")
