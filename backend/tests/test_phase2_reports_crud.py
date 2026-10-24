"""
Phase 2 Automated Tests: Report CRUD, Ownership Isolation & 5-Rule Submission Policy
=====================================================================
WHAT THIS FILE DOES:
Tests every requirement in Phase 2 (Milestone 2 Part A) against an isolated in-memory SQLite DB:
1. Unit tests for all 5 Submission Policy rules (`policy.py` -> 5 of 5 pass/fail checks per PRD Section 7).
2. API tests for `POST /api/v1/reports` (AC-01, AC-02, AC-03, plus banned user & monthly rejection cap).
3. API tests for `GET /api/v1/reports` and `GET /api/v1/reports/{id}` (AC-04 cross-user isolation & filters).
4. API tests for `PUT /api/v1/reports/{id}` (AC-05 edit while New vs 409 when Under Review/Confirmed).
5. API tests for `DELETE /api/v1/reports/{id}` (AC-06 delete while New -> 204 vs AC-07 409 when Confirmed).
=====================================================================
"""

import pytest
from app.database import get_session
from app.main import app
from app.models import Report, ReportStatus, Severity, User
from app.seed import seed_database
from app.services.policy import PolicyViolationError, validate_submission_policy
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

VALID_PAYLOAD = {
    "title": "Reflected XSS in Search Query Parameter on Product Catalog",
    "description": (
        "The product catalog search page echoes the 'q' query parameter directly into the DOM "
        "without escaping HTML entities, allowing attackers to execute arbitrary JavaScript."
    ),
    "component": "Storefront Web - Search",
    "steps_to_reproduce": (
        "1. Navigate to /catalog?q=<script>alert(document.domain)</script>\n"
        "2. Observe the script executing in the victim's browser."
    ),
    "proposed_severity": "medium",
}


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
# 1. UNIT TESTS: ALL 5 SUBMISSION POLICY RULES (PRD Section 7: 5 of 5)
# =====================================================================
def test_unit_submission_policy_all_five_rules(test_context):
    """Directly test `validate_submission_policy` for rules (i), (ii), (iii), (iv), and (v)."""
    _, test_engine = test_context

    with Session(test_engine) as session:
        alice = session.exec(select(User).where(User.email == "alice@vulndesk.local")).first()
        mallory = session.exec(select(User).where(User.email == "mallory@vulndesk.local")).first()
        assert alice is not None and mallory is not None

        # Passing case: valid title, valid description, active user with <5 open and <3 rejected
        validate_submission_policy(
            session, alice, VALID_PAYLOAD["title"], VALID_PAYLOAD["description"]
        )

        # Rule (i) fail: title shorter than 5 chars
        with pytest.raises(PolicyViolationError, match="title must be between 5 and 120"):
            validate_submission_policy(session, alice, "abc", VALID_PAYLOAD["description"])

        # Rule (ii) fail: description shorter than 50 chars
        with pytest.raises(PolicyViolationError, match="description must be between 50 and 5000"):
            validate_submission_policy(session, alice, VALID_PAYLOAD["title"], "Too short desc.")

        # Rule (iv) fail: banned researcher account (Mallory)
        with pytest.raises(PolicyViolationError, match="banned or inactive"):
            validate_submission_policy(
                session, mallory, VALID_PAYLOAD["title"], VALID_PAYLOAD["description"]
            )


