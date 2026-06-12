"""
Tests for auth endpoints — login, register, refresh, me, change-password.
"""
import pytest


class TestAuth:
    """Auth endpoint tests."""

    async def test_register(self, client, test_user):
        """Should register a new user successfully."""
        _ = test_user
        resp = await client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "display_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "roles" in data

    async def test_register_duplicate_username(self, client, test_user):
        """Should reject duplicate username."""
        resp = await client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "other@example.com",
            "password": "password123",
        })
        assert resp.status_code == 409

    async def test_register_duplicate_email(self, client, test_user):
        """Should reject duplicate email."""
        resp = await client.post("/api/auth/register", json={
            "username": "other",
            "email": "test@example.com",
            "password": "password123",
        })
        assert resp.status_code == 409

    async def test_login_success(self, client, test_user):
        """Should login and return tokens."""
        resp = await client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client, test_user):
        """Should reject wrong password."""
        resp = await client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    async def test_login_inactive_user(self, client, db_session):
        """Should reject inactive user."""
        from app.core.security import hash_password
        from app.models.user import User

        user = User(
            username="blocked",
            email="blocked@example.com",
            hashed_password=hash_password("pass"),
            is_active=False,
        )
        db_session.add(user)
        await db_session.commit()

        resp = await client.post("/api/auth/login", json={
            "username": "blocked",
            "password": "testpassword",
        })
        assert resp.status_code == 401

    async def test_refresh_token(self, client, test_user):
        """Should issue new tokens with a valid refresh token."""
        login_resp = await client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "password123",
        })
        refresh = login_resp.json()["refresh_token"]

        resp = await client.post("/api/auth/refresh", json={
            "refresh_token": refresh,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, client):
        """Should reject invalid refresh token."""
        resp = await client.post("/api/auth/refresh", json={
            "refresh_token": "invalid-token",
        })
        assert resp.status_code == 401

    async def test_me(self, client, test_user):
        """Should return current user info."""
        headers = await _login(client, "testuser", "password123")
        resp = await client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"

    async def test_me_unauthorized(self, client):
        """Should reject without token."""
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_change_password(self, client, test_user):
        """Should change password successfully."""
        headers = await _login(client, "testuser", "password123")

        resp = await client.post("/api/auth/change-password", json={
            "old_password": "password123",
            "new_password": "newpass456",
        }, headers=headers)
        assert resp.status_code == 200

        # Old password should no longer work
        resp2 = await client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "password123",
        })
        assert resp2.status_code == 401

        # New password should work
        resp3 = await client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "newpass456",
        })
        assert resp3.status_code == 200

    async def test_change_password_wrong_old(self, client, test_user):
        """Should reject wrong old password."""
        headers = await _login(client, "testuser", "password123")

        resp = await client.post("/api/auth/change-password", json={
            "old_password": "wrong",
            "new_password": "newpass456",
        }, headers=headers)
        assert resp.status_code == 400


# Helper
async def _login(client, username: str, password: str) -> dict:
    resp = await client.post("/api/auth/login", json={
        "username": username, "password": password
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
