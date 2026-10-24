"""
Report CRUD Service (backend/app/services/report_service.py)
=====================================================================
WHAT THIS FILE DOES:
Implements all business logic for creating, listing, filtering, viewing, updating, and deleting
vulnerability reports in the service layer.

WHY WE WROTE IT THIS WAY:
1. Ownership Isolation (`FR-09`, `AC-04`):
   - A Researcher can only list and view their own reports (`Report.reporter_id == user.id`).
   - If Researcher Alice requests Researcher Bob's report ID (`GET /reports/4`), we return HTTP
     `404 Not Found` (NOT `403 Forbidden`) so Alice cannot even tell whether Report #4 exists!
2. State-Gated Edit & Delete (`FR-10a`, `FR-10b`, `AC-05`, `AC-06`, `AC-07`):
   - A Researcher can edit (`PUT`) or delete (`DELETE`) their own report ONLY while `report.status == "new"`.
   - Once an Analyst moves the report to `under_review`, `confirmed`, `rejected`, etc., any attempt
     by the Researcher to edit or delete it raises HTTP `409 Conflict`.
3. Flexible Filtering & Pagination (`FR-11`):
   - Analysts and Admins can filter by `status`, `severity` (matching `final_severity` if set, otherwise
     `proposed_severity`), `component`, `keyword` (in title), and ISO date range (`date_from`, `date_to`).
=====================================================================
"""

import math
from datetime import datetime, timezone
from typing import cast

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, select

from app.models import (
    Comment,
    Report,
    ReportStatus,
    StatusHistory,
    User,
    UserRole,
)
from app.schemas.report import (
    ReportCreate,
    ReportListResponse,
    ReportRead,
    ReportUpdate,
)
from app.services.policy import PolicyViolationError, validate_submission_policy


def list_demo_users(session: Session) -> list[User]:
    """Return all active (non-deleted) seeded users for the MVP Demo User Switcher."""
    statement = (
        select(User)
        .where(User.is_deleted == False)
        .order_by(func.coalesce(User.id, 0))
    )
    return list(session.exec(statement).all())


