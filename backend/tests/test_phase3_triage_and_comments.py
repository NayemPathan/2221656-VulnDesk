"""
Phase 3 Automated Tests: Analyst Triage Workflow, Status History & Comments/Internal Notes
=====================================================================
WHAT THIS FILE DOES:
Verifies all Milestone 2 Part B (Phase 3) requirements in an isolated in-memory SQLite database:
1. `test_ac08_confirm_requires_final_severity_and_full_triage_lifecycle`:
   - Researchers cannot assign severity or change status (403 Forbidden).
   - Moving out of `new` sets `first_responder_id` and `first_response_at`.
   - AC-08: Moving to `confirmed` without `final_severity` fails with 409 ("final severity required").
   - Assigning `final_severity` and stepping through `under_review -> confirmed -> fixed -> closed` succeeds.
   - Analysts cannot reopen `closed` reports (409), while Admins can reopen `closed -> under_review` (FR-16).
   - Every transition is atomically recorded in `GET /api/v1/reports/{id}/history` (FR-15, NFR-08).
2. `test_ac09_reject_requires_reason_and_duplicate_requires_valid_id`:
   - AC-09: Moving to `rejected` requires `rejection_reason` (409 if missing; saved & visible when provided).
   - FR-14: Moving to `duplicate` requires a valid, distinct `duplicate_of_id` (rejects missing, self-reference, or non-existent report ID with 409).
3. `test_ac10_comments_and_internal_notes_visibility`:
   - Researchers cannot post `is_internal=True` notes (403) and cannot access another researcher's comments (404).
   - AC-10 & FR-20: Internal analyst notes (`is_internal=True`) are visible to Analysts/Admins but completely omitted when a Researcher fetches `GET /api/v1/reports/{id}/comments`.
=====================================================================
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app
from app.seed import seed_database


@pytest.fixture()
def test_context():
    """Create a fresh seeded in-memory SQLite database and FastAPI TestClient for each test."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        seed_database(session)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    yield client, test_engine
    app.dependency_overrides.clear()


