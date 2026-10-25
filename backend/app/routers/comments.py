"""
Comments & Internal Notes Router (backend/app/routers/comments.py)
=====================================================================
WHAT THIS FILE DOES:
Exposes the HTTP REST endpoints for Report Comments & Internal Notes under `/api/v1/reports`:
  - `POST /api/v1/reports/{report_id}/comments` -> Add a comment or analyst internal note (201 Created)
  - `GET  /api/v1/reports/{report_id}/comments` -> List comments chronologically (200 OK)
=====================================================================
"""

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.database import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas.comment import CommentCreate, CommentRead
from app.services import comment_service

router = APIRouter(prefix="/reports", tags=["comments"])


@router.post(
    "/{report_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment or analyst-only internal note to a report",
)
def add_comment(
    report_id: int,
    payload: CommentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CommentRead:
    """
    Post a comment on a report (FR-18, FR-19).
    - Researchers can post public comments (`is_internal=False`) on their own reports.
    - Analysts can post public comments or private internal notes (`is_internal=True`) on any report.
    """
    return comment_service.create_comment(session, current_user, report_id, payload)


@router.get(
    "/{report_id}/comments",
    response_model=list[CommentRead],
    summary="List comments on a report (internal notes hidden from researchers)",
)
def get_comments(
    report_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[CommentRead]:
    """
    List comments on a report ordered oldest-first (FR-20, AC-10).
    Internal analyst notes (`is_internal=True`) are automatically omitted when called by a Researcher.
    """
    return comment_service.list_comments(session, current_user, report_id)