def create_report(session: Session, current_user: User, data: ReportCreate) -> Report:
    """
    Validate the 5-rule submission policy and create a new vulnerability report with status `New` (FR-07, FR-08).
    """
    # Only researchers are allowed to submit vulnerability reports (SRS Section 8 Permission Matrix)
    if current_user.role != UserRole.RESEARCHER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only researchers can submit vulnerability reports.",
        )

    # Check all 5 business rules in policy.py; convert PolicyViolationError into HTTP 409 Conflict
    try:
        validate_submission_policy(
            session=session,
            researcher=current_user,
            title=data.title,
            description=data.description,
        )
    except PolicyViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.reason,
        ) from exc

    reporter_id = current_user.id
    if reporter_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user is missing an ID.",
        )

    now = datetime.now(timezone.utc)
    report = Report(
        title=data.title,
        description=data.description,
        component=data.component,
        steps_to_reproduce=data.steps_to_reproduce,
        proposed_severity=data.proposed_severity.value,
        final_severity=None,
        status=ReportStatus.NEW.value,
        rejection_reason=None,
        reporter_id=reporter_id,
        created_at=now,
        updated_at=now,
    )

    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def list_reports(
    session: Session,
    current_user: User,
    status_filter: str | None = None,
    severity_filter: str | None = None,
    component_filter: str | None = None,
    keyword: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> ReportListResponse:
    """
    List vulnerability reports with role-based visibility, filtering, and pagination (FR-09, FR-11).
    - Researchers see only their own reports.
    - Analysts and Admins see all reports.
    """
    conditions = []

    # FR-09 Ownership Isolation: Researchers can only list their own reports
    if current_user.role == UserRole.RESEARCHER.value:
        conditions.append(Report.reporter_id == current_user.id)

    # Optional Filter 1: Status (e.g. 'new', 'under_review', 'confirmed')
    if status_filter:
        conditions.append(Report.status == status_filter.strip().lower())

    # Optional Filter 2: Severity (matches effective severity: final_severity if set, else proposed_severity)
    if severity_filter:
        sev = severity_filter.strip().lower()
        final_severity_condition = cast(ColumnElement[bool], Report.final_severity == sev)
        fallback_severity_condition = cast(
            ColumnElement[bool],
            (Report.final_severity == None) & (Report.proposed_severity == sev),
        )
        conditions.append(or_(final_severity_condition, fallback_severity_condition))

    # Optional Filter 3: Affected Component (case-insensitive substring match)
    if component_filter and component_filter.strip():
        comp_pattern = f"%{component_filter.strip().lower()}%"
        conditions.append(func.lower(Report.component).like(comp_pattern))

    # Optional Filter 4: Title Keyword Search (case-insensitive substring match)
    if keyword and keyword.strip():
        kw_pattern = f"%{keyword.strip().lower()}%"
        conditions.append(func.lower(Report.title).like(kw_pattern))

    # Optional Filter 5 & 6: Created Date Range
    if date_from is not None:
        conditions.append(Report.created_at >= date_from)
    if date_to is not None:
        conditions.append(Report.created_at <= date_to)

    # Count total matching rows for pagination metadata
    count_stmt = select(func.count()).select_from(Report)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = session.exec(count_stmt).one()

    # Fetch the requested page ordered newest-first
    offset = (page - 1) * page_size
    query_stmt = select(Report)
    if conditions:
        query_stmt = query_stmt.where(*conditions)
    query_stmt = (
        query_stmt.order_by(
            cast(ColumnElement[datetime], Report.created_at).desc(),
            cast(ColumnElement[int], Report.id).desc(),
        )
        .offset(offset)
        .limit(page_size)
    )

    reports = session.exec(query_stmt).all()
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

    return ReportListResponse(
        items=[ReportRead.model_validate(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_report_for_user(session: Session, current_user: User, report_id: int) -> Report:
    """
    Fetch a single report by ID and enforce ownership rules (FR-09, AC-04).
    Returns HTTP 404 if the report does not exist OR belongs to another researcher.
    """
    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    # AC-04: A researcher requesting another researcher's report gets 404 (existence is not revealed)
    if (
        current_user.role == UserRole.RESEARCHER.value
        and report.reporter_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    return report


def update_report(
    session: Session,
    current_user: User,
    report_id: int,
    data: ReportUpdate,
) -> Report:
    """
    Update a researcher's own report while its status is still `New` (FR-10a, AC-05).
    """
    report = get_report_for_user(session, current_user, report_id)

    # Only the owner researcher can edit the report content
    if (
        current_user.role != UserRole.RESEARCHER.value
        or report.reporter_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the reporting researcher can edit this report.",
        )

    # FR-10a & AC-05: Editing a report that is no longer New returns 409 Conflict
    if report.status != ReportStatus.NEW.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report cannot be edited because its status is '{report.status}' (must be 'new').",
        )

    report.title = data.title
    report.description = data.description
    report.component = data.component
    report.steps_to_reproduce = data.steps_to_reproduce
    report.proposed_severity = data.proposed_severity.value
    report.updated_at = datetime.now(timezone.utc)

    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def delete_report(session: Session, current_user: User, report_id: int) -> None:
    """
    Delete a researcher's own report while its status is still `New` (FR-10b, AC-06, AC-07).
    Completes the full CRUD cycle required for the CSE 309 Mid-Project Assessment.
    """
    report = get_report_for_user(session, current_user, report_id)

    # Only the owner researcher can delete their report
    if (
        current_user.role != UserRole.RESEARCHER.value
        or report.reporter_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the reporting researcher can delete this report.",
        )

    # FR-10b & AC-07: Deleting a report that has already entered triage returns 409 Conflict
    if report.status != ReportStatus.NEW.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report cannot be deleted because its status is '{report.status}' (must be 'new').",
        )

    # Clean up any child comments or status history rows before deleting the report
    comments = session.exec(select(Comment).where(Comment.report_id == report.id)).all()
    for comment in comments:
        session.delete(comment)

    histories = session.exec(
        select(StatusHistory).where(StatusHistory.report_id == report.id)
    ).all()
    for hist in histories:
        session.delete(hist)

    session.delete(report)
    session.commit()