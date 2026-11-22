"""
Authentication & Profile Router (backend/app/routers/auth.py)
=====================================================================
Exposes /api/v1/auth endpoints for registration, login, refresh token rotation,
logout, session management, profile management, and password changes.
=====================================================================
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlmodel import Session, col, select

from app.config import settings
from app.database import get_session
from app.deps import get_current_user
from app.models import RefreshToken, User
from app.schemas.auth import (
    AuthUserRead,
    ForgotPasswordRequest,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionRead,
    TokenResponse,
)
from app.security import hash_token
from app.services import auth_service
from app.services.audit_service import get_client_meta, log_event

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


def _attach_session_meta(session: Session, raw_refresh: str, request: Request) -> None:
    ip, ua = get_client_meta(request)
    token_row = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh))
    ).first()
    if token_row:
        token_row.ip_address = ip
        token_row.user_agent = ua
        session.add(token_row)
        session.commit()


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
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> TokenResponse:
    try:
        user = auth_service.authenticate_user(session, payload.email, payload.password)
    except HTTPException as exc:
        log_event(
            session,
            user_id=None,
            actor_email=payload.email.lower().strip(),
            action="failed_login",
            target_type="user",
            details=str(exc.detail),
            request=request,
        )
        raise

    access_token = auth_service.create_access_token(user)
    raw_refresh = auth_service.issue_refresh_token(session, user)
    _attach_session_meta(session, raw_refresh, request)
    _set_refresh_cookie(response, raw_refresh)

    log_event(
        session,
        user_id=user.id,
        actor_email=user.email,
        action="login",
        target_type="user",
        target_id=user.id,
        details="Successful login",
        request=request,
    )

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
    request: Request,
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    session: Session = Depends(get_session),
) -> TokenResponse:
    if not refresh_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token cookie.",
        )

    user, new_raw_refresh = auth_service.rotate_refresh_token(session, refresh_cookie)
    _attach_session_meta(session, new_raw_refresh, request)
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
    request: Request,
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    session: Session = Depends(get_session),
) -> Response:
    if refresh_cookie:
        token_row = session.exec(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_cookie))
        ).first()
        if token_row:
            owner = session.get(User, token_row.user_id)
            if owner:
                log_event(
                    session,
                    user_id=owner.id,
                    actor_email=owner.email,
                    action="logout",
                    target_type="session",
                    target_id=token_row.id,
                    details="User logged out",
                    request=request,
                )

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
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AuthUserRead:
    user = auth_service.update_profile(session, current_user, payload)
    log_event(
        session,
        user_id=user.id,
        actor_email=user.email,
        action="profile_update",
        target_type="user",
        target_id=user.id,
        details=f"Updated name to {user.name}",
        request=request,
    )
    return AuthUserRead.model_validate(user)


@router.get(
    "/sessions",
    response_model=list[SessionRead],
    summary="List active refresh sessions for the current user",
)
def list_my_sessions(
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[SessionRead]:
    now = datetime.now(UTC)
    current_hash = hash_token(refresh_cookie) if refresh_cookie else None
    stmt = (
        select(RefreshToken)
        .where(
            col(RefreshToken.user_id) == current_user.id,
            col(RefreshToken.revoked_at).is_(None),
            col(RefreshToken.expires_at) > now,
        )
        .order_by(col(RefreshToken.created_at).desc())
    )
    rows = session.exec(stmt).all()
    sessions: list[SessionRead] = []
    for row in rows:
        if row.id is None:
            raise RuntimeError("Persisted refresh token has no ID.")
        sessions.append(
            SessionRead(
                id=row.id,
                ip_address=row.ip_address,
                user_agent=row.user_agent,
                created_at=row.created_at,
                expires_at=row.expires_at,
                is_current=current_hash is not None and row.token_hash == current_hash,
            )
        )
    return sessions


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a specific active session belonging to the current user",
)
def revoke_my_session(
    session_id: int,
    request: Request,
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    token_row = session.get(RefreshToken, session_id)
    if not token_row or token_row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if refresh_cookie and token_row.token_hash == hash_token(refresh_cookie):
        _clear_refresh_cookie(response)

    if token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(UTC)
        session.add(token_row)
        session.commit()

    log_event(
        session,
        user_id=current_user.id,
        actor_email=current_user.email,
        action="session_revoke",
        target_type="session",
        target_id=session_id,
        details="User revoked session",
        request=request,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password and revoke active refresh sessions",
)
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    auth_service.change_password(session, current_user, payload)
    log_event(
        session,
        user_id=current_user.id,
        actor_email=current_user.email,
        action="password_change",
        target_type="user",
        target_id=current_user.id,
        details="Password changed",
        request=request,
    )
    _clear_refresh_cookie(response)
    return {"detail": "Password updated successfully. Please log in again."}


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request a 15-minute single-use password reset token",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    session: Session = Depends(get_session),
) -> dict[str, str | None]:
    token = auth_service.create_password_reset_token(session, payload.email)
    return {
        "detail": "If an active account exists for that email, a reset token has been generated.",
        "reset_token": token,
    }


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password using a valid reset token",
)
def reset_password(
    payload: ResetPasswordRequest,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    auth_service.reset_password_with_token(session, payload.token, payload.new_password)
    return {"detail": "Password has been reset. You can now sign in."}