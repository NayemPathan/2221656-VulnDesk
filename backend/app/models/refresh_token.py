"""
Refresh Token Database Model (backend/app/models/refresh_token.py)
=====================================================================
WHAT THIS FILE DOES:
Defines the `refresh_token` table for 7-day rotating refresh tokens,
supporting logout revocation, reuse detection, and admin ban invalidation.
=====================================================================
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """Return the current UTC timestamp (timezone-aware)."""
    return datetime.now(UTC)


class RefreshToken(SQLModel, table=True):
    """Stores hashed 7-day refresh tokens linked to a User."""

    __tablename__ = "refresh_token"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(
        foreign_key="user.id", index=True, nullable=False, ondelete="CASCADE"
    )
    token_hash: str = Field(max_length=64, unique=True, index=True, nullable=False)
    expires_at: datetime = Field(nullable=False)
    revoked_at: datetime | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)