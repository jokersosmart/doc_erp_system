"""Unit tests for JWT security utilities."""
from datetime import timedelta

import pytest

from app.core.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestCreateAccessToken:
    def test_create_access_token_contains_required_fields(self):
        token = create_access_token(
            user_id="user-123",
            role="Admin",
            partition_access=["SWE", "SYS"],
        )
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "Admin"
        assert payload["partition_access"] == ["SWE", "SYS"]
        assert "exp" in payload
        assert payload["type"] == ACCESS_TOKEN_TYPE

    def test_create_access_token_default_expiry(self):
        from datetime import datetime, timezone
        token = create_access_token(user_id="u1", role="RD", partition_access=[])
        payload = decode_token(token)
        now = datetime.now(timezone.utc).timestamp()
        # Token should expire in the future
        assert payload["exp"] > now

    def test_create_access_token_custom_expiry(self):
        from datetime import datetime, timezone
        token = create_access_token(
            user_id="u1",
            role="RD",
            partition_access=[],
            expires_delta=timedelta(minutes=5),
        )
        payload = decode_token(token)
        now = datetime.now(timezone.utc).timestamp()
        # Should expire in about 5 minutes (±30s tolerance)
        assert payload["exp"] - now < 330
        assert payload["exp"] > now


class TestVerifyToken:
    def test_verify_token_success(self):
        token = create_access_token(user_id="u1", role="QA", partition_access=["SWE"])
        payload = decode_token(token)
        assert payload["sub"] == "u1"
        assert payload["role"] == "QA"

    def test_verify_token_expired(self):
        token = create_access_token(
            user_id="u1",
            role="PM",
            partition_access=[],
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        with pytest.raises(ValueError, match="AUTH_TOKEN_EXPIRED"):
            decode_token(token)

    def test_verify_token_invalid_signature(self):
        token = create_access_token(user_id="u1", role="Admin", partition_access=[])
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(ValueError, match="AUTH_INVALID_TOKEN"):
            decode_token(tampered)

    def test_verify_token_malformed(self):
        with pytest.raises(ValueError, match="AUTH_INVALID_TOKEN"):
            decode_token("not.a.valid.token")


class TestRefreshToken:
    def test_create_refresh_token_type(self):
        token = create_refresh_token(user_id="u1")
        payload = decode_token(token)
        assert payload["type"] == REFRESH_TOKEN_TYPE
        assert payload["sub"] == "u1"

    def test_refresh_token_no_role(self):
        """Refresh token should not contain role or partition_access."""
        token = create_refresh_token(user_id="u1")
        payload = decode_token(token)
        assert "role" not in payload
        assert "partition_access" not in payload


class TestPasswordHashing:
    def test_password_hash_and_verify(self):
        password = "SecurePassword@123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        hashed = get_password_hash("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_different_hashes_for_same_password(self):
        """bcrypt should produce different hashes each time (salted)."""
        password = "same-password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
