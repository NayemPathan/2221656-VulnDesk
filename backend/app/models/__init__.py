"""
Models Package Initializer (backend/app/models/__init__.py)
=====================================================================
WHAT THIS FILE DOES:
Re-exports all SQLModel table classes (`User`, `Report`, `Comment`, `StatusHistory`) and Enums
from a single place: `from app.models import User, Report, ...`.

WHY THIS IS CRITICAL FOR ALEMBIC & SQLMODEL:
SQLModel only registers a table in `SQLModel.metadata` when the Python file defining that class
is imported! By importing all four models here, any script that runs `import app.models` (such as
`alembic/env.py` or `database.py`) automatically discovers all four tables.
=====================================================================
"""

from app.models.comment import Comment
from app.models.enums import ReportStatus, Severity, UserRole
from app.models.report import Report
from app.models.status_history import StatusHistory
from app.models.user import User

__all__ = [
    "Comment",
    "Report",
    "ReportStatus",
    "Severity",
    "StatusHistory",
    "User",
    "UserRole",
]
