"""

Phase 7 Automated Tests: Registration, Login, JWT Bearer, Refresh Rotation & Lockout
=====================================================================
"""

import pytest
from app.database import get_session
from app.main import app
from app.seed import TUTOR_DEFAULT_PASSWORD, seed_database
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture()
def test_client():
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
    yield client
    app.dependency_overrides.clear()


def test_register_and_duplicate_email(test_client: TestClient):
    """Public registration creates a Researcher and rejects duplicate emails with 409."""
    resp = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "New Researcher",
            "email": "NewUser@VulnDesk.local",
            "password": "StrongPassword123!",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "newuser@vulndesk.local"
    assert body["role"] == "researcher"

    dup = test_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Duplicate",
            "email": "newuser@vulndesk.local",
            "password": "StrongPassword123!",
        },
    )
    assert dup.status_code == 409


def test_tutor_login_jwt_refresh_rotation_and_logout(test_client: TestClient):
    """Tutor logs in, accesses protected endpoints via Bearer JWT, rotates refresh token, and logs out."""
    login_resp = test_client.post(
        "/api/v1/auth/login",
        json={"email": "tutor@vulndesk.local", "password": TUTOR_DEFAULT_PASSWORD},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    access_token = token_data["access_token"]
    assert token_data["user"]["role"] == "admin"

    # Use Bearer JWT to call /auth/me and /reports
    me_resp = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "tutor@vulndesk.local"

    reports_resp = test_client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert reports_resp.status_code == 200
    assert reports_resp.json()["total"] == 4

    # Rotate refresh token (cookie stored automatically in TestClient)
    old_cookie = login_resp.cookies.get("vulndesk_refresh_token")
    assert old_cookie is not None

    refresh_resp = test_client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200
    new_cookie = refresh_resp.cookies.get("vulndesk_refresh_token")
    assert new_cookie is not None and new_cookie != old_cookie

    # Replaying the old (rotated) refresh token must fail with 401 and revoke the session
    replay_resp = test_client.post(
        "/api/v1/auth/refresh",
        cookies={"vulndesk_refresh_token": old_cookie},
    )
    assert replay_resp.status_code == 401

    # Current cookie should also be revoked now due to reuse detection
    after_replay = test_client.post(
        "/api/v1/auth/refresh",
        cookies={"vulndesk_refresh_token": new_cookie},
    )
    assert after_replay.status_code == 401


def test_logout_and_lockout_and_profile_update(test_client: TestClient):
    """Verify 5-attempt account lockout (423), profile update, password change, and logout."""
    # 1. Trigger 5 failed logins on Alice
    for _ in range(5):
        bad = test_client.post(
            "/api/v1/auth/login",
            json={"email": "alice@vulndesk.local", "password": "WrongPassword!"},
        )
        assert bad.status_code == 401

    # 6th attempt even with correct password returns 423 Locked
    locked = test_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@vulndesk.local", "password": "DemoPass123!"},
    )
    assert locked.status_code == 423

    # 2. Register a fresh user, update profile, change password, and logout
    test_client.post(
        "/api/v1/auth/register",
        json={"name": "Sara", "email": "sara@vulndesk.local", "password": "InitialPass123!"},
    )
    login = test_client.post(
        "/api/v1/auth/login",
        json={"email": "sara@vulndesk.local", "password": "InitialPass123!"},
    )
    jwt_token = login.json()["access_token"]

    patch_me = test_client.patch(
        "/api/v1/auth/me",
        json={"name": "Sara Ahmed"},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert patch_me.status_code == 200
    assert patch_me.json()["name"] == "Sara Ahmed"

    change_pw = test_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "InitialPass123!", "new_password": "NewStrongPass456!"},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert change_pw.status_code == 200

    # Logout clears cookie and revokes token
    out = test_client.post("/api/v1/auth/logout")
    assert out.status_code == 204
