"""Allow duplicate respondent_name (multiple submissions per name).

Revision ID: 20260517_0007
Revises: 20260517_0006
Create Date: 2026-05-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260517_0007"
down_revision: Union[str, None] = "20260517_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_response_sessions_respondent_name_active", table_name="response_sessions")
    op.create_index(
        op.f("ix_response_sessions_respondent_name"),
        "response_sessions",
        ["respondent_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_response_sessions_respondent_name"), table_name="response_sessions")
    op.create_index(
        "ix_response_sessions_respondent_name_active",
        "response_sessions",
        ["respondent_name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
