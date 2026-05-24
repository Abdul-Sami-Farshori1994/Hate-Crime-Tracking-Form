"""Soft-delete response sessions (deleted_at, deleted_by_id).

Revision ID: 20260517_0006
Revises: 20260516_0005
Create Date: 2026-05-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260517_0006"
down_revision: Union[str, None] = "20260516_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "response_sessions",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "response_sessions",
        sa.Column("deleted_by_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_response_sessions_deleted_by_id_users",
        "response_sessions",
        "users",
        ["deleted_by_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_response_sessions_deleted_at"),
        "response_sessions",
        ["deleted_at"],
        unique=False,
    )

    op.drop_index(op.f("ix_response_sessions_respondent_name"), table_name="response_sessions")
    op.create_index(
        "ix_response_sessions_respondent_name_active",
        "response_sessions",
        ["respondent_name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_response_sessions_respondent_name_active", table_name="response_sessions")
    op.create_index(
        op.f("ix_response_sessions_respondent_name"),
        "response_sessions",
        ["respondent_name"],
        unique=True,
    )
    op.drop_index(op.f("ix_response_sessions_deleted_at"), table_name="response_sessions")
    op.drop_constraint("fk_response_sessions_deleted_by_id_users", "response_sessions", type_="foreignkey")
    op.drop_column("response_sessions", "deleted_by_id")
    op.drop_column("response_sessions", "deleted_at")
