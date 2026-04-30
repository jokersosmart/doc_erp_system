"""Security utilities: JWT signing/verification and password hashing."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token types
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(
    user_id: str | UUID,
    role: str,
    partition_access: list[str],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "partition_access": partition_access,
        "exp": expire,
        "iat": now,
        "jti": secrets.token_hex(8),  # Unique token ID to prevent duplicates
        "type": ACCESS_TOKEN_TYPE,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    user_id: str | UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token."""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "type": REFRESH_TOKEN_TYPE,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT token.

    Raises:
        ValueError: if token is expired or invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError as e:
        error_str = str(e)
        if "expired" in error_str.lower() or "Signature has expired" in error_str:
            raise ValueError("AUTH_TOKEN_EXPIRED") from e
        raise ValueError("AUTH_INVALID_TOKEN") from e


def hash_token(token: str) -> str:
    """Hash a refresh token for storage (SHA-256)."""
    return hashlib.sha256(token.encode()).hexdigest()
