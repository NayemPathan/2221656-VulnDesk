from app.main import app
from app.security import hash_password, verify_password
from fastapi.testclient import TestClient

client = TestClient(app)


def _login(email: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_password_pepper_hashing():
    hashed = hash_password("SecretPass123!")
    assert hashed.startswith("$argon2id$")
    assert verify_password("SecretPass123!", hashed) is True
    assert verify_password("WrongPass!", hashed) is False


def test_profile_update_and_session_revoke():
    token = _login("alice@vulndesk.local", "DemoPass123!")
    headers = {"Authorization": f"Bearer {token}"}

    # Update profile
    res = client.patch("/api/v1/auth/me", json={"name": "Alice Updated"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Alice Updated"

    # List sessions & revoke one
    sess_res = client.get("/api/v1/auth/sessions", headers=headers)
    assert sess_res.status_code == 200
    sessions = sess_res.json()
    assert len(sessions) >= 1
    current_session = next(s for s in sessions if s["is_current"])

    del_res = client.delete(
        f"/api/v1/auth/sessions/{current_session['id']}",
        headers=headers,
    )
    assert del_res.status_code == 204
    assert "Max-Age=0" in del_res.headers.get("set-cookie", "")


def test_group_permissions_and_owner_only_rules():
    alice_token = _login("alice@vulndesk.local", "DemoPass123!")
    bob_token = _login("bob@vulndesk.local", "DemoPass123!")

    # Alice creates a group
    g_res = client.post(
        "/api/v1/groups",
        json={"name": "API Pentest Group", "description": "Test group"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert g_res.status_code == 201
    group_id = g_res.json()["id"]

    # Get Bob's user id via /auth/me
    bob_id = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bob_token}"}).json()["id"]

    # Alice adds Bob with can_create=True, can_edit=False
    add_res = client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": bob_id, "can_create": True, "can_edit": False, "can_assign": False},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert add_res.status_code == 200

    # Bob CANNOT rename or delete the group (owner-only -> 403)
    rename_res = client.patch(
        f"/api/v1/groups/{group_id}",
        json={"name": "Hijacked"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert rename_res.status_code == 403

    del_res = client.delete(
        f"/api/v1/groups/{group_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert del_res.status_code == 403


def test_admin_safety_rules_and_audit_log():
    admin_token = _login("admin@vulndesk.local", "DemoPass123!")
    tutor_token = _login("tutor@vulndesk.local", "TutorPass123!")
    headers = {"Authorization": f"Bearer {admin_token}"}

    admin_id = client.get("/api/v1/auth/me", headers=headers).json()["id"]
    tutor_id = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tutor_token}"}).json()["id"]

    # Admin cannot change own role
    self_role = client.patch(f"/api/v1/admin/users/{admin_id}/role", json={"role": "researcher"}, headers=headers)
    assert self_role.status_code in (400, 403, 409)

    # Admin cannot ban another admin
    ban_other_admin = client.patch(
        f"/api/v1/admin/users/{tutor_id}/ban",
        json={"is_banned": True, "reason": "test"},
        headers=headers,
    )
    assert ban_other_admin.status_code == 403

    # Audit log target labels & Security view work
    group = client.post(
        "/api/v1/groups",
        json={"name": "Audit Target Group"},
        headers=headers,
    )
    assert group.status_code == 201

    audit = client.get("/api/v1/admin/audit-logs?action=group_create", headers=headers)
    assert audit.status_code == 200
    assert "items" in audit.json()
    assert audit.json()["items"][0]["target_label"] == "Audit Target Group"

    sec = client.get("/api/v1/admin/security", headers=headers)
    assert sec.status_code == 200
    assert "failed_by_ip" in sec.json()
