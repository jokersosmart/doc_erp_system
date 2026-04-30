"""Integration tests for authentication endpoints."""
import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


class TestLogin:
    async def test_login_success(self, async_client):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, async_client):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong_password"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["detail"]["code"] == "AUTH_INVALID_TOKEN"

    async def test_login_nonexistent_user(self, async_client):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "ghost_user", "password": "password123"},
        )
        assert resp.status_code == 401

    async def test_login_rd_user(self, async_client):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "rd_user", "password": "RD@123456"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data


class TestRefreshToken:
    async def test_refresh_token_success(self, async_client):
        # First login
        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New tokens should be different
        assert data["access_token"] != login_resp.json()["access_token"]

    async def test_refresh_token_rotation(self, async_client):
        """Old refresh token should be revoked after use."""
        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Use the token once
        resp1 = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp1.status_code == 200

        # Try to use the same token again - should fail (revoked)
        resp2 = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp2.status_code == 401

    async def test_refresh_with_invalid_token(self, async_client):
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not.a.valid.token"},
        )
        assert resp.status_code == 401

    async def test_refresh_with_access_token(self, async_client):
        """Access token should not be usable as refresh token."""
        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin@123"},
        )
        access_token = login_resp.json()["access_token"]

        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert resp.status_code == 401


class TestProtectedEndpoints:
    async def test_access_protected_without_token(self, async_client):
        resp = await async_client.get("/api/v1/projects")
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "AUTH_MISSING_TOKEN"

    async def test_access_protected_with_expired_token(self, async_client):
        from datetime import timedelta
        from app.core.security import create_access_token

        expired_token = create_access_token(
            user_id="user-admin-001",
            role="Admin",
            partition_access=[],
            expires_delta=timedelta(seconds=-1),
        )
        resp = await async_client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "AUTH_TOKEN_EXPIRED"

    async def test_access_protected_with_invalid_token(self, async_client):
        resp = await async_client.get(
            "/api/v1/projects",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    async def test_health_endpoint_no_auth_required(self, async_client):
        """Health endpoint should be accessible without authentication."""
        resp = await async_client.get("/health")
        assert resp.status_code == 200
