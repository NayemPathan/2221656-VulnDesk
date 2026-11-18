"""
Dashboard Analytics Router (backend/app/routers/dashboard.py)
=====================================================================
Exposes GET /api/v1/dashboard/summary returning role-scoped metrics.
=====================================================================
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas.dashboard import DashboardSummary
from app.services import sla_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get role-scoped vulnerability & SLA summary statistics",
)
def get_summary(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DashboardSummary:
    return sla_service.get_dashboard_summary(session, current_user)
