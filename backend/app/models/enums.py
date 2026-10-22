"""
Domain Enumerations (backend/app/models/enums.py)
=====================================================================
WHAT THIS FILE DOES:
Defines fixed sets of allowed string values (Enums) for User Roles, Vulnerability Severities,
and Report Workflow Statuses.

WHY WE WROTE IT THIS WAY:
1. Prevents Typos: Instead of scattering magic strings like `"under_review"` across 10 files
   (where a typo like `"under-review"` would cause bugs), we use `ReportStatus.UNDER_REVIEW`.
2. Automatic API Validation (SRS Section 7): Inheriting from `(str, Enum)` means FastAPI and
   Pydantic automatically validate incoming JSON against these exact choices and return HTTP 422
   if someone sends an invalid role, severity, or status!
=====================================================================
"""

from enum import Enum


class UserRole(str, Enum):
    """
    Global roles in VulnDesk (SRS Section 2).
    Each user holds exactly one role.
    """
    RESEARCHER = "researcher"  # Submits vulnerability reports and views/edits own New reports
    ANALYST = "analyst"        # Triages all reports, sets final severity, changes status, adds internal notes
    ADMIN = "admin"            # Manages users, reopens end-state reports, views system statistics


class Severity(str, Enum):
    """
    Vulnerability severity levels (SRS Section 7).
    Used for both `proposed_severity` (set by Researcher) and `final_severity` (set by Analyst).
    """
    LOW = "low"            # 10-day first-response deadline
    MEDIUM = "medium"      # 5-day first-response deadline
    HIGH = "high"          # 2-day first-response deadline
    CRITICAL = "critical"  # 1-day first-response deadline


class ReportStatus(str, Enum):
    """
    Report lifecycle states (SRS Section 4 State Diagram).
    - Initial state: NEW
    - Active triage state: UNDER_REVIEW
    - Post-triage states: CONFIRMED -> FIXED -> CLOSED
    - Alternative end states: REJECTED, DUPLICATE
    """
    NEW = "new"
    UNDER_REVIEW = "under_review"
    CONFIRMED = "confirmed"
    FIXED = "fixed"
    CLOSED = "closed"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
