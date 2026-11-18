"""
Authentication & Current User Dependency (backend/app/deps.py)
=====================================================================
Resolves the acting User from:
1. `Authorization: Bearer <jwt>` header (Beta JWT Auth), OR
2. `X-Demo-User` header when `DEMO_MODE=true` and no Bearer token is supplied.
=====================================================================
"""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import User
from app.services.auth_service import decode_access_token


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_demo_user: str | None = Header(default=None, alias="X-Demo-User"),
    session: Session = Depends(get_session),
) -> User:
    """Resolve the acting user from a JWT Bearer token or (if DEMO_MODE=true) X-Demo-User."""
    # 1. Preferred Path: JWT Bearer Token
    if authorization and authorization.strip().lower().startswith("bearer "):
        raw_token = authorization.strip().split(" ", 1)[1].strip()
        payload = decode_access_token(raw_token)
        sub = payload.get("sub")
        if not sub or not str(sub).isdigit():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject.",
            )
        user = session.get(User, int(sub))
        if user is None or user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found or deleted.",
            )
        if user.is_banned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is banned.",
            )
        return user

    # 2. MVP Fallback Path (only active while DEMO_MODE=true)
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer token.",
        )

    if not x_demo_user or not x_demo_user.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer token or X-Demo-User header.",
        )

    identifier = x_demo_user.strip()
    if identifier.isdigit():
        statement = select(User).where(User.id == int(identifier))
    else:
        statement = select(User).where(func.lower(User.email) == identifier.lower())

    user = session.exec(statement).first()
    if user is None or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Demo user '{identifier}' not found or inactive.",
        )

    return user
