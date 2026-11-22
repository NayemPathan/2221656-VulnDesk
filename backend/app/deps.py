"""
Authentication, Current User & RBAC Scope Dependencies (backend/app/deps.py)
=====================================================================
Resolves the acting User from JWT Bearer token (or X-Demo-User when DEMO_MODE=true)
and enforces fine-grained RBAC scopes via `require_scopes(...)`.
=====================================================================
"""

from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import User, UserRole
from app.models.group import Group, GroupMember
from app.services.auth_service import decode_access_token

# Fine-grained RBAC permission matrix (Beta Milestone M5-A)
ROLE_SCOPES: dict[str, set[str]] = {
    UserRole.RESEARCHER.value: {
        "reports:create",
        "reports:read:own",
        "reports:write:own",
        "comments:create:own",
        "comments:read:public",
    },
    UserRole.ANALYST.value: {
        "reports:read:all",
        "triage:write",
        "comments:create:all",
        "comments:read:all",
    },
    UserRole.ADMIN.value: {
        "reports:read:all",
        "triage:reopen",
        "comments:read:all",
        "admin:users",
        "admin:stats",
    },
}


def get_user_scopes(role: str) -> list[str]:
    """Return sorted list of RBAC scopes granted to a given role."""
    return sorted(ROLE_SCOPES.get(role, set()))


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_demo_user: str | None = Header(default=None, alias="X-Demo-User"),
    session: Session = Depends(get_session),
) -> User:
    """Resolve the acting user from a JWT Bearer token or (if DEMO_MODE=true) X-Demo-User."""
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


def require_scopes(*required_scopes: str) -> Callable[..., User]:
    """
    FastAPI Dependency Factory enforcing that `current_user.role` holds all `required_scopes`.
    Raises HTTP 403 Forbidden if any required scope is missing.
    """

    def _scope_dependency(current_user: User = Depends(get_current_user)) -> User:
        granted = ROLE_SCOPES.get(current_user.role, set())
        missing = [scope for scope in required_scopes if scope not in granted]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission scope(s): {', '.join(missing)}.",
            )
        return current_user

    return _scope_dependency

def check_group_permission(
    session: Session,
    group_id: int,
    user: User,
    permission: str,  # "read" | "create" | "edit" | "assign" | "owner"
) -> Group:
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.owner_id == user.id:
        return group

    if permission == "owner":
        raise HTTPException(status_code=403, detail="Only the group owner can perform this action")

    if user.role == "admin" and permission == "read":
        return group

    member = session.exec(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    perm_map = {
        "read": True,
        "create": member.can_create,
        "edit": member.can_edit,
        "assign": member.can_assign,
    }
    if not perm_map.get(permission, False):
        raise HTTPException(status_code=403, detail=f"Missing group permission: {permission}")
    return group
