"""Partition Pydantic schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class PartitionCreate(BaseModel):
    project_id: uuid.UUID
    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Partition name cannot be empty")
        return v


class PartitionRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PartitionListResponse(BaseModel):
    items: list[PartitionRead]
    total: int
    page: int
    page_size: int
