"""
Triage & Status History Pydantic Schemas (backend/app/schemas/triage.py)
=====================================================================
WHAT THIS FILE DOES:
Defines the request and response schemas for the Analyst Triage workflow and Status History:
1. `SeverityUpdate` (`PATCH /api/v1/reports/{id}/severity` — FR-12)
2. `StatusUpdate`   (`PATCH /api/v1/reports/{id}/status`   — FR-13, FR-14)
3. `StatusHistoryRead` (`GET /api/v1/reports/{id}/history` — FR-15)

WHY WE WROTE IT THIS WAY:
- Strict Enum Validation: `final_severity` must be a valid `Severity` (`low`, `medium`, `high`,
  `critical`) and `status` must be a valid `ReportStatus`. Invalid strings automatically trigger
  HTTP `422 Unprocessable Entity`.
- Conditional Triage Fields (`FR-14`):
  - `rejection_reason`: Optional on the schema (up to 1,000 chars), but enforced as mandatory by
    `triage_service.py` whenever `status == "rejected"` (returning HTTP `409 Conflict` if omitted).
  - `duplicate_of_id`: Optional on the schema, but enforced as mandatory by `triage_service.py`
    whenever `status == "duplicate"` (returning HTTP `409 Conflict` if omitted or invalid).
=====================================================================
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ReportStatus, Severity


class SeverityUpdate(BaseModel):
    """Request body schema for `PATCH /api/v1/reports/{id}/severity` (FR-12)."""

    final_severity: Severity = Field(
        ...,
        description="Official severity assigned by the security analyst: low, medium, high, or critical.",
        examples=[Severity.HIGH],
    )


class StatusUpdate(BaseModel):
    """
    Request body schema for `PATCH /api/v1/reports/{id}/status` (FR-13, FR-14).
    - Moving to `rejected` requires `rejection_reason`.
    - Moving to `duplicate` requires `duplicate_of_id`.
    - Moving to `confirmed` requires the report to already have `final_severity` set.
    """

    status: ReportStatus = Field(
        ...,
        description="Target workflow status (e.g. under_review, confirmed, fixed, closed, rejected, duplicate).",
        examples=[ReportStatus.UNDER_REVIEW],
    )
    rejection_reason: str | None = Field(
        default=None,
        max_length=1000,
        description="Required when transitioning status to 'rejected' (1 to 1,000 characters).",
        examples=["Cannot reproduce on production; rate limiting is enforced by Cloudflare WAF."],
    )
    duplicate_of_id: int | None = Field(
        default=None,
        ge=1,
        description="Required when transitioning status to 'duplicate'; must reference an existing Report ID.",
        examples=[1],
    )

    @field_validator("rejection_reason", mode="before")
    @classmethod
    def _strip_rejection_reason(cls, value: str | None) -> str | None:
        """Strip leading/trailing whitespace from rejection_reason if provided."""
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return value


class StatusHistoryRead(BaseModel):
    """Response schema for a single append-only status history record (`GET /reports/{id}/history`)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    changed_by: int
    changed_by_name: str | None = None
    from_status: ReportStatus
    to_status: ReportStatus
    changed_at: datetime