"""
Phase 9 Automated Tests: SLA Overdue Calculation & Role-Scoped Dashboard Summary
=====================================================================
"""

from datetime import UTC, datetime, timedelta

import pytest
from app.database import get_session
from app.main import app
from app.models import Report, ReportStatus, Severity, User
from app.seed import DEFAULT_DEMO_PASSWORD, TUTOR_DEFAULT_PASSWORD, seed_database
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select


@pytest.fixture()
def test_context():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _enable_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        seed_database(session)

    def override_get_session():
        with Session(eng) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    yield client, eng
    app.dependency_overrides.clear()


def _login_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_sla_overdue_flag_and_clears_on_triage(test_context):
    """Critical New report older than 1 day is overdue; moving to under_review clears overdue."""
    client, eng = test_context
    charlie_headers = _login_headers(client, "charlie@vulndesk.local", DEFAULT_DEMO_PASSWORD)

    with Session(eng) as session:
        alice = session.exec(
            select(User).where(User.email == "alice@vulndesk.local")
        ).first()
        assert alice is not None
        assert alice.id is not None
        old_critical = Report(
            title="Old Critical RCE Report Past 1-Day SLA",
            description="A" * 60,
            component="Core API",
            steps_to_reproduce="1. Run PoC\n2. Observe RCE.",
            proposed_severity=Severity.CRITICAL.value,
            status=ReportStatus.NEW.value,
            reporter_id=alice.id,
            created_at=datetime.now(UTC) - timedelta(days=3),
            updated_at=datetime.now(UTC) - timedelta(days=3),
        )
        session.add(old_critical)
        session.commit()
        session.refresh(old_critical)
        rep_id = old_critical.id

    # Before triage: is_overdue is True
    get_resp = client.get(f"/api/v1/reports/{rep_id}", headers=charlie_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["is_overdue"] is True

    # Analyst moves to under_review -> first_response_at is set and is_overdue becomes False
    triage_resp = client.patch(
        f"/api/v1/reports/{rep_id}/status",
        json={"status": "under_review"},
        headers=charlie_headers,
    )
    assert triage_resp.status_code == 200
    assert triage_resp.json()["is_overdue"] is False


def test_dashboard_summary_role_scoping(test_context):
    """Researcher sees own counts; Analyst sees global counts; Admin also sees user stats."""
    client, _ = test_context

    alice_h = _login_headers(client, "alice@vulndesk.local", DEFAULT_DEMO_PASSWORD)
    charlie_h = _login_headers(client, "charlie@vulndesk.local", DEFAULT_DEMO_PASSWORD)
    tutor_h = _login_headers(client, "tutor@vulndesk.local", TUTOR_DEFAULT_PASSWORD)

    alice_sum = client.get("/api/v1/dashboard/summary", headers=alice_h).json()
    assert alice_sum["total_reports"] == 3
    assert alice_sum["total_users"] is None

    charlie_sum = client.get("/api/v1/dashboard/summary", headers=charlie_h).json()
    assert charlie_sum["total_reports"] == 4
    assert charlie_sum["avg_first_response_hours"] is not None
    assert charlie_sum["total_users"] is None

    tutor_sum = client.get("/api/v1/dashboard/summary", headers=tutor_h).json()
    assert tutor_sum["total_reports"] == 4
    assert tutor_sum["total_users"] == 6
    assert tutor_sum["banned_users"] == 1
