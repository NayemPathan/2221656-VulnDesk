"""
Admin User Governance & Moderation Router (backend/app/routers/admin.py)
=====================================================================
Exposes /api/v1/admin endpoints protected by `require_scopes("admin:users")`.
=====================================================================
"""

import csv
import io
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, col, select

from app.database import get_session
from app.deps import require_scopes
from app.models import (
    AuditLog,
    Comment,
    Group,
    GroupMember,
    RefreshToken,
    Report,
    StatusHistory,
    User,
    UserRole,
)
from app.routers.groups import _build_group_read
from app.schemas.admin import (
    AdminBanUpdate,
    AdminOverview,
    AdminRoleUpdate,
    AdminUserCreate,
    AdminUserRead,
    BulkActionResult,
    BulkReportDeleteRequest,
    BulkUserActionRequest,
)
from app.services import admin_service
from app.services.audit_service import log_event

router = APIRouter(prefix="/admin", tags=["admin"])
require_admin_users = require_scopes("admin:users")


def _revoke_user_tokens(session: Session, user_id: int) -> int:
    now = datetime.now(UTC)
    tokens = session.exec(
        select(RefreshToken).where(
            col(RefreshToken.user_id) == user_id,
            col(RefreshToken.revoked_at).is_(None),
        )
    ).all()
    for t in tokens:
        t.revoked_at = now
        session.add(t)
    return len(tokens)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _csv_response(filename: str, headers: list[str], rows: list[list]) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _filter_users(
    users: list[User],
    q: str | None = None,
    role: str | None = None,
    status_filter: str | None = None,
) -> list[User]:
    result = users
    if q and q.strip():
        needle = q.strip().lower()
        result = [u for u in result if needle in u.email.lower() or needle in u.name.lower()]
    if role:
        result = [u for u in result if (u.role.value if hasattr(u.role, "value") else u.role) == role]
    if status_filter == "banned":
        result = [u for u in result if u.is_banned]
    elif status_filter == "active":
        result = [u for u in result if not u.is_banned]
    return result


@router.get(
    "/overview",
    response_model=AdminOverview,
    summary="Overview statistics for the Admin Dashboard",
)
def admin_overview(
    session: Session = Depends(get_session),
    _current_admin: User = Depends(require_admin_users),
) -> AdminOverview:
    week_ago = datetime.now(UTC) - timedelta(days=7)
    users = session.exec(select(User).where(col(User.is_deleted).is_(False))).all()
    reports = session.exec(select(Report)).all()
    groups = session.exec(select(Group)).all()

    return AdminOverview(
        total_users=len(users),
        banned_users=sum(1 for u in users if u.is_banned),
        total_reports=len(reports),
        total_groups=len(groups),
        new_users_7d=sum(
            1 for u in users if _as_utc(u.created_at) >= week_ago
        ),
        new_reports_7d=sum(
            1 for r in reports if _as_utc(r.created_at) >= week_ago
        ),
    )


@router.get(
    "/users",
    response_model=list[AdminUserRead],
    summary="List all platform users (admin:users scope)",
)
def list_users(
    include_deleted: bool = Query(default=False),
    q: str | None = None,
    role: str | None = None,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|banned)$"),
    session: Session = Depends(get_session),
    _current_admin: User = Depends(require_admin_users),
) -> list[AdminUserRead]:
    users = admin_service.list_users(session, include_deleted=include_deleted)
    filtered = _filter_users(users, q=q, role=role, status_filter=status_filter)
    return [AdminUserRead.model_validate(u) for u in filtered]


