"""FastAPI dependencies for authentication and authorization."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from app.schemas.user import UserInToken

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserInToken:
    """Extract and validate the current user from JWT Bearer token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Missing authentication token", "code": "AUTH_MISSING_TOKEN"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ValueError as e:
        code = str(e)
        if code == "AUTH_TOKEN_EXPIRED":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"detail": "Token expired", "code": "AUTH_TOKEN_EXPIRED"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid authentication token", "code": "AUTH_INVALID_TOKEN"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid token type", "code": "AUTH_INVALID_TOKEN"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserInToken(
        user_id=payload["sub"],
        role=payload.get("role", ""),
        partition_access=payload.get("partition_access", []),
    )


def require_role(*roles: str):
    """Dependency factory: require the current user to have one of the specified roles."""

    async def _require_role(current_user: UserInToken = Depends(get_current_user)) -> UserInToken:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "detail": f"Role '{current_user.role}' is not authorized for this operation",
                    "code": "FORBIDDEN",
                },
            )
        return current_user

    return _require_role


def check_partition_access(user: UserInToken, partition_name: str) -> None:
    """Check if the user has access to the given partition name.

    Admin users bypass all partition checks.
    Raises HTTPException 403 if access denied.
    """
    if user.role == "Admin":
        return
    if partition_name not in user.partition_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": f"No access to partition '{partition_name}'",
                "code": "FORBIDDEN",
            },
        )
