"""Add indexes for analytics and response listing.

Revision ID: 20260515_0004
Revises: 20260515_0003
Create Date: 2026-05-15
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260515_0004"
down_revision: Union[str, None] = "20260515_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_responses_question_id"), "responses", ["question_id"], unique=False)
    op.create_index(op.f("ix_responses_submitted_at"), "responses", ["submitted_at"], unique=False)
    op.create_index(
        op.f("ix_response_sessions_submitted_at"),
        "response_sessions",
        ["submitted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_response_sessions_submitted_at"), table_name="response_sessions")
    op.drop_index(op.f("ix_responses_submitted_at"), table_name="responses")
    op.drop_index(op.f("ix_responses_question_id"), table_name="responses")
