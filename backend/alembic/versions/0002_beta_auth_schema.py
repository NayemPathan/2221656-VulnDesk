"""
Beta Auth Schema Migration (0002_beta_auth_schema.py)
=====================================================================
WHAT THIS FILE DOES:
1. Adds `password_hash`, `failed_login_attempts`, `locked_until`, and `updated_at`
   to the `user` table.
2. Creates the `refresh_token` table with a unique index on `token_hash` and
   cascading delete on `user_id`.

Revision ID: 0002_beta_auth
Revises: 0001_initial_mvp
Create Date: 2026-11-16 00:00:00
=====================================================================
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_beta_auth"
down_revision: str | None = "0001_initial_mvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply Beta auth schema changes."""
    # 1. Add authentication and lockout columns to `user`
    op.add_column("user", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column(
        "user",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("user", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "user",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # 2. Create `refresh_token` table
    op.create_table(
        "refresh_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_token_user_id"), "refresh_token", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_refresh_token_token_hash"), "refresh_token", ["token_hash"], unique=True
    )


def downgrade() -> None:
    """Revert Beta auth schema changes."""
    op.drop_index(op.f("ix_refresh_token_token_hash"), table_name="refresh_token")
    op.drop_index(op.f("ix_refresh_token_user_id"), table_name="refresh_token")
    op.drop_table("refresh_token")

    op.drop_column("user", "updated_at")
    op.drop_column("user", "locked_until")
    op.drop_column("user", "failed_login_attempts")
    op.drop_column("user", "password_hash")