"""
Reports CRUD Router (backend/app/routers/reports.py)
=====================================================================
Exposes /api/v1/reports endpoints with ownership + shared-group RBAC.
=====================================================================
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
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
from app.services.audit_service import log_event

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/demo-users",
    response_model=list[DemoUserRead],
    summary="List seeded demo users for MVP role switching",
)
def get_demo_users(
    session: Annotated[Session, Depends(get_session)],
) -> list[DemoUserRead]:
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
        Query(alias="status", description="Filter by report workflow status."),
    ] = None,
    severity_filter: Annotated[
        Severity | None,
        Query(alias="severity", description="Filter by severity."),
    ] = None,
    component: Annotated[
        str | None,
        Query(max_length=100, description="Filter by affected component."),
    ] = None,
    keyword: Annotated[
        str | None,
        Query(max_length=120, description="Search keyword in report title."),
    ] = None,
    group_id: Annotated[
        int | None,
        Query(description="Filter reports belonging to a specific shared group."),
    ] = None,
    date_from: Annotated[
        datetime | None,
        Query(description="Filter reports created on or after this ISO 8601 timestamp."),
    ] = None,
    date_to: Annotated[
        datetime | None,
        Query(description="Filter reports created on or before this ISO 8601 timestamp."),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (starts at 1).")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Items per page (1 to 100, default 20)."),
    ] = 20,
) -> ReportListResponse:
    return report_service.list_reports(
        session=session,
        current_user=current_user,
        status_filter=status_filter.value if status_filter else None,
        severity_filter=severity_filter.value if severity_filter else None,
        component_filter=component,
        keyword=keyword,
        group_id_filter=group_id,
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
    report = report_service.get_report_for_user(session, current_user, report_id)
    return ReportRead.model_validate(report)


@router.put(
    "/{report_id}",
    response_model=ReportRead,
    summary="Update own or group-editable vulnerability report while status is New",
)
def update_report(
    report_id: int,
    payload: ReportUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReportRead:
    report = report_service.update_report(session, current_user, report_id, payload)
    return ReportRead.model_validate(report)


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete own vulnerability report while status is New",
)
def delete_report(
    report_id: int,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    report_service.delete_report(session, current_user, report_id)
    log_event(
        session,
        user_id=current_user.id,
        actor_email=current_user.email,
        action="delete",
        target_type="report",
        target_id=report_id,
        details=f"Deleted report #{report_id}",
        request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)