# =====================================================================
# 1. TRIAGE LIFECYCLE, AC-08 (FINAL SEVERITY REQUIRED) & STATUS HISTORY
# =====================================================================
def test_ac08_confirm_requires_final_severity_and_full_triage_lifecycle(test_context):
    """Verify state transitions, AC-08 precondition, Admin reopen, and append-only StatusHistory."""
    client, _ = test_context

    # 1. Researcher Alice cannot assign severity or change status -> 403 Forbidden
    res_sev = client.patch(
        "/api/v1/reports/1/severity",
        json={"final_severity": "high"},
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert res_sev.status_code == 403

    res_status = client.patch(
        "/api/v1/reports/1/status",
        json={"status": "under_review"},
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert res_status.status_code == 403

    # 2. Analyst Charlie cannot jump directly from 'new' to 'confirmed' -> 409 Conflict
    invalid_jump = client.patch(
        "/api/v1/reports/1/status",
        json={"status": "confirmed"},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert invalid_jump.status_code == 409

    # 3. Analyst Charlie moves Report #1 from 'new' -> 'under_review' -> 200 OK
    to_review = client.patch(
        "/api/v1/reports/1/status",
        json={"status": "under_review"},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert to_review.status_code == 200
    assert to_review.json()["status"] == "under_review"
    assert to_review.json()["first_responder_id"] is not None
    assert to_review.json()["first_response_at"] is not None

    # 4. AC-08: Analyst Charlie tries to move Report #1 to 'confirmed' BEFORE setting final_severity -> 409
    confirm_without_sev = client.patch(
        "/api/v1/reports/1/status",
        json={"status": "confirmed"},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert confirm_without_sev.status_code == 409
    assert "final severity required" in confirm_without_sev.json()["detail"].lower()

    # 5. Analyst Charlie assigns final_severity = 'high' -> 200 OK
    set_sev = client.patch(
        "/api/v1/reports/1/severity",
        json={"final_severity": "high"},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert set_sev.status_code == 200
    assert set_sev.json()["final_severity"] == "high"

    # 6. Now Charlie transitions Report #1: under_review -> confirmed -> fixed -> closed
    for next_status in ("confirmed", "fixed", "closed"):
        step_resp = client.patch(
            "/api/v1/reports/1/status",
            json={"status": next_status},
            headers={"X-Demo-User": "charlie@vulndesk.local"},
        )
        assert step_resp.status_code == 200
        assert step_resp.json()["status"] == next_status

    # 7. End-state enforcement (FR-16): Analyst cannot reopen 'closed' -> 409 Conflict
    analyst_reopen = client.patch(
        "/api/v1/reports/1/status",
        json={"status": "under_review"},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert analyst_reopen.status_code == 409

    # 8. Admin Nadia CAN reopen end-state 'closed' -> 'under_review' -> 200 OK
    admin_reopen = client.patch(
        "/api/v1/reports/1/status",
        json={"status": "under_review"},
        headers={"X-Demo-User": "admin@vulndesk.local"},
    )
    assert admin_reopen.status_code == 200
    assert admin_reopen.json()["status"] == "under_review"

    # 9. Verify append-only StatusHistory (FR-15, NFR-08) has all 5 transitions in chronological order
    hist_resp = client.get(
        "/api/v1/reports/1/history",
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 5
    transitions = [(h["from_status"], h["to_status"]) for h in history]
    assert transitions == [
        ("new", "under_review"),
        ("under_review", "confirmed"),
        ("confirmed", "fixed"),
        ("fixed", "closed"),
        ("closed", "under_review"),
    ]


# =====================================================================
# 2. AC-09 (REJECTION REASON) & DUPLICATE REPORT LINKING (FR-14)
# =====================================================================
def test_ac09_reject_requires_reason_and_duplicate_requires_valid_id(test_context):
    """Verify rejection_reason precondition (AC-09) and duplicate_of_id validation (FR-14)."""
    client, _ = test_context

    # 1. Rejecting Report #4 (currently 'under_review') without rejection_reason fails with 409
    reject_no_reason = client.patch(
        "/api/v1/reports/4/status",
        json={"status": "rejected"},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert reject_no_reason.status_code == 409
    assert "rejection_reason" in reject_no_reason.json()["detail"]

    # 2. AC-09: Rejecting Report #4 with a clear rejection_reason succeeds and is visible to Bob
    reason_text = "Cannot reproduce on Mobile Auth Gateway v2.4; token revocation hook is active."
    reject_ok = client.patch(
        "/api/v1/reports/4/status",
        json={"status": "rejected", "rejection_reason": reason_text},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert reject_ok.status_code == 200
    assert reject_ok.json()["status"] == "rejected"
    assert reject_ok.json()["rejection_reason"] == reason_text

    # Researcher Bob fetches his Report #4 and sees the rejection_reason
    bob_view = client.get(
        "/api/v1/reports/4",
        headers={"X-Demo-User": "bob@vulndesk.local"},
    )
    assert bob_view.status_code == 200
    assert bob_view.json()["rejection_reason"] == reason_text

    # 3. Duplicate validation on Report #1 (currently 'new'):
    # 3a. Missing duplicate_of_id -> 409
    dup_missing = client.patch(
        "/api/v1/reports/1/status",
        json={"status": "duplicate"},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert dup_missing.status_code == 409

    # 3b. Self-duplicate (duplicate_of_id == 1) -> 409
    dup_self = client.patch(
        "/api/v1/reports/1/status",
        json={"status": "duplicate", "duplicate_of_id": 1},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert dup_self.status_code == 409

    # 3c. Non-existent original report (duplicate_of_id == 999) -> 409
    dup_ghost = client.patch(
        "/api/v1/reports/1/status",
        json={"status": "duplicate", "duplicate_of_id": 999},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert dup_ghost.status_code == 409

    # 3d. Valid duplicate pointing to Report #2 -> 200 OK
    dup_ok = client.patch(
        "/api/v1/reports/1/status",
        json={"status": "duplicate", "duplicate_of_id": 2},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert dup_ok.status_code == 200
    assert dup_ok.json()["status"] == "duplicate"
    assert dup_ok.json()["duplicate_of_id"] == 2


# =====================================================================
# 3. AC-10: COMMENTS & INTERNAL ANALYST NOTES CONFIDENTIALITY
# =====================================================================
def test_ac10_comments_and_internal_notes_visibility(test_context):
    """
    Verify FR-18, FR-19, FR-20, and AC-10:
    - Researchers can comment on own reports, cannot post internal notes (403), and cannot access others' reports (404).
    - Analysts can post both public comments and internal notes (`is_internal=True`).
    - AC-10: Researchers never receive internal notes in `GET /api/v1/reports/{id}/comments`.
    """
    client, _ = test_context

    # 1. Researcher Alice tries to post an internal note -> 403 Forbidden
    alice_internal = client.post(
        "/api/v1/reports/1/comments",
        json={"body": "Trying to sneak an internal note", "is_internal": True},
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert alice_internal.status_code == 403

    # 2. Researcher Alice tries to read or post comments on Bob's Report #4 -> 404 Not Found
    alice_cross_get = client.get(
        "/api/v1/reports/4/comments",
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert alice_cross_get.status_code == 404

    alice_cross_post = client.post(
        "/api/v1/reports/4/comments",
        json={"body": "Can I comment on Bob's report?", "is_internal": False},
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert alice_cross_post.status_code == 404

    # 3. Researcher Alice posts a public comment on her Report #1 -> 201 Created
    c1 = client.post(
        "/api/v1/reports/1/comments",
        json={"body": "I also tested this payload on Firefox and Chrome.", "is_internal": False},
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert c1.status_code == 201
    assert c1.json()["is_internal"] is False

    # 4. Analyst Charlie posts an internal-only note on Report #1 -> 201 Created
    c2 = client.post(
        "/api/v1/reports/1/comments",
        json={
            "body": "INTERNAL NOTE: Confirmed unescaped template rendering in support-dashboard.tsx.",
            "is_internal": True,
        },
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert c2.status_code == 201
    assert c2.json()["is_internal"] is True

    # 5. Analyst Charlie posts a public reply on Report #1 -> 201 Created
    c3 = client.post(
        "/api/v1/reports/1/comments",
        json={"body": "Thanks Alice! We have reproduced this and scheduled a fix.", "is_internal": False},
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert c3.status_code == 201

    # 6. AC-10: Alice fetches comments on Report #1 -> sees ONLY the 2 public comments (internal note omitted!)
    alice_comments_resp = client.get(
        "/api/v1/reports/1/comments",
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert alice_comments_resp.status_code == 200
    alice_comments = alice_comments_resp.json()
    assert len(alice_comments) == 2
    assert all(c["is_internal"] is False for c in alice_comments)
    assert all("INTERNAL NOTE" not in c["body"] for c in alice_comments)

    # 7. Analyst Charlie fetches comments on Report #1 -> sees all 3 comments (including internal note)
    charlie_comments_resp = client.get(
        "/api/v1/reports/1/comments",
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert charlie_comments_resp.status_code == 200
    charlie_comments = charlie_comments_resp.json()
    assert len(charlie_comments) == 3
    assert sum(1 for c in charlie_comments if c["is_internal"]) == 1