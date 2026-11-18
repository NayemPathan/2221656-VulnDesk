"""
Admin User Governance Router (backend/app/routers/admin.py)
=====================================================================
Exposes /api/v1/admin/users endpoints protected by `require_scopes("admin:users")`.
=====================================================================
"""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlmodel import Session

from app.database import get_session
from app.deps import require_scopes
from app.models import User
from app.schemas.admin import (
    AdminBanUpdate,
    AdminRoleUpdate,
    AdminUserCreate,
    AdminUserRead,
)
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])
require_admin_users = require_scopes("admin:users")


@router.get(
    "/users",
    response_model=list[AdminUserRead],
    summary="List all platform users (admin:users scope)",
)
def list_users(
    include_deleted: bool = Query(default=False),
    session: Session = Depends(get_session),
    _current_admin: User = Depends(require_admin_users),
) -> list[AdminUserRead]:
    users = admin_service.list_users(session, include_deleted=include_deleted)
    return [AdminUserRead.model_validate(u) for u in users]


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
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> AdminUserRead:
    user = admin_service.update_user_role(session, current_admin, user_id, payload)
    return AdminUserRead.model_validate(user)


@router.patch(
    "/users/{user_id}/ban",
    response_model=AdminUserRead,
    summary="Ban or unban a user account (admin:users scope)",
)
def set_user_ban(
    user_id: int,
    payload: AdminBanUpdate,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> AdminUserRead:
    user = admin_service.set_user_ban(session, current_admin, user_id, payload)
    return AdminUserRead.model_validate(user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a user account (admin:users scope)",
)
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin_users),
) -> Response:
    admin_service.soft_delete_user(session, current_admin, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
