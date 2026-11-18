"""
Dashboard Summary Pydantic Schema (backend/app/schemas/dashboard.py)
=====================================================================
"""

from pydantic import BaseModel

from app.models.enums import UserRole


class DashboardSummary(BaseModel):
    """Role-scoped analytics payload returned by GET /api/v1/dashboard/summary."""

    role: UserRole
    total_reports: int
    open_reports: int
    overdue_reports: int
    by_status: dict[str, int]
    by_severity: dict[str, int]
    avg_first_response_hours: float | None = None
    total_users: int | None = None
    banned_users: int | None = None