@router.get(
    "/users/paginated",
    summary="Paginated & filtered users list for Admin Dashboard",
)
def list_users_paginated(
    q: str | None = None,
    role: str | None = None,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|banned)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_session),
    _current_admin: User = Depends(require_admin_users),
):
    users = admin_service.list_users(session, include_deleted=False)
    filtered = _filter_users(users, q=q, role=role, status_filter=status_filter)
    total = len(filtered)
    start = (page - 1) * page_size
    items = [AdminUserRead.model_validate(u) for u in filtered[start : start + page_size]]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post(
    "/users/bulk-ban",
    response_model=BulkActionResult,
    summary="Bulk ban users (skips self and other admins)",
)
def bulk_ban_users(
    payload: BulkUserActionRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> BulkActionResult:
    affected = 0
    skipped_ids: list[int] = []
    for uid in payload.user_ids:
        target = session.get(User, uid)
        target_role = (target.role.value if hasattr(target.role, "value") else target.role) if target else None
        if not target or target.is_deleted or uid == current_admin.id or target_role == UserRole.ADMIN.value:
            skipped_ids.append(uid)
            continue
        target.is_banned = True
        target.ban_reason = (payload.reason or "Bulk ban").strip()
        _revoke_user_tokens(session, uid)
        session.add(target)
        affected += 1

    session.commit()
    log_event(
        session,
        user_id=current_admin.id,
        actor_email=current_admin.email,
        action="ban",
        target_type="user",
        details=f"Bulk ban affected={affected}, skipped={len(skipped_ids)}",
        request=request,
    )
    return BulkActionResult(affected=affected, skipped=len(skipped_ids), skipped_ids=skipped_ids)


@router.post(
    "/users/bulk-unban",
    response_model=BulkActionResult,
    summary="Bulk unban users",
)
def bulk_unban_users(
    payload: BulkUserActionRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> BulkActionResult:
    affected = 0
    skipped_ids: list[int] = []
    for uid in payload.user_ids:
        target = session.get(User, uid)
        if not target or target.is_deleted:
            skipped_ids.append(uid)
            continue
        target.is_banned = False
        target.ban_reason = None
        session.add(target)
        affected += 1

    session.commit()
    log_event(
        session,
        user_id=current_admin.id,
        actor_email=current_admin.email,
        action="unban",
        target_type="user",
        details=f"Bulk unban affected={affected}, skipped={len(skipped_ids)}",
        request=request,
    )
    return BulkActionResult(affected=affected, skipped=len(skipped_ids), skipped_ids=skipped_ids)


@router.get(
    "/users/{user_id}",
    summary="Get full user detail (records, groups, active sessions, recent activity)",
)
def get_user_detail(
    user_id: int,
    session: Session = Depends(get_session),
    _current_admin: User = Depends(require_admin_users),
):
    user = session.get(User, user_id)
    if not user or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    reports = session.exec(select(Report).where(Report.reporter_id == user_id)).all()
    owned_groups = session.exec(select(Group).where(Group.owner_id == user_id)).all()
    member_links = session.exec(select(GroupMember).where(GroupMember.user_id == user_id)).all()
    now = datetime.now(UTC)
    sessions = session.exec(
        select(RefreshToken).where(
            col(RefreshToken.user_id) == user_id,
            col(RefreshToken.revoked_at).is_(None),
            col(RefreshToken.expires_at) > now,
        )
    ).all()
    recent_activity = session.exec(
        select(AuditLog)
        .where(col(AuditLog.user_id) == user_id)
        .order_by(col(AuditLog.created_at).desc())
        .limit(20)
    ).all()

    member_group_ids = [member.group_id for member in member_links]
    member_groups = session.exec(
        select(Group).where(col(Group.id).in_(member_group_ids))
    ).all()
    groups_by_id = {group.id: group for group in [*owned_groups, *member_groups]}

    return {
        "user": AdminUserRead.model_validate(user),
        "reports": reports,
        "groups": list(groups_by_id.values()),
        "sessions": sessions,
        "recent_activity": recent_activity,
    }


@router.post(
    "/users",
    response_model=AdminUserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user with explicit role (admin:users scope)",
)
def create_user(
    payload: AdminUserCreate,
    session: Session = Depends(get_session),
    _current_admin: User = Depends(require_admin_users),
) -> AdminUserRead:
    user = admin_service.create_user(session, payload)
    return AdminUserRead.model_validate(user)


@router.patch(
    "/users/{user_id}/role",
    response_model=AdminUserRead,
    summary="Update a user's global role (admin:users scope)",
)
def update_user_role(
    user_id: int,
    payload: AdminRoleUpdate,
    request: Request,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> AdminUserRead:
    user = admin_service.update_user_role(session, current_admin, user_id, payload)
    log_event(
        session,
        user_id=current_admin.id,
        actor_email=current_admin.email,
        action="role_change",
        target_type="user",
        target_id=user.id,
        details=f"Changed {user.email} role to {payload.role.value}",
        request=request,
    )
    return AdminUserRead.model_validate(user)


@router.patch(
    "/users/{user_id}/ban",
    response_model=AdminUserRead,
    summary="Ban or unban a user account with optional reason (admin:users scope)",
)
def set_user_ban(
    user_id: int,
    payload: AdminBanUpdate,
    request: Request,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> AdminUserRead:
    target = session.get(User, user_id)
    if target and not target.is_deleted:
        target_role = target.role.value if hasattr(target.role, "value") else target.role
        if payload.is_banned and target_role == UserRole.ADMIN.value and target.id != current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins cannot ban another admin.",
            )

    user = admin_service.set_user_ban(session, current_admin, user_id, payload)
    user.ban_reason = (payload.reason or "Policy violation").strip() if payload.is_banned else None
    session.add(user)
    session.commit()
    session.refresh(user)

    log_event(
        session,
        user_id=current_admin.id,
        actor_email=current_admin.email,
        action="ban" if payload.is_banned else "unban",
        target_type="user",
        target_id=user.id,
        details=f"{'Banned' if payload.is_banned else 'Unbanned'} {user.email}"
        + (f": {user.ban_reason}" if user.ban_reason else ""),
        request=request,
    )
    return AdminUserRead.model_validate(user)

@router.get("/groups", summary="Admin content moderation: list all groups")
def admin_list_groups(
    session: Session = Depends(get_session),
    _current_admin: User = Depends(require_admin_users),
):
    groups = session.exec(select(Group).order_by(col(Group.created_at).desc())).all()
    return [_build_group_read(session, g) for g in groups]


@router.delete(
    "/users/{user_id}/sessions",
    summary="Revoke all active refresh sessions for a user",
)
def revoke_user_sessions(
    user_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
):
    target = session.get(User, user_id)
    if not target or target.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    revoked = _revoke_user_tokens(session, user_id)
    session.commit()
    log_event(
        session,
        user_id=current_admin.id,
        actor_email=current_admin.email,
        action="session_revoke",
        target_type="user",
        target_id=user_id,
        details=f"Admin revoked {revoked} session(s) for {target.email}",
        request=request,
    )
    return {"revoked": revoked}


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a user account (admin:users scope)",
)
def delete_user(
    user_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> Response:
    admin_service.soft_delete_user(session, current_admin, user_id)
    log_event(
        session,
        user_id=current_admin.id,
        actor_email=current_admin.email,
        action="delete",
        target_type="user",
        target_id=user_id,
        details=f"Soft-deleted user #{user_id}",
        request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/reports", summary="Admin content moderation: list all reports")
def admin_list_reports(
    q: str | None = None,
    severity: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=15, ge=1, le=100),
    session: Session = Depends(get_session),
    _current_admin: User = Depends(require_admin_users),
):
    stmt = select(Report)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            col(Report.title).ilike(like) | col(Report.description).ilike(like)
        )
    if severity:
        stmt = stmt.where(
            (col(Report.final_severity) == severity)
            | (
                col(Report.final_severity).is_(None)
                & (col(Report.proposed_severity) == severity)
            )
        )
    if status_filter:
        stmt = stmt.where(Report.status == status_filter)

    rows = session.exec(stmt.order_by(col(Report.created_at).desc())).all()
    total = len(rows)
    start = (page - 1) * page_size
    return {"items": rows[start : start + page_size], "total": total, "page": page, "page_size": page_size}


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Admin delete group")
def admin_delete_group(
    group_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> Response:
    g = session.get(Group, group_id)
    if not g:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    name = g.name
    session.delete(g)
    session.commit()
    log_event(
        session,
        user_id=current_admin.id,
        actor_email=current_admin.email,
        action="group_delete",
        target_type="group",
        target_id=group_id,
        details=f"Admin deleted group '{name}'",
        request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit-logs", summary="Search and filter platform audit logs")
def list_audit_logs(
    action: str | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    _current_admin: User = Depends(require_admin_users),
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            col(AuditLog.actor_email).ilike(like)
            | col(AuditLog.details).ilike(like)
            | col(AuditLog.ip_address).ilike(like)
        )
    logs = session.exec(stmt.order_by(col(AuditLog.created_at).desc())).all()
    total = len(logs)
    start = (page - 1) * page_size
    page_logs = logs[start : start + page_size]

    # Resolve human-readable target labels (email, group name, report title)
    user_map = {u.id: u.email for u in session.exec(select(User)).all()}
    group_map = {g.id: g.name for g in session.exec(select(Group)).all()}
    report_map = {r.id: r.title for r in session.exec(select(Report)).all()}

    enriched = []
    for l in page_logs:
        item = l.model_dump()
        label = None
        if l.target_id is not None:
            if l.target_type == "user":
                label = user_map.get(l.target_id, f"User #{l.target_id}")
            elif l.target_type == "group":
                label = group_map.get(l.target_id, f"Group #{l.target_id}")
            elif l.target_type == "report":
                label = report_map.get(l.target_id, f"Report #{l.target_id}")
            elif l.target_type == "session":
                label = f"Session #{l.target_id}"
        elif l.target_type == "export":
            label = "CSV Export"
        item["target_label"] = label
        enriched.append(item)

    return {"items": enriched, "total": total, "page": page, "page_size": page_size}


@router.get("/security", summary="Security view: failed logins by IP and by account")
def security_view(
    session: Session = Depends(get_session),
    _current_admin: User = Depends(require_admin_users),
):
    failed_logs = session.exec(
        select(AuditLog)
        .where(AuditLog.action == "failed_login")
        .order_by(col(AuditLog.created_at).desc())
    ).all()

    by_ip: dict[str, int] = {}
    by_account: dict[str, int] = {}
    for entry in failed_logs:
        ip = entry.ip_address or "unknown"
        by_ip[ip] = by_ip.get(ip, 0) + 1
        by_account[entry.actor_email] = by_account.get(entry.actor_email, 0) + 1

    return {
        "failed_by_ip": [{"ip": k, "count": v} for k, v in sorted(by_ip.items(), key=lambda x: -x[1])],
        "failed_by_account": [{"email": k, "count": v} for k, v in sorted(by_account.items(), key=lambda x: -x[1])],
        "recent_failures": failed_logs[:20],
    }


@router.get("/export/users", summary="Export filtered users as CSV")
def export_users_csv(
    request: Request,
    q: str | None = None,
    role: str | None = None,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|banned)$"),
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> StreamingResponse:
    users = admin_service.list_users(session, include_deleted=False)
    filtered = _filter_users(users, q=q, role=role, status_filter=status_filter)
    log_event(
        session,
        user_id=current_admin.id,
        actor_email=current_admin.email,
        action="export",
        target_type="export",
        details=f"Exported {len(filtered)} users CSV",
        request=request,
    )
    rows = [
        [
            u.id,
            u.email,
            u.name,
            u.role.value if hasattr(u.role, "value") else u.role,
            u.is_banned,
            u.ban_reason or "",
            u.created_at,
        ]
        for u in filtered
    ]
    return _csv_response(
        "vulndesk_users.csv",
        ["ID", "Email", "Name", "Role", "Banned", "Ban Reason", "Created At"],
        rows,
    )


@router.get("/export/reports", summary="Export filtered reports as CSV")
def export_reports_csv(
    request: Request,
    q: str | None = None,
    severity: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> StreamingResponse:
    stmt = select(Report)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            col(Report.title).ilike(like) | col(Report.description).ilike(like)
        )
    if severity:
        stmt = stmt.where(
            (col(Report.final_severity) == severity)
            | (
                col(Report.final_severity).is_(None)
                & (col(Report.proposed_severity) == severity)
            )
        )
    if status_filter:
        stmt = stmt.where(Report.status == status_filter)

    reports = session.exec(stmt.order_by(col(Report.created_at).desc())).all()
    log_event(
        session,
        user_id=current_admin.id,
        actor_email=current_admin.email,
        action="export",
        target_type="export",
        details=f"Exported {len(reports)} reports CSV",
        request=request,
    )
    rows = [
        [r.id, r.title, r.final_severity or r.proposed_severity, r.status, r.reporter_id, r.group_id or "", r.created_at]
        for r in reports
    ]
    return _csv_response(
        "vulndesk_reports.csv",
        ["ID", "Title", "Severity", "Status", "Reporter ID", "Group ID", "Created At"],
        rows,
    )


@router.get("/export/audit-logs", summary="Export filtered audit logs as CSV")
def export_audit_logs_csv(
    request: Request,
    action: str | None = None,
    q: str | None = None,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> StreamingResponse:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            col(AuditLog.actor_email).ilike(like)
            | col(AuditLog.details).ilike(like)
            | col(AuditLog.ip_address).ilike(like)
        )

    logs = session.exec(stmt.order_by(col(AuditLog.created_at).desc())).all()
    log_event(
        session,
        user_id=current_admin.id,
        actor_email=current_admin.email,
        action="export",
        target_type="export",
        details=f"Exported {len(logs)} audit logs CSV",
        request=request,
    )
    rows = [
        [l.id, l.actor_email, l.action, l.target_type or "", l.target_id or "", l.ip_address or "", l.details or "", l.created_at]
        for l in logs
    ]
    return _csv_response(
        "vulndesk_audit_logs.csv",
        ["ID", "Actor Email", "Action", "Target Type", "Target ID", "IP Address", "Details", "Created At"],
        rows,
    )
    
@router.post("/reports/bulk-delete", response_model=BulkActionResult, summary="Bulk delete reports")
def bulk_delete_reports(
    payload: BulkReportDeleteRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> BulkActionResult:
    affected = 0
    skipped_ids: list[int] = []
    for rid in payload.report_ids:
        r = session.get(Report, rid)
        if not r:
            skipped_ids.append(rid)
            continue

        # Delete child comments & status history rows first (Postgres FK constraint)
        for comment in session.exec(select(Comment).where(Comment.report_id == rid)).all():
            session.delete(comment)
        for hist in session.exec(select(StatusHistory).where(StatusHistory.report_id == rid)).all():
            session.delete(hist)

        session.flush()
        session.delete(r)
        affected += 1

    session.commit()
    log_event(
        session,
        user_id=current_admin.id,
        actor_email=current_admin.email,
        action="delete",
        target_type="report",
        details=f"Bulk deleted {affected} report(s), skipped={len(skipped_ids)}",
        request=request,
    )
    return BulkActionResult(affected=affected, skipped=len(skipped_ids), skipped_ids=skipped_ids)