"""P1 baseline schema.

Revision ID: 20260920_0001
Revises:
Create Date: 2026-09-20
"""

from alembic import op

from backend.app.db.application_models import AuditLog, SearchHistory  # noqa: F401
from backend.app.db.models import Base

revision = "20260920_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
