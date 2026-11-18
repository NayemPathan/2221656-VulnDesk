"""
User Database Model (backend/app/models/user.py)
=====================================================================
WHAT THIS FILE DOES:
Defines the `user` table in PostgreSQL/SQLite using SQLModel, including Beta
authentication and brute-force lockout fields.
=====================================================================
"""

from datetime import UTC, datetime

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import UserRole
from app.models.refresh_token import RefreshToken


def utc_now() -> datetime:
    """Return the current UTC timestamp (timezone-aware)."""
    return datetime.now(UTC)


class User(SQLModel, table=True):
    """Represents a registered Researcher, Security Analyst, or Administrator."""

    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=80, nullable=False)
    email: str = Field(max_length=254, unique=True, index=True, nullable=False)
    role: str = Field(default=UserRole.RESEARCHER.value, max_length=20, nullable=False)

    # Beta Auth & Lockout fields (Migration 0002)
    password_hash: str | None = Field(default=None, max_length=255, nullable=True)
    failed_login_attempts: int = Field(default=0, nullable=False)
    locked_until: datetime | None = Field(default=None, nullable=True)

    # Account status flags
    is_banned: bool = Field(default=False, nullable=False)
    is_deleted: bool = Field(default=False, nullable=False)

    # Audit timestamps
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)

    refresh_tokens: list[RefreshToken] = Relationship(cascade_delete=True)
