"""
Health Check Router (backend/app/routers/health.py)
=====================================================================
WHAT THIS FILE DOES:
Exposes `GET /api/v1/health` (required by TDD Section 5 & SRS NFR-03).

WHY WE WROTE IT THIS WAY:
Instead of just returning `{"status": "ok"}` without checking the database, we inject
an SQLModel session through FastAPI dependency injection and execute a lightweight `SELECT 1` query.
That way, when you deploy to Vercel, hitting `/api/v1/health` proves both that:
1. Your FastAPI serverless function is running, AND
2. Your `DATABASE_URL` connection to Supabase PostgreSQL is working!
=====================================================================
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import literal
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session

SessionDep = Annotated[Session, Depends(get_session)]

# Create a modular APIRouter that `app/main.py` mounts under `/api/v1`
router = APIRouter(tags=["health"])


@router.get("/health", summary="Check API and database health")
def health_check(session: SessionDep) -> dict:
    """
    Execute a lightweight `SELECT 1` ping against the database and return service status.
    Used by uptime monitors (NFR-03) and post-deployment smoke tests (TDD Section 12).
    """
    # Run a trivial SQL query to confirm the database connection is alive
    session.exec(select(literal(1)))

    return {
        "status": "ok",
        "service": settings.project_name,
        "version": settings.version,
        "database": "connected",
        "demo_mode": settings.demo_mode,
    }