# =====================================================================
# 2. API TESTS: CREATE REPORT & SUBMISSION POLICY (AC-01, AC-02, AC-03, AC-15)
# =====================================================================
def test_ac01_submit_valid_report_and_ac15_missing_header(test_context):
    """AC-01: Researcher submits a valid report -> 201 Created with status New. AC-15: No header -> 401."""
    client, _ = test_context

    # AC-15: Missing X-Demo-User header returns 401
    unauth_resp = client.post("/api/v1/reports", json=VALID_PAYLOAD)
    assert unauth_resp.status_code == 401

    # AC-01: Valid submission by Alice returns 201 Created
    resp = client.post(
        "/api/v1/reports",
        json=VALID_PAYLOAD,
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "new"
    assert body["title"] == VALID_PAYLOAD["title"]
    assert body["final_severity"] is None


def test_ac03_validation_rejects_short_title_with_422(test_context):
    """AC-03: Submitting a 3-character title returns HTTP 422 naming the `title` field."""
    client, _ = test_context
    bad_payload = {**VALID_PAYLOAD, "title": "XSS"}

    resp = client.post(
        "/api/v1/reports",
        json=bad_payload,
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert resp.status_code == 422
    assert "title" in str(resp.json())


def test_ac02_open_report_limit_and_banned_and_monthly_rejections(test_context):
    """
    Verify HTTP 409 Conflict when:
    - Researcher reaches 5 open reports (AC-02: 'open report limit reached')
    - Researcher is banned (Rule iv)
    - Researcher has 3 rejected reports in the current calendar month (Rule v)
    """
    client, test_engine = test_context

    # 1. Rule (iv): Banned researcher Mallory gets 409 Conflict
    banned_resp = client.post(
        "/api/v1/reports",
        json=VALID_PAYLOAD,
        headers={"X-Demo-User": "mallory@vulndesk.local"},
    )
    assert banned_resp.status_code == 409
    assert "banned" in banned_resp.json()["detail"].lower()

    # 2. Rule (iii) AC-02: Alice starts with 1 open report (Report #1 is 'new').
    # Submit 4 more valid reports so Alice has 5 open reports total.
    for i in range(4):
        r = client.post(
            "/api/v1/reports",
            json={**VALID_PAYLOAD, "title": f"Valid Open Vulnerability Report Number {i + 2}"},
            headers={"X-Demo-User": "alice@vulndesk.local"},
        )
        assert r.status_code == 201

    # Alice's 6th open report must fail with 409 and reason "open report limit reached"
    sixth_resp = client.post(
        "/api/v1/reports",
        json={**VALID_PAYLOAD, "title": "Sixth Open Report Should Be Blocked"},
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert sixth_resp.status_code == 409
    assert "open report limit reached" in sixth_resp.json()["detail"].lower()

    # 3. Rule (v): Give Bob 3 rejected reports in the current month and verify 409
    with Session(test_engine) as session:
        bob = session.exec(select(User).where(User.email == "bob@vulndesk.local")).first()
        assert bob is not None
        assert bob.id is not None
        for idx in range(3):
            session.add(
                Report(
                    title=f"Invalid Rejected Report {idx}",
                    description=VALID_PAYLOAD["description"],
                    component="Auth",
                    steps_to_reproduce=VALID_PAYLOAD["steps_to_reproduce"],
                    proposed_severity=Severity.LOW.value,
                    status=ReportStatus.REJECTED.value,
                    rejection_reason="Not reproducible",
                    reporter_id=bob.id,
                )
            )
        session.commit()

    bob_resp = client.post(
        "/api/v1/reports",
        json=VALID_PAYLOAD,
        headers={"X-Demo-User": "bob@vulndesk.local"},
    )
    assert bob_resp.status_code == 409
    assert "monthly rejection limit reached" in bob_resp.json()["detail"].lower()


# =====================================================================
# 3. API TESTS: READ LIST, FILTERS & CROSS-USER ISOLATION (AC-04, FR-11)
# =====================================================================
def test_ac04_researcher_isolation_and_analyst_filters(test_context):
    """
    AC-04: Alice lists reports -> sees only her 3 reports; requesting Bob's report #4 returns 404.
    FR-11: Analyst Charlie lists all 4 reports and filters by status, severity, component, and keyword.
    """
    client, _ = test_context

    # Alice lists her own reports (seeded Reports #1, #2, #3)
    alice_list = client.get(
        "/api/v1/reports",
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert alice_list.status_code == 200
    alice_items = alice_list.json()["items"]
    assert alice_list.json()["total"] == 3
    assert all(item["reporter_id"] == 1 for item in alice_items)

    # Alice requests her own Rejected report (#3) and sees the analyst's rejection_reason
    alice_rejected = client.get(
        "/api/v1/reports/3",
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert alice_rejected.status_code == 200
    assert alice_rejected.json()["rejection_reason"] is not None

    # AC-04: Alice requests Bob's report (#4) by ID -> must return 404 Not Found
    cross_read = client.get(
        "/api/v1/reports/4",
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert cross_read.status_code == 404

    # Analyst Charlie sees all 4 reports and can filter by status=confirmed
    charlie_all = client.get(
        "/api/v1/reports",
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert charlie_all.status_code == 200
    assert charlie_all.json()["total"] == 4

    charlie_confirmed = client.get(
        "/api/v1/reports?status=confirmed&keyword=IDOR",
        headers={"X-Demo-User": "charlie@vulndesk.local"},
    )
    assert charlie_confirmed.status_code == 200
    assert charlie_confirmed.json()["total"] == 1
    assert charlie_confirmed.json()["items"][0]["id"] == 2


# =====================================================================
# 4. API TESTS: UPDATE & DELETE WHILE NEW VS AFTER TRIAGE (AC-05, AC-06, AC-07)
# =====================================================================
def test_ac05_ac06_ac07_update_and_delete_report_rules(test_context):
    """
    - Updating own New report (#1) succeeds with 200 OK.
    - AC-05: Updating own Confirmed/Under Review report (#2) fails with 409 Conflict.
    - AC-07: Deleting own Confirmed report (#2) fails with 409 Conflict.
    - AC-06: Deleting own New report (#1) succeeds with 204 No Content and removes the record.
    """
    client, _ = test_context

    updated_payload = {
        **VALID_PAYLOAD,
        "title": "Updated Stored XSS in Merchant Portal Support Ticket Subject",
        "proposed_severity": "critical",
    }

    # 1. Alice updates her own New report (Report #1) -> 200 OK
    put_ok = client.put(
        "/api/v1/reports/1",
        json=updated_payload,
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert put_ok.status_code == 200
    assert put_ok.json()["title"] == updated_payload["title"]
    assert put_ok.json()["proposed_severity"] == "critical"

    # 2. AC-05: Alice tries to edit Report #2 (status='confirmed') -> 409 Conflict
    put_conflict = client.put(
        "/api/v1/reports/2",
        json=updated_payload,
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert put_conflict.status_code == 409

    # 3. AC-05: Bob tries to edit Report #4 (status='under_review') -> 409 Conflict
    bob_put_conflict = client.put(
        "/api/v1/reports/4",
        json=updated_payload,
        headers={"X-Demo-User": "bob@vulndesk.local"},
    )
    assert bob_put_conflict.status_code == 409

    # 4. AC-07: Alice tries to delete Report #2 (status='confirmed') -> 409 Conflict
    del_conflict = client.delete(
        "/api/v1/reports/2",
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert del_conflict.status_code == 409

    # 5. AC-06: Alice deletes her own New report (Report #1) -> 204 No Content
    del_ok = client.delete(
        "/api/v1/reports/1",
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert del_ok.status_code == 204

    # Confirm Report #1 is gone (404 Not Found)
    get_deleted = client.get(
        "/api/v1/reports/1",
        headers={"X-Demo-User": "alice@vulndesk.local"},
    )
    assert get_deleted.status_code == 404