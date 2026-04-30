"""Auth endpoints: login and refresh token."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.crud.user import authenticate_user
from app.db.session import get_db
from app.models.refresh_token import RefreshToken
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from sqlalchemy import select

router = APIRouter()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Authenticate user and return JWT access and refresh tokens."""
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid username or password", "code": "AUTH_INVALID_TOKEN"},
        )

    access_token = create_access_token(
        user_id=user["id"],
        role=user["role"],
        partition_access=user["partition_access"],
    )
    refresh_token = create_refresh_token(user_id=user["id"])

    # Store hashed refresh token
    token_hash = hash_token(refresh_token)
    refresh_payload = decode_token(refresh_token)
    expires_at = datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)

    db_token = RefreshToken(
        user_id=user["id"],
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(db_token)
    await db.flush()  # Make token visible within the session before response

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Refresh access token using a valid refresh token (Rotation)."""
    try:
        payload = decode_token(request.refresh_token)
    except ValueError as e:
        code = str(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid or expired refresh token", "code": code},
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid token type", "code": "AUTH_INVALID_TOKEN"},
        )

    token_hash = hash_token(request.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()

    if not db_token or db_token.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Refresh token has been revoked", "code": "AUTH_TOKEN_REVOKED"},
        )

    if db_token.expires_at.replace(tzinfo=None) < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Refresh token expired", "code": "AUTH_TOKEN_EXPIRED"},
        )

    # Revoke the old token (rotation)
    db_token.revoked_at = datetime.now(timezone.utc)
    await db.flush()

    # Get user info (from simple store)
    from app.crud.user import _USERS
    user = next((u for u in _USERS.values() if u["id"] == payload["sub"]), None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "User not found", "code": "AUTH_INVALID_TOKEN"},
        )

    # Issue new tokens
    new_access = create_access_token(
        user_id=user["id"],
        role=user["role"],
        partition_access=user["partition_access"],
    )
    new_refresh = create_refresh_token(user_id=user["id"])

    # Store new refresh token
    new_hash = hash_token(new_refresh)
    new_payload = decode_token(new_refresh)
    new_expires = datetime.fromtimestamp(new_payload["exp"], tz=timezone.utc)
    new_db_token = RefreshToken(
        user_id=user["id"],
        token_hash=new_hash,
        expires_at=new_expires,
    )
    db.add(new_db_token)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
    )
