"""Add response_sessions for one-email-one-submission flow.

Revision ID: 20260514_0002
Revises: 20260112_0001
Create Date: 2026-05-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260514_0002"
down_revision: Union[str, None] = "20260112_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "response_sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("respondent_email", sa.String(length=320), nullable=True),
        sa.Column("submitted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["submitted_by_user_id"],
            ["users.id"],
            name=op.f("fk_response_sessions_submitted_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(
        op.f("ix_response_sessions_respondent_email"),
        "response_sessions",
        ["respondent_email"],
        unique=True,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO response_sessions (session_id, respondent_email, submitted_by_user_id, submitted_at)
            SELECT session_id, NULL, NULL, max(submitted_at)
            FROM responses
            GROUP BY session_id
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_response_sessions_respondent_email"), table_name="response_sessions")
    op.drop_table("response_sessions")
