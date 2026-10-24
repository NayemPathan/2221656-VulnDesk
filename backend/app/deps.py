"""
Authentication & Current User Dependency (backend/app/deps.py)
=====================================================================
WHAT THIS FILE DOES:
Defines `get_current_user()`, a FastAPI Dependency Injection function that resolves which
User is making the current HTTP request.

WHY WE WROTE IT THIS WAY (SRS FR-30 & TDD Section 6 "MVP Seam"):
1. What is the "MVP Seam"?
   In the MVP (Milestones 1-3), real JWT login is not built yet. Instead, the caller sends the
   `X-Demo-User` HTTP header containing a seeded demo user's email (e.g. `alice@vulndesk.local`
   or `charlie@vulndesk.local`).
2. Why put this logic inside `get_current_user()`?
   Every router in our app simply declares `current_user: User = Depends(get_current_user)`.
   When we move to the Beta release (Milestone 4), we only change the inside of THIS function
   to decode a JWT Bearer token — none of our routers or services will need to change!
3. Why does `get_current_user` allow a banned user (`mallory@vulndesk.local`) through in MVP?
   Because Submission Policy Rule (iv) (FR-08) requires `POST /api/v1/reports` to check whether
   the researcher's account is banned and return HTTP `409 Conflict` with the specific policy
   reason! If `deps.py` blocked Mallory with 401 first, we could never test Rule (iv) returning 409.
=====================================================================
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import User


def get_current_user(
    session: Annotated[Session, Depends(get_session)],
    x_demo_user: Annotated[
        str | None,
        Header(alias="X-Demo-User", description="..."),
    ] = None,
) -> User:
    """
    Resolve the acting user from the `X-Demo-User` header when `DEMO_MODE=true`.
    Raises HTTP 401 if Demo Mode is disabled, the header is missing, or the user does not exist.
    """
    # Security check (TDD Section 6): The X-Demo-User header is only honored when DEMO_MODE=true
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Demo mode is disabled. Please authenticate with a valid token.",
        )

    # AC-15: If no identity header is provided, reject with 401 Unauthorized
    if not x_demo_user or not x_demo_user.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Demo-User header (e.g. alice@vulndesk.local).",
        )

    identifier = x_demo_user.strip()

    # Allow lookup by numeric user ID (e.g. "1") or case-insensitive email (e.g. "alice@vulndesk.local")
    if identifier.isdigit():
        statement = select(User).where(User.id == int(identifier))
    else:
        statement = select(User).where(func.lower(User.email) == identifier.lower())

    user = session.exec(statement).first()

    # Reject if user does not exist or has been soft-deleted (is_deleted=True)
    if user is None or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Demo user '{identifier}' not found or inactive.",
        )

    return user
