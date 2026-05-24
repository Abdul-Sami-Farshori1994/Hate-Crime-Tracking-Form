"""Soft-delete form pages and questions (deleted_at, deleted_by_id).

Revision ID: 20260525_0011
Revises: 20260524_0010
Create Date: 2026-05-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260525_0011"
down_revision: Union[str, None] = "20260524_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("form_pages", "questions"):
        op.add_column(
            table,
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("deleted_by_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            f"fk_{table}_deleted_by_id_users",
            table,
            "users",
            ["deleted_by_id"],
            ["id"],
        )
        op.create_index(
            op.f(f"ix_{table}_deleted_at"),
            table,
            ["deleted_at"],
            unique=False,
        )

    op.drop_index("ix_questions_ms_forms_id", table_name="questions")
    op.create_index(
        "ix_questions_ms_forms_id_active",
        "questions",
        ["ms_forms_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND ms_forms_id IS NOT NULL"),
        sqlite_where=sa.text("deleted_at IS NULL AND ms_forms_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_questions_ms_forms_id_active", table_name="questions")
    op.create_index("ix_questions_ms_forms_id", "questions", ["ms_forms_id"], unique=True)

    for table in ("questions", "form_pages"):
        op.drop_index(op.f(f"ix_{table}_deleted_at"), table_name=table)
        op.drop_constraint(f"fk_{table}_deleted_by_id_users", table, type_="foreignkey")
        op.drop_column(table, "deleted_by_id")
        op.drop_column(table, "deleted_at")
