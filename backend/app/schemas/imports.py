"""Schemas for Narwhal/AiWorkSpace import scanning."""

from __future__ import annotations

import enum
import uuid

from pydantic import BaseModel, Field

from app.models.spec_item import DependencyRelationshipType
from app.schemas.documents import DocumentResponse


class NarwhalScanRequest(BaseModel):
    config_path: str = Field(description="Absolute path to Narwhal_md_path_config.json")
    process_keys: list[str] | None = Field(default=None, description="Optional process key filter")
    include_disabled: bool = Field(default=False)


class NarwhalProcessSummary(BaseModel):
    process_key: str
    folder: str
    description: str
    enabled: bool
    pattern_prefix: str
    source_block_type: str | None = None
    metadata_fields: list[str] = Field(default_factory=list)


class NarwhalImportCandidate(BaseModel):
    process_key: str
    document_type: str
    source_path: str
    relative_path: str
    file_name: str
    title: str
    pattern_prefix: str


class NarwhalScanResponse(BaseModel):
    workspace_root: str
    processes: list[NarwhalProcessSummary]
    candidates: list[NarwhalImportCandidate]
    total_candidates: int


class NarwhalImportDocumentRequest(BaseModel):
    config_path: str = Field(description="Absolute path to Narwhal_md_path_config.json")
    process_key: str
    relative_path: str = Field(description="Workspace-relative markdown path to import")
    project_id: uuid.UUID
    owner_id: uuid.UUID
    partition_id: uuid.UUID
    standards_scope: list[str] = Field(default_factory=list)
    trace_link_mode: "NarwhalTraceLinkMode" = Field(default="NONE")
    relationship_strategy: "NarwhalRelationshipStrategy" = Field(default="FIXED")
    relationship_type: DependencyRelationshipType = Field(
        default=DependencyRelationshipType.BLOCKING
    )


class NarwhalTraceLinkMode(str, enum.Enum):
    NONE = "NONE"
    SUGGEST = "SUGGEST"
    AUTO_CREATE = "AUTO_CREATE"


class NarwhalRelationshipStrategy(str, enum.Enum):
    FIXED = "FIXED"
    PROCESS_DEFAULT = "PROCESS_DEFAULT"


class NarwhalTraceLinkStatus(str, enum.Enum):
    SUGGESTED = "SUGGESTED"
    CREATED = "CREATED"
    UNRESOLVED = "UNRESOLVED"
    SKIPPED_CONFLICT = "SKIPPED_CONFLICT"


class NarwhalTraceLinkResult(BaseModel):
    source_item_id: uuid.UUID
    source_identifier: str
    target_identifier: str
    target_item_id: uuid.UUID | None = None
    relationship_type: DependencyRelationshipType
    status: NarwhalTraceLinkStatus
    reason: str | None = None


class NarwhalImportDocumentResponse(BaseModel):
    process_key: str
    source_path: str
    relative_path: str
    document: DocumentResponse
    source_item_id: uuid.UUID
    source_item_identifier: str
    trace_links: list[NarwhalTraceLinkResult] = Field(default_factory=list)


class NarwhalBatchImportRequest(BaseModel):
    config_path: str = Field(description="Absolute path to Narwhal_md_path_config.json")
    project_id: uuid.UUID
    owner_id: uuid.UUID
    partition_id: uuid.UUID
    standards_scope: list[str] = Field(default_factory=list)
    process_keys: list[str] | None = None
    relative_paths: list[str] | None = None
    include_disabled: bool = False
    trace_link_mode: NarwhalTraceLinkMode = Field(default=NarwhalTraceLinkMode.NONE)
    relationship_strategy: NarwhalRelationshipStrategy = Field(
        default=NarwhalRelationshipStrategy.FIXED
    )
    relationship_type: DependencyRelationshipType = Field(
        default=DependencyRelationshipType.BLOCKING
    )


class NarwhalBatchImportResponse(BaseModel):
    workspace_root: str
    imported: list[NarwhalImportDocumentResponse]
    imported_count: int
