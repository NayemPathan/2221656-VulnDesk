"""
Authentication & Session Service (backend/app/services/auth_service.py)
=====================================================================
Implements registration, login with brute-force lockout, JWT creation/decoding,
7-day rotating refresh tokens with reuse detection, and profile/password updates.
=====================================================================
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.config import settings
from app.models import RefreshToken, User, UserRole
from app.schemas.auth import (
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegisterRequest,
)
from app.security import (
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)


def _as_utc(dt: datetime) -> datetime:
    """Normalize naive SQLite datetimes to timezone-aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def create_access_token(user: User) -> str:
    """Create a signed 15-minute JWT access token containing user ID, email, and role."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()
        ),
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token, raising HTTP 401 on any failure."""
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
        ) from exc


def register_user(session: Session, data: RegisterRequest) -> User:
    """Register a new Researcher account with an Argon2id password hash."""
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
        role=UserRole.RESEARCHER.value,
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


def authenticate_user(session: Session, email: str, password: str) -> User:
    """Verify email/password, enforce account lockout, and reset failure counter on success."""
    user = session.exec(
        select(User).where(func.lower(User.email) == email.strip().lower())
    ).first()

    if user is None or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is banned. Contact an administrator.",
        )

    now = datetime.now(UTC)
    if user.locked_until is not None and _as_utc(user.locked_until) > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to repeated failed login attempts. Try again later.",
        )

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_login_attempts:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
        user.updated_at = now
        session.add(user)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Reset lockout counters on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = now
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def issue_refresh_token(session: Session, user: User) -> str:
    """Generate and persist a hashed 7-day refresh token, returning the raw token."""
    raw_token = generate_refresh_token()
    now = datetime.now(UTC)
    if user.id is None:
        raise RuntimeError("Persisted user has no ID.")
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        created_at=now,
    )
    session.add(record)
    session.commit()
    return raw_token


def revoke_all_user_tokens(session: Session, user_id: int) -> None:
    """Revoke all active refresh tokens for a user (on token reuse, password change, or ban)."""
    now = datetime.now(UTC)
    tokens = session.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at == None,
        )
    ).all()
    for tok in tokens:
        tok.revoked_at = now
        session.add(tok)
    session.commit()


def rotate_refresh_token(session: Session, raw_token: str) -> tuple[User, str]:
    """
    Validate a refresh token, revoke it, and issue a new one.
    If a previously revoked token is replayed, revoke all tokens for that user.
    """
    digest = hash_token(raw_token)
    record = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == digest)
    ).first()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    now = datetime.now(UTC)

    # Reuse detection: if this token was already rotated/revoked, invalidate all user sessions
    if record.revoked_at is not None:
        revoke_all_user_tokens(session, record.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has already been used or revoked.",
        )

    if _as_utc(record.expires_at) <= now:
        record.revoked_at = now
        session.add(record)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired.",
        )

    user = session.get(User, record.user_id)
    if user is None or user.is_deleted or user.is_banned:
        record.revoked_at = now
        session.add(record)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or banned.",
        )

    # Rotate: revoke current token and issue a fresh one atomically
    record.revoked_at = now
    new_raw = generate_refresh_token()
    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or banned.",
        )
    new_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_raw),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        created_at=now,
    )
    session.add(record)
    session.add(new_record)
    session.commit()
    return user, new_raw


def revoke_refresh_token(session: Session, raw_token: str | None) -> None:
    """Revoke a single refresh token during logout."""
    if not raw_token:
        return
    digest = hash_token(raw_token)
    record = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == digest)
    ).first()
    if record is not None and record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
        session.add(record)
        session.commit()


def update_profile(
    session: Session, current_user: User, data: ProfileUpdateRequest
) -> User:
    """Update the authenticated user's display name."""
    current_user.name = data.name
    current_user.updated_at = datetime.now(UTC)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


def change_password(
    session: Session, current_user: User, data: PasswordChangeRequest
) -> None:
    """Verify current password, update Argon2id hash, and revoke existing sessions."""
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    current_user.password_hash = hash_password(data.new_password)
    current_user.updated_at = datetime.now(UTC)
    session.add(current_user)
    session.commit()
    if current_user.id is None:
        raise RuntimeError("Persisted user has no ID.")
    revoke_all_user_tokens(session, current_user.id)
