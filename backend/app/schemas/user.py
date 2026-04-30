"""User Pydantic schemas."""
import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    role: str
    partition_access: List[str] = []


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class UserInToken(BaseModel):
    """Current user extracted from JWT."""
    user_id: str
    role: str
    partition_access: list[str] = []
