"""Initial Microsoft-Forms-style schema + seed users/pages/questions.

Revision ID: 20260112_0001
Revises:
Create Date: 2026-01-12

Alembic migration hints: when you change models.py (new columns/tables), add a new
revision with `alembic revision --autogenerate -m "describe change"` (or hand-edit),
then `alembic upgrade head`.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260112_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS responses CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS admin_credentials CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS questions CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS form_pages CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS users CASCADE"))

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], name=op.f("fk_users_created_by_id_users")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "form_pages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=False),
        sa.Column("options", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["form_pages.id"], ondelete="CASCADE", name=op.f("fk_questions_page_id_form_pages")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "responses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("answer_value", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE", name=op.f("fk_responses_question_id_questions")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_responses_session_id"), "responses", ["session_id"], unique=False)

    op.create_table(
        "admin_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("secret_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], name=op.f("fk_admin_credentials_created_by_id_users")),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed shared accounts (change passwords in production).
    admin_hash = "$2b$12$OzI5c337ccXVIzWRmTY2Ye.HVrITDuaaOzmiULXLEzYki0ygYaDs2"  # password: admin
    user_hash = "$2b$12$roiLekMLWsYtTydNWov2.O0JBMH7BlfZkDVLTv9.LRqWOIWkzya.S"  # password: user
    op.execute(
        sa.text(
            """
            INSERT INTO users (username, password_hash, role, is_active, created_by_id)
            VALUES
              ('admin', :admin_hash, 'admin', true, NULL),
              ('user', :user_hash, 'user', true, NULL)
            """
        ).bindparams(admin_hash=admin_hash, user_hash=user_hash)
    )

    op.execute(
        sa.text(
            """
            INSERT INTO form_pages (title, description, order_index) VALUES
              ('Page 1 — About the incident', 'Tell us what happened.', 0),
              ('Page 2 — Details', 'Additional information.', 1)
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO questions (page_id, question_text, question_type, options, is_required, order_index) VALUES
              (1, 'Short description', 'text', NULL, true, 0),
              (1, 'Incident date', 'date', NULL, true, 1),
              (2, 'Was bias motivation present?', 'radio', '["Yes","No","Unsure"]'::jsonb, true, 0),
              (2, 'Type of incident (select all that apply)', 'checkbox', '["Harassment","Vandalism","Assault","Other"]'::jsonb, false, 1),
              (2, 'Severity (1–5)', 'rating', NULL, false, 2),
              (2, 'Police report filed?', 'select', '["Yes","No"]'::jsonb, false, 3)
            """
        )
    )


def downgrade() -> None:
    op.drop_table("admin_credentials")
    op.drop_index(op.f("ix_responses_session_id"), table_name="responses")
    op.drop_table("responses")
    op.drop_table("questions")
    op.drop_table("form_pages")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
