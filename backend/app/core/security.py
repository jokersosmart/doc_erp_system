"""
Authentication helpers: LDAP bind (primary), bcrypt local-admin (fallback), JWT (FR-038).

Security notes:
- LDAP credentials are never stored; only the DN is persisted for reference.
- Local admin password_hash uses bcrypt with cost factor ≥ 12.
- Emergency local-admin login writes an audit log entry and emits a security alert.
- JWT tokens are short-lived (configurable, default 8 h) and signed with HS256.
"""
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import ldap  # type: ignore[import]
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# ── LDAP ──────────────────────────────────────────────────────────────────────


def authenticate_ldap(username: str, password: str) -> dict[str, Any] | None:
    """
    Attempt LDAP bind.  Returns basic user dict on success, None on failure.
    Never raises — all LDAP exceptions are swallowed and logged at WARNING level.
    """
    try:
        conn = ldap.initialize(settings.LDAP_URL)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)
        conn.set_option(ldap.OPT_TIMEOUT, 5)

        # Search for user DN
        search_filter = settings.LDAP_USER_SEARCH_FILTER.replace("{username}", username)
        results = conn.search_s(settings.LDAP_BASE_DN, ldap.SCOPE_SUBTREE, search_filter, ["cn", "mail", "displayName"])
        if not results:
            return None
        user_dn, attrs = results[0]

        # Bind with user credentials
        conn.simple_bind_s(user_dn, password)

        return {
            "ldap_dn": user_dn,
            "username": username,
            "email": (attrs.get("mail", [b""])[0] or b"").decode(),
            "display_name": (attrs.get("displayName", [username.encode()])[0]).decode(),
        }
    except ldap.INVALID_CREDENTIALS:
        return None
    except Exception as exc:
        logger.warning("LDAP authentication error for user %s: %s", username, exc)
        return None


# ── Local admin fallback (FR-038) ─────────────────────────────────────────────


def verify_local_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


# ── JWT ───────────────────────────────────────────────────────────────────────


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "iat": datetime.now(UTC)}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token. Raises JWTError on invalid/expired token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
