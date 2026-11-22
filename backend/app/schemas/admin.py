"""
Admin User Governance & Moderation Pydantic Schemas (backend/app/schemas/admin.py)
=====================================================================
Request and response schemas for /api/v1/admin endpoints.
=====================================================================
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import UserRole


class AdminUserRead(BaseModel):
    """Full user record visible to Administrators."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    is_banned: bool
    ban_reason: str | None = None
    is_deleted: bool
    failed_login_attempts: int
    locked_until: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminUserCreate(BaseModel):
    """Payload for an Administrator to create a Researcher, Analyst, or Admin account."""

    name: str = Field(..., min_length=1, max_length=80)
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = Field(default=UserRole.RESEARCHER)

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


class AdminRoleUpdate(BaseModel):
    """Payload for PATCH /api/v1/admin/users/{user_id}/role."""

    role: UserRole


class AdminBanUpdate(BaseModel):
    """Payload for PATCH /api/v1/admin/users/{user_id}/ban."""

    is_banned: bool
    reason: str | None = Field(default=None, max_length=500)


class AdminOverview(BaseModel):
    """Overview KPIs for the Admin Dashboard."""

    total_users: int
    banned_users: int
    total_reports: int
    total_groups: int
    new_users_7d: int
    new_reports_7d: int


class BulkUserActionRequest(BaseModel):
    """Payload for bulk ban / unban."""

    user_ids: list[int]
    reason: str | None = Field(default="Bulk moderation action", max_length=500)


class BulkReportDeleteRequest(BaseModel):
    """Payload for bulk deleting reports."""

    report_ids: list[int]


class BulkActionResult(BaseModel):
    """Summary returned by bulk admin actions."""

    affected: int
    skipped: int
    skipped_ids: list[int] = []