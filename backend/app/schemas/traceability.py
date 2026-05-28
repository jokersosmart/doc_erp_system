"""Traceability API request and response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.spec_item import DependencyHealthState, DependencyRelationshipType


class CreateTraceabilityLinkRequest(BaseModel):
    source_item_id: uuid.UUID
    target_item_id: uuid.UUID
    relationship_type: DependencyRelationshipType


class TraceabilityLinkResponse(BaseModel):
    id: uuid.UUID
    source_item_id: uuid.UUID
    target_item_id: uuid.UUID
    relationship_type: DependencyRelationshipType
    health_status: DependencyHealthState
    last_upstream_revision: int | None = None
    suspect_since: datetime | None = None

    @classmethod
    def from_link(cls, *, link) -> "TraceabilityLinkResponse":
        suspect_since = (
            link.last_health_transition_at if link.health_state == DependencyHealthState.SUSPECT else None
        )
        return cls(
            id=link.id,
            source_item_id=link.source_item_id,
            target_item_id=link.target_item_id,
            relationship_type=link.relationship_type,
            health_status=link.health_state,
            last_upstream_revision=None,
            suspect_since=suspect_since,
        )


class ImpactedDocument(BaseModel):
    document_id: uuid.UUID
    title: str
    owner_id: uuid.UUID | None = None
    health_status: DependencyHealthState
    current_resolution: str | None = None


class ImpactAnalysisResponse(BaseModel):
    upstream_document_id: uuid.UUID
    upstream_version: int | None = None
    impacted_documents: list[ImpactedDocument]


class ResolveType(str):
    UPDATED = "UPDATED"
    NOT_IMPACTED = "NOT_IMPACTED"
    PENDING = "PENDING"


class ResolveSuspectRequest(BaseModel):
    resolution_type: str = Field(pattern="^(UPDATED|NOT_IMPACTED|PENDING)$")
    rationale: str | None = None
