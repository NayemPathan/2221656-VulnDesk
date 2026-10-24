"""
Report Pydantic Schemas (backend/app/schemas/report.py)
=====================================================================
WHAT THIS FILE DOES:
Defines the Pydantic models used to validate incoming JSON request bodies (`ReportCreate`,
`ReportUpdate`) and format outgoing JSON responses (`ReportRead`, `ReportListResponse`,
`DemoUserRead`).

WHY WE SEPARATE SCHEMAS FROM DATABASE MODELS (TDD Section 3):
1. Security: A client should never be able to send `"status": "confirmed"` or `"reporter_id": 99`
   when creating a report! `ReportCreate` only accepts the 5 fields a researcher is allowed to submit.
2. Input Validation (SRS Section 7 & AC-03):
   - `title`: 5 to 120 characters (`Field(min_length=5, max_length=120)`)
   - `description`: 50 to 5,000 characters (`Field(min_length=50, max_length=5000)`)
   - `component`: 1 to 100 characters (`Field(min_length=1, max_length=100)`)
   - `steps_to_reproduce`: 10 to 5,000 characters (`Field(min_length=10, max_length=5000)`)
   - `proposed_severity`: must be one of `low`, `medium`, `high`, `critical` (`Severity` enum)
   If any field fails these bounds, FastAPI automatically returns HTTP `422 Unprocessable Entity`
   naming the offending field (satisfying AC-03)!
=====================================================================
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ReportStatus, Severity, UserRole


class ReportCreate(BaseModel):
    """Request body schema for `POST /api/v1/reports` (FR-07, FR-08, SRS Section 7)."""

    title: str = Field(
        ...,
        min_length=5,
        max_length=120,
        description="Short summary of the vulnerability (5 to 120 characters).",
        examples=["Stored XSS in Customer Support Ticket Subject"],
    )
    description: str = Field(
        ...,
        min_length=50,
        max_length=5000,
        description="Detailed explanation of the vulnerability and its impact (50 to 5,000 characters).",
        examples=[
            ("When submitting a support ticket on the merchant portal, the subject field is rendered "
            "without HTML entity encoding in the agent dashboard, allowing arbitrary JavaScript execution.")
        ],
    )
    component: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Affected product, service, or module (1 to 100 characters).",
        examples=["Merchant Portal - Support Module"],
    )
    steps_to_reproduce: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Step-by-step instructions to reproduce the issue (10 to 5,000 characters).",
        examples=[
            ("1. Log into Merchant Portal.\n2. Open New Support Ticket.\n"
            "3. Enter <script>alert(1)</script> in Subject and submit.")
        ],
    )
    proposed_severity: Severity = Field(
        ...,
        description="Researcher's proposed severity: low, medium, high, or critical.",
        examples=[Severity.HIGH],
    )

    @field_validator("title", "description", "component", "steps_to_reproduce", mode="before")
    @classmethod
    def _strip_whitespace(cls, value: str) -> str:
        """Strip leading/trailing whitespace before checking character length limits."""
        if isinstance(value, str):
            return value.strip()
        return value


class ReportUpdate(BaseModel):
    """
    Request body schema for `PUT /api/v1/reports/{id}` (FR-10a).
    Allows a researcher to update their own report while its status is still `New`.
    """

    title: str = Field(..., min_length=5, max_length=120)
    description: str = Field(..., min_length=50, max_length=5000)
    component: str = Field(..., min_length=1, max_length=100)
    steps_to_reproduce: str = Field(..., min_length=10, max_length=5000)
    proposed_severity: Severity

    @field_validator("title", "description", "component", "steps_to_reproduce", mode="before")
    @classmethod
    def _strip_whitespace(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


class ReportRead(BaseModel):
    """Response schema representing a single vulnerability report (`GET /reports/{id}`, etc.)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    component: str
    steps_to_reproduce: str
    proposed_severity: Severity
    final_severity: Severity | None = None
    status: ReportStatus
    rejection_reason: str | None = None
    reporter_id: int
    duplicate_of_id: int | None = None
    first_responder_id: int | None = None
    first_response_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReportListResponse(BaseModel):
    """Paginated response schema for `GET /api/v1/reports` (FR-11)."""

    items: list[ReportRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class DemoUserRead(BaseModel):
    """Response schema for `GET /api/v1/reports/demo-users` (helps UI role switcher)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    is_banned: bool