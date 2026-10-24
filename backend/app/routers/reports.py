"""
Reports CRUD Router (backend/app/routers/reports.py)
=====================================================================
WHAT THIS FILE DOES:
Exposes the HTTP REST endpoints under `/api/v1/reports` for Phase 2 (Milestone 2 Part A):
  - `GET    /api/v1/reports/demo-users` -> List seeded demo users for the UI role switcher
  - `POST   /api/v1/reports`            -> Create a new vulnerability report (201 Created)
  - `GET    /api/v1/reports`            -> List reports with filters and pagination (200 OK)
  - `GET    /api/v1/reports/{report_id}`-> Read a single report's details (200 OK)
  - `PUT    /api/v1/reports/{report_id}`-> Update own report while status is New (200 OK)
  - `DELETE /api/v1/reports/{report_id}`-> Delete own report while status is New (204 No Content)

WHY WE WROTE IT THIS WAY (TDD Section 2):
Notice how thin each endpoint function is! Each function only:
  1. Validates query/path/body parameters using FastAPI & Pydantic (`Query`, `ReportCreate`, etc.)
  2. Resolves `current_user` and `session` via `Depends(...)`
  3. Calls `report_service` and returns the result with the right HTTP status code (`201`, `200`, `204`).
=====================================================================
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlmodel import Session

from app.database import get_session
from app.deps import get_current_user
from app.models import ReportStatus, Severity, User
from app.schemas.report import (
    DemoUserRead,
    ReportCreate,
    ReportListResponse,
    ReportRead,
    ReportUpdate,
)
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/demo-users",
    response_model=list[DemoUserRead],
    summary="List seeded demo users for MVP role switching",
)
def get_demo_users(
    session: Annotated[Session, Depends(get_session)],
) -> list[DemoUserRead]:
    """
    Return the seeded demo accounts (Alice, Bob, Mallory, Charlie, Admin) so the React UI
    dropdown and Postman testers can easily switch `X-Demo-User` identities.
    """
    users = report_service.list_demo_users(session)
    return [DemoUserRead.model_validate(u) for u in users]


@router.post(
    "",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new vulnerability report (Create)",
)
def submit_report(
    payload: ReportCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReportRead:
    """
    Submit a new vulnerability report (FR-07, FR-08).
    - Requires a Researcher user (`X-Demo-User: alice@vulndesk.local`).
    - Enforces all 5 submission policy rules; returns 409 Conflict with reason if violated.
    """
    report = report_service.create_report(session, current_user, payload)
    return ReportRead.model_validate(report)


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List vulnerability reports with filters and pagination (Read List)",
)
def list_reports(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: Annotated[
        ReportStatus | None,
        Query(
            alias="status",
            description="Filter by report workflow status (e.g. new, under_review, confirmed).",
        ),
    ] = None,
    severity_filter: Annotated[
        Severity | None,
        Query(
            alias="severity",
            description="Filter by severity (low, medium, high, critical).",
        ),
    ] = None,
    component: Annotated[
        str | None,
        Query(max_length=100, description="Filter by affected component (case-insensitive substring)."),
    ] = None,
    keyword: Annotated[
        str | None,
        Query(max_length=120, description="Search keyword in report title (case-insensitive)."),
    ] = None,
    date_from: Annotated[
        datetime | None,
        Query(description="Filter reports created on or after this ISO 8601 timestamp."),
    ] = None,
    date_to: Annotated[
        datetime | None,
        Query(description="Filter reports created on or before this ISO 8601 timestamp."),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (starts at 1)." )] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Items per page (1 to 100, default 20)."),
    ] = 20,
) -> ReportListResponse:
    """
    List vulnerability reports (FR-09, FR-11).
    - Researchers only see their own submitted reports.
    - Analysts and Admins see all reports across the system.
    """
    return report_service.list_reports(
        session=session,
        current_user=current_user,
        status_filter=status_filter.value if status_filter else None,
        severity_filter=severity_filter.value if severity_filter else None,
        component_filter=component,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{report_id}",
    response_model=ReportRead,
    summary="Get a single vulnerability report by ID (Read Single)",
)
def get_report(
    report_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReportRead:
    """
    Fetch full details of a single report by ID (FR-09).
    Returns 404 if the report does not exist or belongs to another researcher (AC-04).
    """
    report = report_service.get_report_for_user(session, current_user, report_id)
    return ReportRead.model_validate(report)


@router.put(
    "/{report_id}",
    response_model=ReportRead,
    summary="Update own vulnerability report while status is New (Update)",
)
def update_report(
    report_id: int,
    payload: ReportUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReportRead:
    """
    Edit a vulnerability report's title, description, component, steps, or proposed severity (FR-10a).
    Allowed ONLY for the reporting researcher while the report's status is `New` (AC-05).
    """
    report = report_service.update_report(session, current_user, report_id, payload)
    return ReportRead.model_validate(report)


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete own vulnerability report while status is New (Delete)",
)
def delete_report(
    report_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """
    Delete (withdraw) a researcher's own vulnerability report while its status is `New` (FR-10b, AC-06, AC-07).
    Returns HTTP 204 No Content on success.
    """
    report_service.delete_report(session, current_user, report_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)