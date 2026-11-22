from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, col, select

from app.database import get_session
from app.deps import check_group_permission, get_current_user
from app.models.group import Group, GroupMember
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupMemberRead,
    GroupMemberUpsert,
    GroupRead,
    GroupUpdate,
)
from app.services.audit_service import log_event

router = APIRouter(prefix="/groups", tags=["groups"])


def _build_group_read(session: Session, group: Group) -> GroupRead:
    if group.id is None:
        raise RuntimeError("Persisted group has no ID.")
    group_id = group.id
    owner = session.get(User, group.owner_id)
    members_rows = session.exec(
        select(GroupMember).where(col(GroupMember.group_id) == group_id)
    ).all()
    members: list[GroupMemberRead] = []
    for m in members_rows:
        u = session.get(User, m.user_id)
        if u and u.id is not None:
            members.append(
                GroupMemberRead(
                    user_id=u.id,
                    email=u.email,
                    full_name=u.name,
                    can_create=m.can_create,
                    can_edit=m.can_edit,
                    can_assign=m.can_assign,
                    added_at=m.added_at,
                )
            )
    return GroupRead(
        id=group_id,
        name=group.name,
        description=group.description,
        owner_id=group.owner_id,
        owner_email=owner.email if owner else "unknown",
        created_at=group.created_at,
        members=members,
    )


@router.get("", response_model=list[GroupRead])
def list_groups(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if current_user.role == "admin":
        groups = session.exec(select(Group).order_by(col(Group.created_at).desc())).all()
    else:
        member_group_ids = session.exec(
            select(GroupMember.group_id).where(
                col(GroupMember.user_id) == current_user.id
            )
        ).all()
        groups = session.exec(
            select(Group)
            .where(
                (col(Group.owner_id) == current_user.id)
                | col(Group.id).in_(member_group_ids)
            )
            .order_by(col(Group.created_at).desc())
        ).all()
    return [_build_group_read(session, g) for g in groups]


@router.post("", response_model=GroupRead, status_code=201)
def create_group(
    payload: GroupCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if current_user.id is None:
        raise RuntimeError("Persisted user has no ID.")
    owner_id = current_user.id
    group = Group(
        name=payload.name.strip(),
        description=payload.description,
        owner_id=owner_id,
    )
    session.add(group)
    session.commit()
    session.refresh(group)
    log_event(
        session,
        user_id=current_user.id,
        actor_email=current_user.email,
        action="group_create",
        target_type="group",
        target_id=group.id,
        details=f"Created group '{group.name}'",
        request=request,
    )
    return _build_group_read(session, group)


@router.get("/{group_id}", response_model=GroupRead)
def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    group = check_group_permission(session, group_id, current_user, "read")
    return _build_group_read(session, group)


@router.patch("/{group_id}", response_model=GroupRead)
def rename_group(
    group_id: int,
    payload: GroupUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    group = check_group_permission(session, group_id, current_user, "owner")
    group.name = payload.name.strip()
    group.description = payload.description
    session.add(group)
    session.commit()
    session.refresh(group)
    return _build_group_read(session, group)


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    group = check_group_permission(session, group_id, current_user, "owner")
    name = group.name
    session.delete(group)
    session.commit()
    log_event(
        session,
        user_id=current_user.id,
        actor_email=current_user.email,
        action="group_delete",
        target_type="group",
        target_id=group_id,
        details=f"Deleted group '{name}'",
        request=request,
    )


@router.post("/{group_id}/members", response_model=GroupRead)
def upsert_member(
    group_id: int,
    payload: GroupMemberUpsert,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    group = check_group_permission(session, group_id, current_user, "owner")
    target = session.get(User, payload.user_id)
    if not target or target.is_deleted:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == group.owner_id:
        raise HTTPException(status_code=400, detail="Owner already has full permissions")

    member = session.exec(
        select(GroupMember).where(
            col(GroupMember.group_id) == group_id,
            col(GroupMember.user_id) == payload.user_id,
        )
    ).first()
    if member:
        member.can_create = payload.can_create
        member.can_edit = payload.can_edit
        member.can_assign = payload.can_assign
    else:
        member = GroupMember(
            group_id=group_id,
            user_id=payload.user_id,
            can_create=payload.can_create,
            can_edit=payload.can_edit,
            can_assign=payload.can_assign,
        )
    session.add(member)
    session.commit()
    return _build_group_read(session, group)


@router.delete("/{group_id}/members/{member_user_id}", response_model=GroupRead)
def remove_member(
    group_id: int,
    member_user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    group = check_group_permission(session, group_id, current_user, "owner")
    member = session.exec(
        select(GroupMember).where(
            col(GroupMember.group_id) == group_id,
            col(GroupMember.user_id) == member_user_id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    session.delete(member)
    session.commit()
    return _build_group_read(session, group)

