from datetime import UTC, datetime

from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    actor_email: str = Field(max_length=255, index=True)
    action: str = Field(max_length=64, index=True)
    target_type: str | None = Field(default=None, max_length=64)
    target_id: int | None = Field(default=None)
    details: str | None = Field(default=None, max_length=1000)
    ip_address: str | None = Field(default=None, max_length=64, index=True)
    user_agent: str | None = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), index=True)
