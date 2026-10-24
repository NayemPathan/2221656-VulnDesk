"""
User Database Model (backend/app/models/user.py)
=====================================================================
WHAT THIS FILE DOES:
Defines the ` user ` table in PostgreSQL/SQLite using SQLModel.

WHY WE WROTE IT THIS WAY (TDD Section 4 & SRS FR-08):
1. `table=True`: Tells SQLModel that this class maps to an actual database table (not just a JSON schema).
2. `email` has `unique=True, index=True`: Guarantees no two accounts can share an email address
   and makes looking up a user by email (`X-Demo-User` or login) fast via a B-tree index.
3. Why are `is_banned` and `is_deleted` included in Phase 1 (MVP)?
   - Submission Policy Rule (iv) (FR-08) requires checking that the researcher's account is active
     (not banned) when submitting a report in the MVP.
   - Soft Delete (FR-05 & TDD Section 4): When an admin deletes a user, we set `is_deleted=True`
     instead of removing the row so historical vulnerability reports and audit trails never lose their author!
=====================================================================
"""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from app.models.enums import UserRole


def utc_now() -> datetime:
    """Return the current UTC timestamp (timezone-aware) so researchers across time zones stay synced."""
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """Represents a registered Researcher, Security Analyst, or Administrator."""

    # Explicitly name the table "user" to match the ERD in TDD Section 4
    __tablename__ = "user"

    # Primary Key: `Optional[int] = None` in Python because the database auto-generates the ID on INSERT
    id: int | None = Field(default=None, primary_key=True)

    # Display name of the user (SRS Section 7: 1 to 80 characters)
    name: str = Field(max_length=80, nullable=False)

    # Unique email address (SRS Section 7: max 254 chars, indexed for fast lookup)
    email: str = Field(max_length=254, unique=True, index=True, nullable=False)

    # User's global role: 'researcher', 'analyst', or 'admin'
    role: str = Field(default=UserRole.RESEARCHER.value, max_length=20, nullable=False)

    # Submission Policy Rule (iv) & FR-05: Banned users cannot submit reports or use the API
    is_banned: bool = Field(default=False, nullable=False)

    # Soft-delete flag (TDD Section 4): Preserves foreign key integrity for reports/comments/history
    is_deleted: bool = Field(default=False, nullable=False)

    # Timestamp when the user account was created (always stored in UTC)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
