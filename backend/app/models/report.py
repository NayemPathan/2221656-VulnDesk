"""
Vulnerability Report Database Model (backend/app/models/report.py)
=====================================================================
WHAT THIS FILE DOES:
Defines the `report` table — the central entity of VulnDesk where vulnerability submissions,
triage severities, workflow statuses, rejection reasons, and duplicate links are stored.

WHY WE WROTE IT THIS WAY (SRS Section 4, 5, 7 & TDD Section 4):
1. Two Severity Columns (`proposed_severity` vs `final_severity`):
   - When a researcher submits a report (FR-07), they suggest `proposed_severity` (`low`..`critical`).
   - `final_severity` starts as `None` (NULL) because only a Security Analyst can assign the official
     severity during triage (FR-12), and a report cannot move to `Confirmed` until `final_severity` is set (FR-14).
2. `rejection_reason` Column:
   - Stores the analyst's explanation when a report is moved to `Rejected` so the researcher can see
     why their submission was rejected, and allows counting invalid rejections per month (FR-08 rule v).
3. Self-Referencing Foreign Key (`duplicate_of_id -> report.id`):
   - When an analyst marks a report as `Duplicate` (FR-14), it must point to the original `report.id`
     that already reported the same bug.
4. `first_responder_id` & `first_response_at`:
   - Automatically recorded the very first time an analyst moves a report out of `New`. Used in Beta
     to calculate average response time and analyst deadline compliance (TDD Section 4 & 7).
=====================================================================
"""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from app.models.enums import ReportStatus


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class Report(SQLModel, table=True):
    """Represents a single vulnerability report submitted by a researcher."""

    __tablename__ = "report"

    # Auto-incrementing primary key
    id: int | None = Field(default=None, primary_key=True)

    # Core submission fields provided by the Researcher (validated by SRS Section 7 rules)
    title: str = Field(max_length=120, nullable=False)               # Policy Rule (i): 5 to 120 chars
    description: str = Field(max_length=5000, nullable=False)        # Policy Rule (ii): 50 to 5,000 chars
    component: str = Field(max_length=100, nullable=False)           # Affected product/module (1 to 100 chars)
    steps_to_reproduce: str = Field(max_length=5000, nullable=False) # Repro steps (10 to 5,000 chars)

    # Severity fields: Researcher proposes one; Analyst assigns final_severity during triage
    proposed_severity: str = Field(max_length=20, nullable=False)
    final_severity: str | None = Field(default=None, max_length=20, nullable=True)

    # Current workflow status (indexed because analysts frequently filter by status)
    status: str = Field(default=ReportStatus.NEW.value, max_length=20, index=True, nullable=False)

    # Analyst's explanation when a report is rejected (visible to the Researcher on Report Detail)
    rejection_reason: str | None = Field(default=None, max_length=1000, nullable=True)

    # Foreign Key to the Researcher who submitted this report (indexed for fast 'My Reports' queries)
    reporter_id: int = Field(foreign_key="user.id", index=True, nullable=False)

    # Self-referencing Foreign Key: if status == 'duplicate', points to the original Report ID (FR-14)
    duplicate_of_id: int | None = Field(default=None, foreign_key="report.id", nullable=True)

    # Tracks which Analyst first triaged the report and when (for SLA / deadline metrics)
    first_responder_id: int | None = Field(default=None, foreign_key="user.id", nullable=True)
    first_response_at: datetime | None = Field(default=None, nullable=True)

    # Audit timestamps
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
