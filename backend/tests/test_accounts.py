"""
Tests for AI Accounts — CRUD with encryption and permission gating.

Uses API-based setup where possible, and db_session for admin creation.
"""
import pytest


class TestAccounts:

    async def test_list_empty(self, client, db_session):
        h = await _ensure_admin(client, db_session)
        resp = await client.get("/api/accounts/", headers=h)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_create_account(self, client, db_session):
        h = await _ensure_admin(client, db_session)
        resp = await client.post("/api/accounts/", json={
            "platform": "openai", "account_name": "Test OpenAI",
            "username": "myuser", "password": "secret123",
            "api_key": "sk-test-key", "cookie_data": '{"s":"abc"}',
        }, headers=h)
        assert resp.status_code == 201
        data = resp.json()
        assert data["platform"] == "openai"
        assert "username" not in data
        assert "api_key" not in data

    async def test_create_without_permission(self, client):
        h = await _ensure_user(client)
        resp = await client.post("/api/accounts/", json={
            "platform": "openai", "account_name": "Test",
        }, headers=h)
        assert resp.status_code == 403

    async def test_list_accounts(self, client, db_session):
        h = await _ensure_admin(client, db_session)
        await client.post("/api/accounts/", json={"platform": "openai", "account_name": "A1"}, headers=h)
        await client.post("/api/accounts/", json={"platform": "claude", "account_name": "A2"}, headers=h)
        resp = await client.get("/api/accounts/", headers=h)
        assert resp.json()["total"] == 2

    async def test_filter_by_platform(self, client, db_session):
        h = await _ensure_admin(client, db_session)
        await client.post("/api/accounts/", json={"platform": "openai", "account_name": "O1"}, headers=h)
        await client.post("/api/accounts/", json={"platform": "claude", "account_name": "C1"}, headers=h)
        resp = await client.get("/api/accounts/?platform=openai", headers=h)
        assert resp.json()["total"] == 1

    async def test_update_account(self, client, db_session):
        h = await _ensure_admin(client, db_session)
        r = await client.post("/api/accounts/", json={"platform": "openai", "account_name": "Original"}, headers=h)
        acc_id = r.json()["id"]
        resp = await client.put(f"/api/accounts/{acc_id}", json={"account_name": "Updated"}, headers=h)
        assert resp.json()["account_name"] == "Updated"

    async def test_delete_account(self, client, db_session):
        h = await _ensure_admin(client, db_session)
        r = await client.post("/api/accounts/", json={"platform": "openai", "account_name": "ToDelete"}, headers=h)
        acc_id = r.json()["id"]
        resp = await client.delete(f"/api/accounts/{acc_id}", headers=h)
        assert resp.status_code == 204
        get_resp = await client.get(f"/api/accounts/{acc_id}", headers=h)
        assert get_resp.status_code == 404

    async def test_view_secret_with_permission(self, client, db_session):
        h = await _ensure_admin(client, db_session)
        r = await client.post("/api/accounts/", json={
            "platform": "openai", "account_name": "S",
            "username": "u", "password": "p", "api_key": "sk-k",
        }, headers=h)
        acc_id = r.json()["id"]
        resp = await client.get(f"/api/accounts/{acc_id}/secret", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "u"
        assert data["password"] == "p"
        assert data["api_key"] == "sk-k"

    async def test_view_secret_without_permission(self, client, db_session):
        h = await _ensure_admin(client, db_session)
        r = await client.post("/api/accounts/", json={
            "platform": "openai", "account_name": "NS", "api_key": "sk-secret",
        }, headers=h)
        acc_id = r.json()["id"]
        u = await _ensure_user(client)
        resp = await client.get(f"/api/accounts/{acc_id}/secret", headers=u)
        assert resp.status_code == 403

    async def test_encryption_at_rest(self, client, db_session):
        from app.models.account import AIAccount
        from sqlalchemy import select

        h = await _ensure_admin(client, db_session)
        await client.post("/api/accounts/", json={
            "platform": "openai", "account_name": "ET", "api_key": "sk-plain",
        }, headers=h)

        # Verify stored value is encrypted via DB
        result = await db_session.execute(select(AIAccount).where(AIAccount.account_name == "ET"))
        account = result.scalar_one()
        assert account.api_key != "sk-plain"
        assert len(str(account.api_key)) > 0

        # Via API secret endpoint
        resp = await client.get("/api/accounts/", headers=h)
        items = resp.json()["items"]
        acc_id = items[0]["id"]
        secret = await client.get(f"/api/accounts/{acc_id}/secret", headers=h)
        assert secret.json()["api_key"] == "sk-plain"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _register(client, username: str, password: str, email: str | None = None):
    r = await client.post("/api/auth/register", json={
        "username": username, "email": email or f"{username}@test.com",
        "password": password,
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _login(client, username: str, password: str) -> dict:
    r = await client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _ensure_admin(client, db_session) -> dict:
    """Create an admin superuser via DB, then login via API."""
    from app.core.security import hash_password
    from app.models.user import User, Role, Permission

    # Check if admin already exists
    from sqlalchemy import select as sa_select
    existing = await db_session.execute(sa_select(User).where(User.username == "admin"))
    if existing.scalar_one_or_none():
        return await _login(client, "admin", "admin123")

    role = Role(name="admin", description="Admin")
    db_session.add(role)
    await db_session.flush()

    perms_data = [
        ("accounts.read", "accounts"), ("accounts.read_secret", "accounts"),
        ("accounts.create", "accounts"), ("accounts.update", "accounts"),
        ("accounts.delete", "accounts"),
        ("compute.read", "compute"), ("compute.manage", "compute"),
        ("compute.request", "compute"), ("compute.approve", "compute"),
        ("dashboard.view", "dashboard"),
        ("admin.manage_users", "admin"), ("admin.manage_roles", "admin"),
    ]
    for codename, rtype in perms_data:
        perm = Permission(codename=codename, resource_type=rtype)
        db_session.add(perm)
        role.permissions.append(perm)

    user = User(
        username="admin", email="admin@test.com",
        hashed_password=hash_password("admin123"),
        display_name="Admin", is_active=True, is_superuser=True,
    )
    user.roles.append(role)
    db_session.add(user)
    await db_session.commit()
    return await _login(client, "admin", "admin123")


async def _ensure_user(client) -> dict:
    await _register(client, "normie", "pass1234")
    return await _login(client, "normie", "pass1234")
