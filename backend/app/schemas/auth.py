"""
Authentication & Profile Pydantic Schemas (backend/app/schemas/auth.py)
=====================================================================
Defines request/response models for registration, login, JWT tokens,
profile updates, and password changes.
=====================================================================
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    """Public researcher self-registration payload."""

    name: str = Field(..., min_length=1, max_length=80)
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        if isinstance(value, str):
            cleaned = value.strip().lower()
            if "@" not in cleaned or "." not in cleaned.split("@", 1)[-1]:
                raise ValueError("Invalid email address format.")
            return cleaned
        return value


class LoginRequest(BaseModel):
    """Credentials payload for POST /api/v1/auth/login."""

    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value


class AuthUserRead(BaseModel):
    """Safe user profile returned by /auth/register, /auth/login, and /auth/me."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    is_banned: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT access token response returned by /auth/login and /auth/refresh."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserRead


class ProfileUpdateRequest(BaseModel):
    """Payload for PATCH /api/v1/auth/me."""

    name: str = Field(..., min_length=1, max_length=80)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class PasswordChangeRequest(BaseModel):
    """Payload for POST /api/v1/auth/change-password."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
    
class ForgotPasswordRequest(BaseModel):
    """Payload for POST /api/v1/auth/forgot-password."""

    email: str = Field(..., min_length=3, max_length=254)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value


class ResetPasswordRequest(BaseModel):
    """Payload for POST /api/v1/auth/reset-password."""

    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)
