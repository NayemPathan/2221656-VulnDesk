"""
Append-Only Status History Database Model (backend/app/models/status_history.py)
=====================================================================
WHAT THIS FILE DOES:
Defines the `status_history` table, which records an immutable audit trail every time a report's
status changes (e.g., from `new` -> `under_review`).

WHY WE WROTE IT THIS WAY (SRS FR-15 & NFR-08):
1. Traceability (Goal G2): In the problem statement, management complained that when a fix was delayed,
   nobody could prove who changed a report's status or when.
2. Append-Only Integrity (NFR-08): Whenever an Analyst changes `report.status`, our service layer inserts
   a new `StatusHistory` row in the **exact same database transaction**. We deliberately provide NO
   update (`PUT`/`PATCH`) or delete (`DELETE`) endpoint for `status_history`, so this audit trail
   can never be tampered with by any role.
=====================================================================
"""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class StatusHistory(SQLModel, table=True):
    """Immutable audit record of a single status transition on a vulnerability report."""

    __tablename__ = "status_history"

    # Auto-incrementing primary key
    id: int | None = Field(default=None, primary_key=True)

    # Which report changed status (indexed so GET /reports/{id}/history is fast)
    report_id: int = Field(foreign_key="report.id", index=True, nullable=False)

    # Which user (Analyst or Admin) performed the status transition
    changed_by: int = Field(foreign_key="user.id", nullable=False)

    # The previous status (e.g., 'new') and the new status (e.g., 'under_review')
    from_status: str = Field(max_length=20, nullable=False)
    to_status: str = Field(max_length=20, nullable=False)

    # Exact UTC timestamp when the transition occurred
    changed_at: datetime = Field(default_factory=utc_now, nullable=False)
