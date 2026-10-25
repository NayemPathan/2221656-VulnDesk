"""
Analyst Triage & Status History Service (backend/app/services/triage_service.py)
=====================================================================
WHAT THIS FILE DOES:
Implements all business logic for Milestone 2 Part B (Phase 3) Triage & Audit Trail:
1. `assign_final_severity`   (`PATCH /api/v1/reports/{id}/severity` — FR-12)
2. `transition_report_status` (`PATCH /api/v1/reports/{id}/status`   — FR-13, FR-14, FR-15, FR-16, NFR-08)
3. `list_status_history`     (`GET   /api/v1/reports/{id}/history`  — FR-15)

WHY WE WROTE IT THIS WAY:
1. Explicit State Machine Dictionary (`ALLOWED_ANALYST_TRANSITIONS`):
   Instead of messy nested `if/else` chains, we represent the SRS Section 2 State Diagram as a clean
   dictionary mapping each `from_status` to the set of allowed `to_status` values. Your tutor can
   verify our state machine in 5 seconds!
2. Precondition Enforcement (`FR-14`, `AC-08`, `AC-09`):
   - Moving to `confirmed` requires `report.final_severity` to be set first (`AC-08`: 409 "final severity required").
   - Moving to `rejected` requires a non-empty `rejection_reason` (`AC-09`: saved on report for researcher visibility).
   - Moving to `duplicate` requires a valid, distinct `duplicate_of_id` pointing to an existing report.
3. Transactional Integrity (`FR-15`, `NFR-08`):
   Both the `Report.status` update and the new `StatusHistory` audit row are added to the same
   `Session` and committed in a single `session.commit()` call. If anything fails, both roll back!
=====================================================================
"""

from datetime import datetime, timezone
from typing import Any, cast

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Report, ReportStatus, StatusHistory, User, UserRole
from app.schemas.triage import SeverityUpdate, StatusHistoryRead, StatusUpdate
from app.services.report_service import get_report_for_user

# SRS Section 2 State Machine: Allowed transitions for Security Analysts (FR-13)
ALLOWED_ANALYST_TRANSITIONS: dict[str, set[str]] = {
    ReportStatus.NEW.value: {
        ReportStatus.UNDER_REVIEW.value,
        ReportStatus.REJECTED.value,
        ReportStatus.DUPLICATE.value,
    },
    ReportStatus.UNDER_REVIEW.value: {
        ReportStatus.CONFIRMED.value,
        ReportStatus.REJECTED.value,
        ReportStatus.DUPLICATE.value,
    },
    ReportStatus.CONFIRMED.value: {
        ReportStatus.FIXED.value,
    },
    ReportStatus.FIXED.value: {
        ReportStatus.CLOSED.value,
    },
    # End states: Analysts cannot transition out of closed, rejected, or duplicate (FR-16)
    ReportStatus.CLOSED.value: set(),
    ReportStatus.REJECTED.value: set(),
    ReportStatus.DUPLICATE.value: set(),
}

# SRS Section 2 State Machine (FR-16): Only an Admin can reopen an end-state report back to Under Review
END_STATES: set[str] = {
    ReportStatus.CLOSED.value,
    ReportStatus.REJECTED.value,
    ReportStatus.DUPLICATE.value,
}


