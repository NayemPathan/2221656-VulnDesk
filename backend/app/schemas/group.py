from datetime import datetime

from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class GroupUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class GroupMemberUpsert(BaseModel):
    user_id: int
    can_create: bool = False
    can_edit: bool = False
    can_assign: bool = False


class GroupMemberRead(BaseModel):
    user_id: int
    email: str
    name: str
    can_create: bool
    can_edit: bool
    can_assign: bool
    added_at: datetime


class GroupRead(BaseModel):
    id: int
    name: str
    description: str | None
    owner_id: int
    owner_email: str
    created_at: datetime
    members: list[GroupMemberRead] = []

