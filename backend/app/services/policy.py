"""
Submission Policy Service (backend/app/services/policy.py)
=====================================================================
WHAT THIS FILE DOES:
Enforces the 5-rule Report Submission Policy required by SRS FR-08 and Project Definition Section 4.

THE 5 SUBMISSION POLICY RULES (FR-08):
A report submission is accepted ONLY if all 5 conditions hold:
  (i)   The title has between 5 and 120 characters.
  (ii)  The description has between 50 and 5,000 characters.
  (iii) The researcher currently has fewer than 5 open reports (status `new` or `under_review`).
  (iv)  The researcher's account is active (not banned and not deleted).
  (v)   The researcher has fewer than 3 reports rejected as invalid in the current calendar month.

WHY WE WROTE IT THIS WAY:
1. Pure Service Function (`validate_submission_policy`):
   By raising a custom `PolicyViolationError(reason)` in the service layer (which the router or
   service translates to HTTP `409 Conflict`), we can unit-test all 5 rules directly in Python
   AND test them through the HTTP API!
2. Specific Failure Reasons (FR-08 & AC-02):
   Each rule returns a clear, human-readable message explaining *which* rule failed (e.g.,
   `"open report limit reached"` for AC-02) so the researcher knows why their submission was refused.
=====================================================================
"""

from datetime import datetime, timezone

from sqlalchemy import column, func
from sqlmodel import Session, select

from app.models import Report, ReportStatus, User

# Constants defining policy thresholds so they are easy to read and explain in Viva
MIN_TITLE_LEN = 5
MAX_TITLE_LEN = 120
MIN_DESCRIPTION_LEN = 50
MAX_DESCRIPTION_LEN = 5000
MAX_OPEN_REPORTS = 5
MAX_MONTHLY_REJECTIONS = 3


class PolicyViolationError(ValueError):
    """
    Raised when a report submission violates one of the 5 business rules in FR-08.
    Mapped to HTTP 409 Conflict by the API layer (SRS Section 7).
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _current_month_utc_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """
    Calculate the start of the current UTC calendar month and the start of the next month.
    Used by Rule (v) to count how many reports were rejected in the current calendar month.
    """
    current = now or datetime.now(timezone.utc)
    month_start = datetime(current.year, current.month, 1, tzinfo=timezone.utc)
    if current.month == 12:
        next_month_start = datetime(current.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month_start = datetime(current.year, current.month + 1, 1, tzinfo=timezone.utc)
    return month_start, next_month_start


def validate_submission_policy(
    session: Session,
    researcher: User,
    title: str,
    description: str,
    now: datetime | None = None,
) -> None:
    """
    Check all 5 submission policy rules (FR-08).
    Raises `PolicyViolationError` with the specific reason if any rule fails.
    """
    clean_title = title.strip()
    clean_description = description.strip()

    # -----------------------------------------------------------------
    # Rule (i): Title length must be between 5 and 120 characters
    # -----------------------------------------------------------------
    if not (MIN_TITLE_LEN <= len(clean_title) <= MAX_TITLE_LEN):
        raise PolicyViolationError(
            f"Submission rejected: title must be between {MIN_TITLE_LEN} and {MAX_TITLE_LEN} characters."
        )

    # -----------------------------------------------------------------
    # Rule (ii): Description length must be between 50 and 5,000 characters
    # -----------------------------------------------------------------
    if not (MIN_DESCRIPTION_LEN <= len(clean_description) <= MAX_DESCRIPTION_LEN):
        raise PolicyViolationError(
            f"Submission rejected: description must be between {MIN_DESCRIPTION_LEN} and {MAX_DESCRIPTION_LEN} characters."
        )

    # -----------------------------------------------------------------
    # Rule (iv): Researcher account must be active (not banned or deleted)
    # (Checked before DB queries so banned users are rejected immediately)
    # -----------------------------------------------------------------
    if researcher.is_banned or researcher.is_deleted:
        raise PolicyViolationError(
            "Submission rejected: researcher account is banned or inactive."
        )

    # -----------------------------------------------------------------
    # Rule (iii): Researcher must have fewer than 5 open reports
    # Open statuses are defined in FR-08 as `New` or `Under Review`.
    # -----------------------------------------------------------------
    open_statuses = [ReportStatus.NEW.value, ReportStatus.UNDER_REVIEW.value]
    open_count_stmt = (
        select(func.count())
        .select_from(Report)
        .where(
            Report.reporter_id == researcher.id,
            column("status").in_(open_statuses),
        )
    )
    open_reports_count = session.exec(open_count_stmt).one()

    if open_reports_count >= MAX_OPEN_REPORTS:
        # AC-02 requires the reason to include "open report limit reached"
        raise PolicyViolationError(
            f"Submission rejected: open report limit reached ({MAX_OPEN_REPORTS} open reports maximum)."
        )

    # -----------------------------------------------------------------
    # Rule (v): Fewer than 3 reports rejected as invalid in current calendar month
    # -----------------------------------------------------------------
    month_start, next_month_start = _current_month_utc_bounds(now)
    # For SQLite compatibility (which stores naive datetimes), compare using both naive/aware bounds
    month_start_naive = month_start.replace(tzinfo=None)
    next_month_naive = next_month_start.replace(tzinfo=None)

    rejected_stmt = select(Report).where(
        Report.reporter_id == researcher.id,
        Report.status == ReportStatus.REJECTED.value,
    )
    rejected_reports = session.exec(rejected_stmt).all()

    rejected_this_month = 0
    for rep in rejected_reports:
        ts = rep.updated_at or rep.created_at
        ts_naive = ts.replace(tzinfo=None) if ts.tzinfo is not None else ts
        if month_start_naive <= ts_naive < next_month_naive:
            rejected_this_month += 1

    if rejected_this_month >= MAX_MONTHLY_REJECTIONS:
        raise PolicyViolationError(
            f"Submission rejected: monthly rejection limit reached ({MAX_MONTHLY_REJECTIONS} rejected reports in current month)."
        )