"""
Comments & Internal Notes Service (backend/app/services/comment_service.py)
=====================================================================
WHAT THIS FILE DOES:
Implements business logic for creating and listing report comments and analyst internal notes:
1. `create_comment` (`POST /api/v1/reports/{id}/comments` — FR-18, FR-19)
2. `list_comments`  (`GET  /api/v1/reports/{id}/comments` — FR-20, AC-10)

WHY WE WROTE IT THIS WAY:
1. Ownership Isolation (`FR-09`, `FR-18`):
   By calling `get_report_for_user(session, current_user, report_id)` first, a Researcher trying
   to read or post comments on another Researcher's report receives HTTP `404 Not Found` (never
   leaking whether the report exists).
2. Strict Internal Note Guard (`FR-19`, `AC-10`):
   - Only a Security Analyst can create an internal note (`is_internal=True`). If a Researcher attempts
     to pass `is_internal=True`, we reject with HTTP `403 Forbidden`.
   - When a Researcher lists comments (`GET /reports/{id}/comments`), we add a SQL `.where(Comment.is_internal == False)`
     filter so internal notes are NEVER serialized or sent over the network to researchers (`AC-10`).
3. Chronological Ordering (`FR-20`):
   Comments are ordered oldest-first (`created_at ASC, id ASC`) so the discussion reads naturally.
=====================================================================
"""

from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models import Comment, User, UserRole
from app.schemas.comment import CommentCreate, CommentRead
from app.services.report_service import get_report_for_user


def create_comment(
    session: Session,
    current_user: User,
    report_id: int,
    data: CommentCreate,
) -> CommentRead:
    """
    Add a public comment or an analyst-only internal note to a report (FR-18, FR-19).
    - Researchers can only post public comments (`is_internal=False`) on their own reports.
    - Analysts can post public comments or internal notes (`is_internal=True`) on any report.
    """
    # Step 1: Verify report exists and (if Researcher) belongs to current_user (returns 404 otherwise)
    report = get_report_for_user(session, current_user, report_id)

    # Step 2: Check role permission to post comments (FR-18: Owner Researcher or Analyst)
    if current_user.role not in (UserRole.RESEARCHER.value, UserRole.ANALYST.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the reporting researcher or a security analyst can post comments.",
        )

    # Step 3: FR-19 Guard — Researchers are strictly forbidden from posting internal notes
    if data.is_internal and current_user.role != UserRole.ANALYST.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only security analysts can post internal notes.",
        )

    now = datetime.now(timezone.utc)
    comment = Comment(
        report_id=report.id,  # type: ignore[arg-type]
        author_id=current_user.id,  # type: ignore[arg-type]
        body=data.body,
        is_internal=data.is_internal,
        created_at=now,
    )

    session.add(comment)
    session.commit()
    session.refresh(comment)

    return CommentRead(
        id=comment.id,  # type: ignore[arg-type]
        report_id=comment.report_id,
        author_id=comment.author_id,
        author_name=current_user.name,
        author_role=UserRole(current_user.role),
        body=comment.body,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
    )


def list_comments(
    session: Session,
    current_user: User,
    report_id: int,
) -> list[CommentRead]:
    """
    List comments on a report ordered oldest-first (FR-20, AC-10).
    - Researchers see ONLY public comments (`is_internal == False`) on their own reports.
    - Analysts and Admins see both public comments and internal notes.
    """
    # Enforces 404 if report does not exist or belongs to a different researcher
    report = get_report_for_user(session, current_user, report_id)

    statement = select(Comment).where(Comment.report_id == report.id)

    # CRITICAL CONFIDENTIALITY RULE (FR-20 & AC-10):
    # Filter out internal analyst notes at the database query level when the caller is a Researcher
    if current_user.role == UserRole.RESEARCHER.value:
        statement = statement.where(Comment.is_internal == False)  # noqa: E712

    statement = statement.order_by(Comment.created_at.asc(), Comment.id.asc())  # type: ignore[attr-defined]
    comments = session.exec(statement).all()

    # Load author names and roles in a single batch query
    author_ids = {c.author_id for c in comments}
    authors_by_id: dict[int, User] = {}
    if author_ids:
        users = session.exec(select(User).where(User.id.in_(author_ids))).all()  # type: ignore[union-attr]
        authors_by_id = {u.id: u for u in users if u.id is not None}

    result: list[CommentRead] = []
    for c in comments:
        author = authors_by_id.get(c.author_id)
        result.append(
            CommentRead(
                id=c.id,  # type: ignore[arg-type]
                report_id=c.report_id,
                author_id=c.author_id,
                author_name=author.name if author else None,
                author_role=UserRole(author.role) if author else None,
                body=c.body,
                is_internal=c.is_internal,
                created_at=c.created_at,
            )
        )
    return result