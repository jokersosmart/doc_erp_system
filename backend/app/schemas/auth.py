"""Authentication and authorization Pydantic schemas."""
from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    """Login credentials."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""
    sub: str  # user_id
    role: str
    partition_access: list[str] = []
    type: str = "access"
