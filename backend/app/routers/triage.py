"""
Analyst Triage & Status History Router (backend/app/routers/triage.py)
=====================================================================
WHAT THIS FILE DOES:
Exposes the HTTP REST endpoints for Triage & Audit Trail under `/api/v1/reports`:
  - `PATCH /api/v1/reports/{report_id}/severity` -> Assign final severity (200 OK)
  - `PATCH /api/v1/reports/{report_id}/status`   -> Transition status & log history (200 OK)
  - `GET   /api/v1/reports/{report_id}/history`  -> List immutable status audit history (200 OK)

WHY WE WROTE IT THIS WAY:
Separating triage endpoints into `routers/triage.py` keeps each router file small and focused,
and groups triage operations cleanly under the `triage` section in `/api/docs`!
=====================================================================
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas.report import ReportRead
from app.schemas.triage import SeverityUpdate, StatusHistoryRead, StatusUpdate
from app.services import triage_service

router = APIRouter(prefix="/reports", tags=["triage"])


@router.patch(
    "/{report_id}/severity",
    response_model=ReportRead,
    summary="Assign final severity to a report (Analyst only)",
)
def assign_severity(
    report_id: int,
    payload: SeverityUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReportRead:
    """
    Assign `final_severity` (`low`, `medium`, `high`, `critical`) to a vulnerability report (FR-12).
    Required before a report can transition to `Confirmed` (FR-14, AC-08).
    """
    report = triage_service.assign_final_severity(session, current_user, report_id, payload)
    return ReportRead.model_validate(report)


@router.patch(
    "/{report_id}/status",
    response_model=ReportRead,
    summary="Transition report status and record audit history (Analyst / Admin)",
)
def change_status(
    report_id: int,
    payload: StatusUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReportRead:
    """
    Transition a report's status along allowed workflow paths (FR-13, FR-14, FR-15, FR-16).
    - Moving to `confirmed` requires `final_severity` to be set (AC-08).
    - Moving to `rejected` requires `rejection_reason` (AC-09).
    - Moving to `duplicate` requires `duplicate_of_id` referencing an existing report.
    - Every transition writes an append-only `StatusHistory` record in the same transaction (NFR-08).
    """
    report = triage_service.transition_report_status(session, current_user, report_id, payload)
    return ReportRead.model_validate(report)


@router.get(
    "/{report_id}/history",
    response_model=list[StatusHistoryRead],
    summary="Get immutable status transition history for a report",
)
def get_report_history(
    report_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[StatusHistoryRead]:
    """
    List all status transitions for a report ordered chronologically oldest-first (FR-15).
    Accessible by the owning Researcher, Security Analysts, and Administrators.
    """
    return triage_service.list_status_history(session, current_user, report_id)