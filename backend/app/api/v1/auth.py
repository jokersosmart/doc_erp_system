"""Auth endpoints: POST /login, POST /logout, GET /me (FR-038)."""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    authenticate_ldap,
    create_access_token,
    verify_local_password,
)
from app.models.audit_package import AuditTrailEntry
from app.models.org import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    display_name: str
    locale: str


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    LDAP-first authentication (FR-038).
    Falls back to local admin only when LDAP returns None AND the user is_local_admin=True.
    Emergency local login writes an audit trail entry and emits a security alert log.
    """
    ldap_user = authenticate_ldap(body.username, body.password)
    is_local_login = False

    if ldap_user is not None:
        # Upsert user from LDAP data
        result = await db.execute(select(User).where(User.username == body.username))
        user: User | None = result.scalar_one_or_none()
        if user is None:
            user = User(
                username=ldap_user["username"],
                email=ldap_user["email"],
                display_name=ldap_user["display_name"],
                ldap_dn=ldap_user["ldap_dn"],
                is_local_admin=False,
            )
            db.add(user)
        else:
            user.ldap_dn = ldap_user["ldap_dn"]
            user.display_name = ldap_user["display_name"]
        user.last_login_at = datetime.now(UTC)
        await db.flush()

    else:
        # Local admin fallback
        result = await db.execute(select(User).where(User.username == body.username))
        user = result.scalar_one_or_none()
        if (
            user is None
            or not user.is_local_admin
            or user.password_hash is None
            or not verify_local_password(body.password, user.password_hash)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        is_local_login = True
        user.last_login_at = datetime.now(UTC)
        await db.flush()

        # Security: log emergency local login
        if is_local_login:
            logger.warning("SECURITY: Local admin login used for user %s", body.username)
            audit = AuditTrailEntry(
                actor_id=user.id,
                action="local_admin_login",
                detail={"username": body.username, "reason": "LDAP unavailable or failed"},
            )
            db.add(audit)

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"username": user.username, "is_local_admin": user.is_local_admin},
    )
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        locale=user.locale,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> None:
    """Token invalidation on client side (stateless JWT); endpoint for future token blocklist."""
    return None


class MeResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    email: str
    locale: str
    is_local_admin: bool
