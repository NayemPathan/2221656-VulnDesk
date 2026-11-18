"""
Admin User Governance Service (backend/app/services/admin_service.py)
=====================================================================
Implements user listing, role assignment, banning/unbanning, and soft-deletion
for Administrators, with automatic refresh token revocation.
=====================================================================
"""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.models import User, UserRole
from app.schemas.admin import AdminBanUpdate, AdminRoleUpdate, AdminUserCreate
from app.security import hash_password
from app.services.auth_service import revoke_all_user_tokens


def list_users(session: Session, include_deleted: bool = False) -> list[User]:
    """Return all user accounts ordered by ID."""
    statement = select(User)
    if not include_deleted:
        statement = statement.where(User.is_deleted == False)
    statement = statement.order_by("id")
    return list(session.exec(statement).all())


def create_user(session: Session, data: AdminUserCreate) -> User:
    """Create a new user account with an explicit role (Admin only)."""
    existing = session.exec(
        select(User).where(func.lower(User.email) == data.email.lower())
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    now = datetime.now(UTC)
    user = User(
        name=data.name,
        email=data.email.lower(),
        role=data.role.value,
        password_hash=hash_password(data.password),
        is_banned=False,
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user_role(
    session: Session,
    current_admin: User,
    target_user_id: int,
    data: AdminRoleUpdate,
) -> User:
    """Change a user's global role, preventing an admin from demoting themselves."""
    if target_user_id == current_admin.id and data.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Administrators cannot demote their own account.",
        )

    user = session.get(User, target_user_id)
    if user is None or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.role = data.role.value
    user.updated_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def set_user_ban(
    session: Session,
    current_admin: User,
    target_user_id: int,
    data: AdminBanUpdate,
) -> User:
    """Ban or unban a user account; banning immediately revokes active refresh tokens."""
    if target_user_id == current_admin.id and data.is_banned:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Administrators cannot ban their own account.",
        )

    user = session.get(User, target_user_id)
    if user is None or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.is_banned = data.is_banned
    user.updated_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    session.refresh(user)

    if data.is_banned:
        if user.id is None:
            raise RuntimeError("Persisted user is missing its ID.")
        revoke_all_user_tokens(session, user.id)

    return user


def soft_delete_user(
    session: Session,
    current_admin: User,
    target_user_id: int,
) -> None:
    """Soft-delete a user account to preserve foreign-key integrity on reports/history."""
    if target_user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Administrators cannot delete their own account.",
        )

    user = session.get(User, target_user_id)
    if user is None or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.is_deleted = True
    user.updated_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    if user.id is None:
        raise RuntimeError("Persisted user is missing its ID.")
    revoke_all_user_tokens(session, user.id)
