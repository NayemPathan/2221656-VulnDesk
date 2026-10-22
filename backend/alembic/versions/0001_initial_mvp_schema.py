"""
Initial VulnDesk MVP Schema Migration (0001_initial_mvp_schema.py)
=====================================================================
WHAT THIS FILE DOES:
Defines the exact `upgrade()` and `downgrade()` steps to create (or drop) our four MVP tables:
1. `user`
2. `report`
3. `comment`
4. `status_history`

WHY WE WROTE IT THIS WAY (TDD Section 11):
- Creation Order Matters: `user` is created first because `report`, `comment`, and `status_history`
  all have Foreign Keys pointing to `user.id`. Next, `report` is created because `comment` and
  `status_history` have Foreign Keys pointing to `report.id`.
- `ondelete="CASCADE"` on `comment.report_id` and `status_history.report_id`:
  When a Researcher deletes their own `New` report (`DELETE /api/v1/reports/{id}` for CSE 309 CRUD),
  the database automatically cleans up any child rows referencing that report without raising a
  ForeignKeyViolation error!
- Drop Order in `downgrade()`: Tables are dropped in the exact reverse order (`status_history` ->
  `comment` -> `report` -> `user`) so foreign key constraints are respected when rolling back.
=====================================================================

Revision ID: 0001_initial_mvp
Revises: None
Create Date: 2026-10-22 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Unique identifier for this migration version
revision: str = "0001_initial_mvp"
# None because this is the very first migration in the project
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration: create user, report, comment, and status_history tables."""

    # 1. Create the `user` table first (referenced by all other tables)
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Unique index on user.email so no two accounts can register with the same email
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    # 2. Create the `report` table (references user.id and self-references report.id for duplicates)
    op.create_table(
        "report",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=5000), nullable=False),
        sa.Column("component", sa.String(length=100), nullable=False),
        sa.Column("steps_to_reproduce", sa.String(length=5000), nullable=False),
        sa.Column("proposed_severity", sa.String(length=20), nullable=False),
        sa.Column("final_severity", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rejection_reason", sa.String(length=1000), nullable=True),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("duplicate_of_id", sa.Integer(), nullable=True),
        sa.Column("first_responder_id", sa.Integer(), nullable=True),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["duplicate_of_id"], ["report.id"]),
        sa.ForeignKeyConstraint(["first_responder_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["reporter_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # Indexes to speed up filtering by reporter_id (Researcher's own reports) and status (Analyst triage queue)
    op.create_index(op.f("ix_report_reporter_id"), "report", ["reporter_id"], unique=False)
    op.create_index(op.f("ix_report_status"), "report", ["status"], unique=False)

    # 3. Create the `comment` table (references report.id and user.id)
    op.create_table(
        "comment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(length=2000), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["report.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_comment_report_id"), "comment", ["report_id"], unique=False)

    # 4. Create the `status_history` table (append-only audit log referencing report.id and user.id)
    op.create_table(
        "status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("changed_by", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=False),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["changed_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["report.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_status_history_report_id"), "status_history", ["report_id"], unique=False
    )


def downgrade() -> None:
    """Revert the migration: drop tables in reverse dependency order."""
    op.drop_index(op.f("ix_status_history_report_id"), table_name="status_history")
    op.drop_table("status_history")
    op.drop_index(op.f("ix_comment_report_id"), table_name="comment")
    op.drop_table("comment")
    op.drop_index(op.f("ix_report_status"), table_name="report")
    op.drop_index(op.f("ix_report_reporter_id"), table_name="report")
    op.drop_table("report")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
