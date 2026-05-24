"""Microsoft Forms import: ms_forms_id, help_text, number type, branch rules.

Revision ID: 20260516_0005
Revises: 20260515_0004
Create Date: 2026-05-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260516_0005"
down_revision: Union[str, None] = "20260515_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("ms_forms_id", sa.String(64), nullable=True))
    op.add_column("questions", sa.Column("help_text", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("global_order", sa.Integer(), nullable=True))
    op.create_index("ix_questions_ms_forms_id", "questions", ["ms_forms_id"], unique=True)

    op.create_table(
        "question_branch_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_question_id", sa.Integer(), nullable=False),
        sa.Column("option_value", sa.Text(), nullable=False),
        sa.Column("target_ms_forms_id", sa.String(64), nullable=False),
        sa.Column("target_question_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_question_id"],
            ["questions.id"],
            ondelete="CASCADE",
            name=op.f("fk_question_branch_rules_source_question_id_questions"),
        ),
        sa.ForeignKeyConstraint(
            ["target_question_id"],
            ["questions.id"],
            ondelete="SET NULL",
            name=op.f("fk_question_branch_rules_target_question_id_questions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_branch_rules")),
    )
    op.create_index(
        "ix_question_branch_rules_source_question_id",
        "question_branch_rules",
        ["source_question_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_question_branch_rules_source_question_id", table_name="question_branch_rules")
    op.drop_table("question_branch_rules")
    op.drop_index("ix_questions_ms_forms_id", table_name="questions")
    op.drop_column("questions", "global_order")
    op.drop_column("questions", "help_text")
    op.drop_column("questions", "ms_forms_id")
