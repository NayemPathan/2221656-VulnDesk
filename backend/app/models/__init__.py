"""
Models Package Initializer (backend/app/models/__init__.py)
=====================================================================
Re-exports all SQLModel table classes and Enums so Alembic and SQLModel
discover every table automatically.
=====================================================================
"""

from app.models.audit_log import AuditLog
from app.models.comment import Comment
from app.models.enums import ReportStatus, Severity, UserRole
from app.models.group import Group, GroupMember
from app.models.refresh_token import RefreshToken
from app.models.report import Report
from app.models.status_history import StatusHistory
from app.models.user import User

__all__ = [
    "AuditLog",
    "Comment",
    "Group",
    "GroupMember",
    "RefreshToken",
    "Report",
    "ReportStatus",
    "Severity",
    "StatusHistory",
    "User",
    "UserRole",
]