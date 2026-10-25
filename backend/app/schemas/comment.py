"""
Comment & Internal Note Pydantic Schemas (backend/app/schemas/comment.py)
=====================================================================
WHAT THIS FILE DOES:
Defines the request and response schemas for Report Comments and Analyst Internal Notes:
1. `CommentCreate` (`POST /api/v1/reports/{id}/comments` — FR-18, FR-19)
2. `CommentRead`   (`GET  /api/v1/reports/{id}/comments` — FR-20, AC-10)

WHY WE WROTE IT THIS WAY (SRS Section 7 & FR-18..FR-20):
1. Character Length Validation: `body` must be 1 to 2,000 characters after stripping whitespace.
   Empty strings or >2,000 character payloads are rejected automatically with HTTP 422.
2. `is_internal` Flag: Defaults to `False` (public comment visible to the reporting Researcher
   and all Analysts). Only an Analyst is allowed to set `is_internal=True` (enforced in
   `comment_service.py`), and internal notes are filtered out when Researchers fetch comments.
3. Enriched Author Info (`author_name`, `author_role`): Included in `CommentRead` so the React
   discussion thread can display who wrote each comment and badge their role (`researcher` vs `analyst`).
=====================================================================
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import UserRole


class CommentCreate(BaseModel):
    """Request body schema for `POST /api/v1/reports/{id}/comments` (FR-18, FR-19)."""

    body: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Comment text (1 to 2,000 characters).",
        examples=["We have reproduced this issue on staging and are preparing a hotfix."],
    )
    is_internal: bool = Field(
        default=False,
        description="If true, creates an analyst-only internal note hidden from the researcher (FR-19).",
        examples=[False],
    )

    @field_validator("body", mode="before")
    @classmethod
    def _strip_body(cls, value: str) -> str:
        """Strip leading and trailing whitespace so blank spaces cannot bypass min_length=1."""
        if isinstance(value, str):
            return value.strip()
        return value


class CommentRead(BaseModel):
    """Response schema for a single comment or internal note (`GET /reports/{id}/comments`)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    author_id: int
    author_name: str | None = None
    author_role: UserRole | None = None
    body: str
    is_internal: bool
    created_at: datetime