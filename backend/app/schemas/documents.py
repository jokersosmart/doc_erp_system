"""Document API request and response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.document import LifecycleState


class DynamicAttributeValue(BaseModel):
    attribute_key: str
    value_string: str | None = None
    value_integer: int | None = None
    value_boolean: bool | None = None
    value_date: str | None = None


class CreateDocumentRequest(BaseModel):
    project_id: uuid.UUID
    owner_id: uuid.UUID
    partition_id: uuid.UUID
    title: str = Field(max_length=500)
    document_type: str = Field(default="spec", max_length=50)
    content_markdown: str = ""
    standards_scope: list[str]


class UpdateDocumentRequest(BaseModel):
    expected_version: int = Field(ge=1)
    content_markdown: str
    commit_message: str | None = None


class LifecycleTransitionRequest(BaseModel):
    to_state: LifecycleState
    rationale: str | None = None


class MarkdownConversionResponse(BaseModel):
    source_filename: str | None = None
    title: str | None = None
    markdown: str


class DocumentResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    owner_id: uuid.UUID | None
    partition_id: uuid.UUID | None
    title: str
    document_type: str
    content_markdown: str
    lifecycle_state: LifecycleState
    current_version: int
    attributes: list[DynamicAttributeValue] = Field(default_factory=list)
    updated_at: datetime | None

    @classmethod
    def from_document(
        cls,
        *,
        document,
        attributes: list[DynamicAttributeValue] | None = None,
    ) -> "DocumentResponse":
        return cls(
            id=document.id,
            project_id=document.project_id,
            owner_id=document.owner_id,
            partition_id=document.bu_node_id,
            title=document.title,
            document_type=document.document_type,
            content_markdown=document.content_markdown,
            lifecycle_state=document.lifecycle_state,
            current_version=document.current_version,
            attributes=attributes or [],
            updated_at=document.updated_at,
        )
