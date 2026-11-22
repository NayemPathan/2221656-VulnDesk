from datetime import UTC, datetime

from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlmodel import Field, SQLModel


class Group(SQLModel, table=True):
    __tablename__ = "group"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=120, index=True)
    description: str | None = Field(default=None, max_length=500)
    owner_id: int = Field(
        sa_column=Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class GroupMember(SQLModel, table=True):
    __tablename__ = "group_member"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_user"),)

    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(
        sa_column=Column(Integer, ForeignKey("group.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    user_id: int = Field(
        sa_column=Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    can_create: bool = Field(default=False)
    can_edit: bool = Field(default=False)
    can_assign: bool = Field(default=False)
    added_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