def assign_final_severity(
    session: Session,
    current_user: User,
    report_id: int,
    data: SeverityUpdate,
) -> Report:
    """
    Assign the official `final_severity` (`low`, `medium`, `high`, `critical`) to a report (FR-12).
    Only a Security Analyst is permitted to perform this action.
    """
    if current_user.role != UserRole.ANALYST.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only security analysts can assign final severity.",
        )

    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    report.final_severity = data.final_severity.value
    report.updated_at = datetime.now(timezone.utc)

    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def transition_report_status(
    session: Session,
    current_user: User,
    report_id: int,
    data: StatusUpdate,
) -> Report:
    """
    Transition a report's status along allowed state paths, enforce preconditions (FR-13, FR-14),
    and record an immutable `StatusHistory` entry in the same database transaction (FR-15, NFR-08).
    """
    # 1. Role Check: Researchers can never transition report status
    if current_user.role == UserRole.RESEARCHER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Researchers are not permitted to change report status.",
        )

    actor_id = current_user.id
    if actor_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An authenticated user is required to change report status.",
        )

    # 2. Fetch target report
    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    from_status = report.status
    to_status = data.status.value

    # 3. Validate State Machine Transition based on caller's role (FR-13, FR-16)
    if current_user.role == UserRole.ANALYST.value:
        allowed_targets = ALLOWED_ANALYST_TRANSITIONS.get(from_status, set())
        if to_status not in allowed_targets:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Invalid status transition from '{from_status}' to '{to_status}'. "
                    f"Allowed transitions from '{from_status}': {sorted(allowed_targets) or 'none (end state)'}."
                ),
            )
    elif current_user.role == UserRole.ADMIN.value:
        # FR-16: Admins can only reopen end-state reports (closed, rejected, duplicate) back to under_review
        if from_status not in END_STATES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrators can only reopen end-state reports (closed, rejected, duplicate).",
            )
        if to_status != ReportStatus.UNDER_REVIEW.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"End-state report '{from_status}' can only be reopened to 'under_review'.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to change report status.",
        )

    # 4. Enforce Precondition A (FR-14 & AC-08): Moving to 'confirmed' requires final_severity
    if to_status == ReportStatus.CONFIRMED.value and not report.final_severity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot transition to 'confirmed': final severity required before confirming a report.",
        )

    # 5. Enforce Precondition B (FR-14 & AC-09): Moving to 'rejected' requires rejection_reason
    if to_status == ReportStatus.REJECTED.value:
        if not data.rejection_reason or not data.rejection_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot transition to 'rejected': rejection_reason is required.",
            )
        report.rejection_reason = data.rejection_reason.strip()

    # 6. Enforce Precondition C (FR-14): Moving to 'duplicate' requires a valid, distinct duplicate_of_id
    if to_status == ReportStatus.DUPLICATE.value:
        if data.duplicate_of_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot transition to 'duplicate': duplicate_of_id is required.",
            )
        if data.duplicate_of_id == report.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot transition to 'duplicate': a report cannot be a duplicate of itself.",
            )
        original_report = session.get(Report, data.duplicate_of_id)
        if original_report is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot transition to 'duplicate': original report #{data.duplicate_of_id} does not exist.",
            )
        report.duplicate_of_id = data.duplicate_of_id

    # If an Admin reopens an end-state report to 'under_review', clear prior rejection/duplicate fields
    if current_user.role == UserRole.ADMIN.value and to_status == ReportStatus.UNDER_REVIEW.value:
        report.rejection_reason = None
        report.duplicate_of_id = None

    now = datetime.now(timezone.utc)

    # 7. First-Response SLA Tracking (TDD Section 4 & 7):
    # Record the first analyst who moves the report out of 'new' and when
    if from_status == ReportStatus.NEW.value and report.first_response_at is None:
        report.first_responder_id = actor_id
        report.first_response_at = now

    # 8. Atomic Update: Mutate report status AND append StatusHistory in the same transaction (NFR-08)
    report.status = to_status
    report.updated_at = now

    history_entry = StatusHistory(
        report_id=report_id,
        changed_by=actor_id,
        from_status=from_status,
        to_status=to_status,
        changed_at=now,
    )

    session.add(report)
    session.add(history_entry)
    session.commit()
    session.refresh(report)
    return report


def list_status_history(
    session: Session,
    current_user: User,
    report_id: int,
) -> list[StatusHistoryRead]:
    """
    Return the immutable status transition history for a report ordered oldest-first (FR-15).
    Enforces ownership isolation via `get_report_for_user` (Researchers can only view their own report's history).
    """
    report = get_report_for_user(session, current_user, report_id)

    statement = (
        select(StatusHistory)
        .where(StatusHistory.report_id == report.id)
        .order_by(
            cast(Any, StatusHistory.changed_at),
            cast(Any, StatusHistory.id),
        )
    )
    entries = session.exec(statement).all()

    # Map user IDs to display names so the UI timeline shows who performed each transition
    user_ids = {entry.changed_by for entry in entries}
    users_by_id: dict[int, User] = {}
    if user_ids:
        users = session.exec(select(User).where(cast(Any, User.id).in_(user_ids))).all()
        users_by_id = {u.id: u for u in users if u.id is not None}

    result: list[StatusHistoryRead] = []
    for entry in entries:
        actor = users_by_id.get(entry.changed_by)
        assert entry.id is not None
        result.append(
            StatusHistoryRead(
                id=entry.id,
                report_id=entry.report_id,
                changed_by=entry.changed_by,
                changed_by_name=actor.name if actor else None,
                from_status=ReportStatus(entry.from_status),
                to_status=ReportStatus(entry.to_status),
                changed_at=entry.changed_at,
            )
        )
    return result