"""
Report CRUD Service (backend/app/services/report_service.py)
=====================================================================
Implements ownership isolation, shared-group permission checks (create/read/edit),
5-rule submission policy, filtering, and state-gated updates/deletes.
=====================================================================
"""

import math
from datetime import UTC, datetime
from typing import cast

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, select

from app.deps import check_group_permission
from app.models import (
    Comment,
    Group,
    GroupMember,
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
    """Return all active (non-deleted) seeded users."""
    statement = (
        select(User)
        .where(User.is_deleted == False)
        .order_by(func.coalesce(User.id, 0))
    )
    return list(session.exec(statement).all())


def create_report(session: Session, current_user: User, data: ReportCreate) -> Report:
    """
    Validate submission policy + group `create` permission (if group_id is set)
    and create a new vulnerability report with status `New`.
    """
    if data.group_id is not None:
        check_group_permission(session, data.group_id, current_user, "create")
    elif current_user.role != UserRole.RESEARCHER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only researchers can submit personal vulnerability reports.",
        )

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

    now = datetime.now(UTC)
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
        group_id=data.group_id,
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
    group_id_filter: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> ReportListResponse:
    """
    List vulnerability reports with role + group visibility, filtering, and pagination.
    - Researchers see their own reports + reports in groups they own or belong to.
    - Analysts and Admins see all reports.
    """
    conditions = []

    if group_id_filter is not None:
        if current_user.role == UserRole.RESEARCHER.value:
            check_group_permission(session, group_id_filter, current_user, "read")
        conditions.append(Report.group_id == group_id_filter)
    elif current_user.role == UserRole.RESEARCHER.value:
        owned_gids = session.exec(
            select(Group.id).where(Group.owner_id == current_user.id)
        ).all()
        member_gids = session.exec(
            select(GroupMember.group_id).where(GroupMember.user_id == current_user.id)
        ).all()
        allowed_gids = [gid for gid in (set(owned_gids) | set(member_gids)) if gid is not None]

        if allowed_gids:
            conditions.append(
                or_(
                    cast(ColumnElement[bool], Report.reporter_id == current_user.id),
                    cast(ColumnElement[int], Report.group_id).in_(allowed_gids),
                )
            )
        else:
            conditions.append(Report.reporter_id == current_user.id)

    if status_filter:
        conditions.append(Report.status == status_filter.strip().lower())

    if severity_filter:
        sev = severity_filter.strip().lower()
        final_severity_condition = cast(ColumnElement[bool], Report.final_severity == sev)
        fallback_severity_condition = cast(
            ColumnElement[bool],
            (Report.final_severity == None) & (Report.proposed_severity == sev),
        )
        conditions.append(or_(final_severity_condition, fallback_severity_condition))

    if component_filter and component_filter.strip():
        comp_pattern = f"%{component_filter.strip().lower()}%"
        conditions.append(func.lower(Report.component).like(comp_pattern))

    if keyword and keyword.strip():
        kw_pattern = f"%{keyword.strip().lower()}%"
        conditions.append(func.lower(Report.title).like(kw_pattern))

    if date_from is not None:
        conditions.append(Report.created_at >= date_from)
    if date_to is not None:
        conditions.append(Report.created_at <= date_to)

    count_stmt = select(func.count()).select_from(Report)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = session.exec(count_stmt).one()

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
    Fetch a single report and enforce ownership + shared-group read access.
    """
    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    if (
        current_user.role == UserRole.RESEARCHER.value
        and report.reporter_id != current_user.id
    ):
        if report.group_id is not None:
            check_group_permission(session, report.group_id, current_user, "read")
        else:
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
    Update a report while its status is `New`.
    Allowed for the reporting researcher OR a group member with `can_edit=True`.
    """
    report = get_report_for_user(session, current_user, report_id)

    if report.reporter_id != current_user.id:
        if report.group_id is not None:
            check_group_permission(session, report.group_id, current_user, "edit")
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the reporting researcher can edit this report.",
            )
    elif current_user.role != UserRole.RESEARCHER.value and report.group_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the reporting researcher can edit this report.",
        )

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
    report.updated_at = datetime.now(UTC)

    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def delete_report(session: Session, current_user: User, report_id: int) -> None:
    """
    Delete a researcher's own report while its status is still `New`.
    """
    report = get_report_for_user(session, current_user, report_id)

    if (
        current_user.role != UserRole.RESEARCHER.value
        or report.reporter_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the reporting researcher can delete this report.",
        )

    if report.status != ReportStatus.NEW.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report cannot be deleted because its status is '{report.status}' (must be 'new').",
        )

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