"""Rename respondent_email to respondent_name.

Revision ID: 20260515_0003
Revises: 20260514_0002
Create Date: 2026-05-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260515_0003"
down_revision: Union[str, None] = "20260514_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_response_sessions_respondent_email"), table_name="response_sessions")
    op.alter_column(
        "response_sessions",
        "respondent_email",
        new_column_name="respondent_name",
        existing_type=sa.String(length=320),
        existing_nullable=True,
    )
    op.create_index(
        op.f("ix_response_sessions_respondent_name"),
        "response_sessions",
        ["respondent_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_response_sessions_respondent_name"), table_name="response_sessions")
    op.alter_column(
        "response_sessions",
        "respondent_name",
        new_column_name="respondent_email",
        existing_type=sa.String(length=320),
        existing_nullable=True,
    )
    op.create_index(
        op.f("ix_response_sessions_respondent_email"),
        "response_sessions",
        ["respondent_email"],
        unique=True,
    )
