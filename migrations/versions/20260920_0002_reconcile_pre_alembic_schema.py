"""Reconcile databases created before the Alembic baseline.

Revision ID: 20260920_0002
Revises: 20260920_0001
Create Date: 2026-09-20

P0 created tables directly with ``Base.metadata.create_all``. When Alembic was
introduced in P1, the baseline migration also used ``create_all``. That is safe
for a fresh database, but ``create_all`` never alters an existing table. A local
P0 database could therefore be marked at the P1 Alembic revision while still
missing columns added to existing P0 tables.

This migration is intentionally idempotent: it creates any P1 tables that are
missing, then adds the known columns introduced on tables that already existed
in P0. It supports both SQLite development databases and the intended MySQL 8
runtime.
"""

from alembic import op
import sqlalchemy as sa

from backend.app.db.application_models import AuditLog, SearchHistory  # noqa: F401
from backend.app.db.models import Base

revision = "20260920_0002"
down_revision = "20260920_0001"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _column_names(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()

    # P0 databases do not contain the P1-only tables. create_all creates only
    # missing tables and leaves existing tables/data untouched.
    Base.metadata.create_all(bind=bind)

    # biz_metric existed in P0 and gained these columns in P1.
    _add_column_if_missing("biz_metric", sa.Column("stat_system_code", sa.String(length=64), nullable=True))
    _add_column_if_missing(
        "biz_metric",
        sa.Column(
            "time_additivity",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'ADDITIVE'"),
        ),
    )
    _add_column_if_missing("biz_metric", sa.Column("valid_dimensions", sa.String(length=500), nullable=True))

    # std_code_table also existed in P0 and gained richer standard metadata.
    _add_column_if_missing("std_code_table", sa.Column("en_name", sa.String(length=128), nullable=True))
    _add_column_if_missing("std_code_table", sa.Column("category_code", sa.String(length=64), nullable=True))
    _add_column_if_missing("std_code_table", sa.Column("source_standard", sa.String(length=32), nullable=True))
    _add_column_if_missing("std_code_table", sa.Column("version", sa.String(length=32), nullable=True))
    _add_column_if_missing("std_code_table", sa.Column("owner", sa.String(length=64), nullable=True))


def downgrade() -> None:
    # This compatibility migration is deliberately non-destructive on downgrade.
    # Removing these columns would discard data and is not required for the local
    # development upgrade path it repairs.
    pass
