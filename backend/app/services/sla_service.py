"""
SLA Deadlines & Dashboard Analytics Service (backend/app/services/sla_service.py)
=====================================================================
Computes severity-based first-response SLA deadlines (`sla_due_at`, `is_overdue`)
and aggregates role-scoped summary metrics for GET /api/v1/dashboard/summary.
=====================================================================
"""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.models import Report, ReportStatus, Severity, User, UserRole
from app.schemas.dashboard import DashboardSummary

SLA_DAYS_BY_SEVERITY: dict[str, int] = {
    Severity.CRITICAL.value: 1,
    Severity.HIGH.value: 2,
    Severity.MEDIUM.value: 5,
    Severity.LOW.value: 10,
}


def _as_utc(dt: datetime) -> datetime:
    """Normalize naive SQLite datetimes to timezone-aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def compute_sla_due_at(created_at: datetime, effective_severity: str) -> datetime:
    """Return the UTC first-response deadline based on report severity."""
    days = SLA_DAYS_BY_SEVERITY.get(effective_severity, 10)
    return _as_utc(created_at) + timedelta(days=days)


def compute_is_overdue(
    status: str,
    first_response_at: datetime | None,
    sla_due_at: datetime,
    now: datetime | None = None,
) -> bool:
    """A report is overdue only if it is still `new` (unanswered) past its SLA deadline."""
    if status != ReportStatus.NEW.value or first_response_at is not None:
        return False
    current = now or datetime.now(UTC)
    return current > _as_utc(sla_due_at)


def get_dashboard_summary(session: Session, current_user: User) -> DashboardSummary:
    """Aggregate report and (for Admins) user statistics scoped to the caller's role."""
    statement = select(Report)
    if current_user.role == UserRole.RESEARCHER.value:
        statement = statement.where(Report.reporter_id == current_user.id)

    reports = session.exec(statement).all()
    now = datetime.now(UTC)

    by_status: dict[str, int] = {st.value: 0 for st in ReportStatus}
    by_severity: dict[str, int] = {sev.value: 0 for sev in Severity}
    open_reports = 0
    overdue_reports = 0
    response_hours: list[float] = []

    for rep in reports:
        by_status[rep.status] = by_status.get(rep.status, 0) + 1

        eff_sev = rep.final_severity or rep.proposed_severity
        by_severity[eff_sev] = by_severity.get(eff_sev, 0) + 1

        if rep.status in (ReportStatus.NEW.value, ReportStatus.UNDER_REVIEW.value):
            open_reports += 1

        due_at = compute_sla_due_at(rep.created_at, eff_sev)
        if compute_is_overdue(rep.status, rep.first_response_at, due_at, now=now):
            overdue_reports += 1

        if rep.first_response_at is not None:
            delta_sec = (
                _as_utc(rep.first_response_at) - _as_utc(rep.created_at)
            ).total_seconds()
            response_hours.append(max(0.0, delta_sec / 3600.0))

    avg_hours = (
        round(sum(response_hours) / len(response_hours), 2)
        if response_hours
        else None
    )

    total_users: int | None = None
    banned_users: int | None = None
    if current_user.role == UserRole.ADMIN.value:
        active_users = session.exec(
            select(User).where(User.is_deleted == False)
        ).all()
        total_users = len(active_users)
        banned_users = sum(1 for u in active_users if u.is_banned)

    return DashboardSummary(
        role=UserRole(current_user.role),
        total_reports=len(reports),
        open_reports=open_reports,
        overdue_reports=overdue_reports,
        by_status=by_status,
        by_severity=by_severity,
        avg_first_response_hours=avg_hours,
        total_users=total_users,
        banned_users=banned_users,
    )
