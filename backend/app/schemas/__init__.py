"""
Pydantic Request & Response Schemas Package (backend/app/schemas/__init__.py)
=====================================================================
WHAT THIS FILE DOES:
Re-exports all Pydantic schema classes (`report`, `triage`, `comment`) so routers and services
can import them from `app.schemas`.
=====================================================================
"""

from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.report import (
    DemoUserRead,
    ReportCreate,
    ReportListResponse,
    ReportRead,
    ReportUpdate,
)
from app.schemas.triage import SeverityUpdate, StatusHistoryRead, StatusUpdate

__all__ = [
    "CommentCreate",
    "CommentRead",
    "DemoUserRead",
    "ReportCreate",
    "ReportListResponse",
    "ReportRead",
    "ReportUpdate",
    "SeverityUpdate",
    "StatusHistoryRead",
    "StatusUpdate",
]