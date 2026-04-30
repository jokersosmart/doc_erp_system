"""Document Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

from app.schemas.attribute import AttributeValueInput, AttributeValueRead

VALID_STATUSES = ("DRAFT", "REVIEW", "APPROVED", "OBSOLETE")
MAX_CONTENT_SIZE_MB = 5
MAX_CONTENT_SIZE_BYTES = MAX_CONTENT_SIZE_MB * 1024 * 1024


class DocumentCreate(BaseModel):
    project_id: uuid.UUID
    partition_id: uuid.UUID
    title: str
    content_md: str
    attributes: list[AttributeValueInput] = []

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("content_md")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content_md cannot be empty or whitespace only")
        if len(v.encode("utf-8")) > MAX_CONTENT_SIZE_BYTES:
            raise ValueError(
                f"content_md exceeds maximum size of {MAX_CONTENT_SIZE_MB}MB"
            )
        return v


class DocumentUpdate(BaseModel):
    title: str | None = None
    content_md: str | None = None
    commit_message: str | None = None
    attributes: list[AttributeValueInput] | None = None
    version_lock: int | None = None  # for optimistic locking

    @field_validator("content_md")
    @classmethod
    def content_not_empty(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.strip():
                raise ValueError("content_md cannot be empty or whitespace only")
            if len(v.encode("utf-8")) > MAX_CONTENT_SIZE_BYTES:
                raise ValueError(
                    f"content_md exceeds maximum size of {MAX_CONTENT_SIZE_MB}MB"
                )
        return v


class StatusTransitionRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v


class VersionListItem(BaseModel):
    id: uuid.UUID
    version: str
    modified_by: str
    commit_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VersionRead(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    version: str
    content_md: str
    modified_by: str
    commit_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListItem(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    partition_id: uuid.UUID
    title: str
    version: str
    status: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    partition_id: uuid.UUID
    title: str
    content_md: str
    version: str
    status: str
    owner_id: str
    version_lock: int
    attributes: list[AttributeValueRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
    page: int
    page_size: int


class VersionHistoryResponse(BaseModel):
    document_id: uuid.UUID
    current_version: str
    versions: list[VersionListItem]
