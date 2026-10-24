"""
Comment & Internal Note Database Model (backend/app/models/comment.py)
=====================================================================
WHAT THIS FILE DOES:
Defines the `comment` table, which stores both public comments (between the Researcher and Analysts)
and private Analyst-only internal notes on a vulnerability report.

WHY WE WROTE IT THIS WAY (SRS FR-18, FR-19, FR-20):
1. Single Table with `is_internal` Boolean Flag:
   - Instead of creating two separate tables for public comments and internal notes, we use a single
     `comment` table with `is_internal: bool`.
   - When `is_internal == False`, both the report's Researcher and all Analysts can read it.
   - When `is_internal == True` (only Analysts are allowed to set this), our service layer filters
     these rows out whenever a Researcher fetches `GET /api/v1/reports/{id}/comments` (AC-09)!
=====================================================================
"""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class Comment(SQLModel, table=True):
    """Represents a comment or analyst-only internal note on a vulnerability report."""

    __tablename__ = "comment"

    # Auto-incrementing primary key
    id: int | None = Field(default=None, primary_key=True)

    # Foreign Key linking this comment to its parent Report (indexed for fast lookup by report_id)
    report_id: int = Field(foreign_key="report.id", index=True, nullable=False)

    # Foreign Key linking this comment to the User (Researcher or Analyst) who wrote it
    author_id: int = Field(foreign_key="user.id", nullable=False)

    # Comment text (SRS Section 7: 1 to 2,000 characters)
    body: str = Field(max_length=2000, nullable=False)

    # FR-19 & FR-20: True = Private internal analyst note (hidden from Researchers); False = Public comment
    is_internal: bool = Field(default=False, nullable=False)

    # Creation timestamp (comments are ordered oldest-first by created_at per FR-20)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
