"""
Phase 8 Automated Tests: RBAC Scope Guards & Admin User Governance
=====================================================================
"""

import pytest
from app.database import get_session
from app.main import app
from app.seed import DEFAULT_DEMO_PASSWORD, TUTOR_DEFAULT_PASSWORD, seed_database
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


def _login_bearer(client: TestClient, email: str, password: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_rbac_blocks_researcher_and_analyst_from_admin_routes(test_client: TestClient):
    """Researchers and Analysts lack `admin:users` scope and must receive 403 Forbidden."""
    alice_headers = _login_bearer(test_client, "alice@vulndesk.local", DEFAULT_DEMO_PASSWORD)
    charlie_headers = _login_bearer(test_client, "charlie@vulndesk.local", DEFAULT_DEMO_PASSWORD)

    r1 = test_client.get("/api/v1/admin/users", headers=alice_headers)
    assert r1.status_code == 403
    assert "admin:users" in r1.json()["detail"]

    r2 = test_client.get("/api/v1/admin/users", headers=charlie_headers)
    assert r2.status_code == 403
    assert "admin:users" in r2.json()["detail"]


def test_admin_crud_ban_revokes_tokens_and_soft_delete(test_client: TestClient):
    """Admin creates a user, changes role, bans (revoking active session), unbans, and soft-deletes."""
    admin_headers = _login_bearer(test_client, "tutor@vulndesk.local", TUTOR_DEFAULT_PASSWORD)

    # 1. Admin lists all 6 seeded users
    list_resp = test_client.get("/api/v1/admin/users", headers=admin_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 6

    # 2. Admin creates a new Security Analyst
    create_resp = test_client.post(
        "/api/v1/admin/users",
        json={
            "name": "Zara Security",
            "email": "zara@vulndesk.local",
            "password": "ZaraStrongPass123!",
            "role": "analyst",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    zara_id = create_resp.json()["id"]
    assert create_resp.json()["role"] == "analyst"

    # 3. Zara logs in (receives refresh cookie)
    zara_login = test_client.post(
        "/api/v1/auth/login",
        json={"email": "zara@vulndesk.local", "password": "ZaraStrongPass123!"},
    )
    assert zara_login.status_code == 200
    zara_cookie = zara_login.cookies.get("vulndesk_refresh_token")
    assert zara_cookie is not None

    # 4. Admin bans Zara -> Zara's active refresh token is immediately revoked
    ban_resp = test_client.patch(
        f"/api/v1/admin/users/{zara_id}/ban",
        json={"is_banned": True},
        headers=admin_headers,
    )
    assert ban_resp.status_code == 200
    assert ban_resp.json()["is_banned"] is True

    zara_refresh = test_client.post(
        "/api/v1/auth/refresh",
        cookies={"vulndesk_refresh_token": zara_cookie},
    )
    assert zara_refresh.status_code == 401

    # 5. Admin unbans Zara and updates her role to researcher
    unban_resp = test_client.patch(
        f"/api/v1/admin/users/{zara_id}/ban",
        json={"is_banned": False},
        headers=admin_headers,
    )
    assert unban_resp.status_code == 200 and unban_resp.json()["is_banned"] is False

    role_resp = test_client.patch(
        f"/api/v1/admin/users/{zara_id}/role",
        json={"role": "researcher"},
        headers=admin_headers,
    )
    assert role_resp.status_code == 200 and role_resp.json()["role"] == "researcher"

    # 6. Admin cannot ban or delete themselves (409 Conflict)
    tutor_id = next(u["id"] for u in list_resp.json() if u["email"] == "tutor@vulndesk.local")
    self_ban = test_client.patch(
        f"/api/v1/admin/users/{tutor_id}/ban",
        json={"is_banned": True},
        headers=admin_headers,
    )
    assert self_ban.status_code == 409

    # 7. Admin soft-deletes Zara -> 204 No Content, hidden from default list, visible with include_deleted=true
    del_resp = test_client.delete(f"/api/v1/admin/users/{zara_id}", headers=admin_headers)
    assert del_resp.status_code == 204

    after_del = test_client.get("/api/v1/admin/users", headers=admin_headers)
    assert all(u["id"] != zara_id for u in after_del.json())

    with_deleted = test_client.get(
        "/api/v1/admin/users?include_deleted=true", headers=admin_headers
    )
    assert any(u["id"] == zara_id and u["is_deleted"] is True for u in with_deleted.json())
