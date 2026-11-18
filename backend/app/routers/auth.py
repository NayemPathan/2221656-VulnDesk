"""
Authentication & Profile Router (backend/app/routers/auth.py)
=====================================================================
Exposes /api/v1/auth endpoints for registration, login, refresh token rotation,
logout, profile management, and password changes.
=====================================================================
"""


from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas.auth import (
    AuthUserRead,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "vulndesk_refresh_token"


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
    )


@router.post(
    "/register",
    response_model=AuthUserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new researcher account",
)
def register(
    payload: RegisterRequest,
    session: Session = Depends(get_session),
) -> AuthUserRead:
    user = auth_service.register_user(session, payload)
    return AuthUserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a 15-minute JWT + 7-day refresh cookie",
)
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> TokenResponse:
    user = auth_service.authenticate_user(session, payload.email, payload.password)
    access_token = auth_service.create_access_token(user)
    raw_refresh = auth_service.issue_refresh_token(session, user)
    _set_refresh_cookie(response, raw_refresh)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=AuthUserRead.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh cookie and issue a fresh JWT access token",
)
def refresh(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    session: Session = Depends(get_session),
) -> TokenResponse:
    if not refresh_cookie:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token cookie.",
        )

    user, new_raw_refresh = auth_service.rotate_refresh_token(session, refresh_cookie)
    access_token = auth_service.create_access_token(user)
    _set_refresh_cookie(response, new_raw_refresh)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=AuthUserRead.model_validate(user),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke current refresh token and clear session cookie",
)
def logout(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    session: Session = Depends(get_session),
) -> Response:
    auth_service.revoke_refresh_token(session, refresh_cookie)
    _clear_refresh_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=AuthUserRead,
    summary="Get the currently authenticated user's profile",
)
def get_me(current_user: User = Depends(get_current_user)) -> AuthUserRead:
    return AuthUserRead.model_validate(current_user)


@router.patch(
    "/me",
    response_model=AuthUserRead,
    summary="Update the authenticated user's display name",
)
def update_me(
    payload: ProfileUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AuthUserRead:
    user = auth_service.update_profile(session, current_user, payload)
    return AuthUserRead.model_validate(user)


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password and revoke active refresh sessions",
)
def change_password(
    payload: PasswordChangeRequest,
    response: Response,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    auth_service.change_password(session, current_user, payload)
    _clear_refresh_cookie(response)
    return {"detail": "Password updated successfully. Please log in again."}

