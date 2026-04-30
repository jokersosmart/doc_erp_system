"""ORM models: Document, DocumentVersion, AISuggestion."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

# ── Enums ──────────────────────────────────────────────────────────────────

import enum


class LifecycleState(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    OBSOLETE = "OBSOLETE"


class LockState(str, enum.Enum):
    UNLOCKED = "UNLOCKED"
    LOCKED = "LOCKED"
    PENDING_QRA = "PENDING_QRA"


class AISuggestionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


# ── Document ───────────────────────────────────────────────────────────────


class Document(Base):
    """
    Core document entity.

    Lifecycle (FR-013b — unidirectional except via explicit transition actions):
      DRAFT → REVIEW → APPROVED → OBSOLETE

    Backward transitions (REVIEW→DRAFT, APPROVED→REVIEW) are controlled via
    `revision_requested` flag and dedicated lifecycle endpoint, never via direct
    lifecycle_state mutation (FR-013b, constitution §Data Model).

    Lock state (FR-012/013/014):
      UNLOCKED → LOCKED → PENDING_QRA → UNLOCKED  (safety-critical)
      UNLOCKED → LOCKED → UNLOCKED                 (standard)
    """

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_project_id", "project_id"),
        Index("ix_documents_lifecycle_state", "lifecycle_state"),
        Index("ix_documents_lock_state", "lock_state"),
        Index("ix_documents_bu_node_id", "bu_node_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    bu_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisation_nodes.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # manual|procedure|spec|form
    partition: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # SYS|HW|SWE|SAFETY|SECURITY|FW|SW|VCT
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        Enum(LifecycleState), nullable=False, default=LifecycleState.DRAFT
    )
    lock_state: Mapped[LockState] = mapped_column(
        Enum(LockState), nullable=False, default=LockState.UNLOCKED
    )
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revision_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # FR-013b: flag for backward review without state regression
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    current_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # optimistic lock counter (FR-015b)
    schema_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="1.0"
    )  # EAV schema version (FR-035)
    git_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    git_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    upstream_obsolete_warning: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # FR-039
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="documents")  # type: ignore[name-defined]
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", order_by="DocumentVersion.version_number"
    )
    spec_items: Mapped[list["SpecItem"]] = relationship("SpecItem", back_populates="document")  # type: ignore[name-defined]
    ai_suggestions: Mapped[list["AISuggestion"]] = relationship(
        "AISuggestion", back_populates="document"
    )
    lock_events_triggered: Mapped[list["LockEvent"]] = relationship(  # type: ignore[name-defined]
        "LockEvent", foreign_keys="LockEvent.upstream_document_id", back_populates="upstream_document"
    )


class DocumentVersion(Base):
    """Immutable snapshot of document content at a point in time (FR-011)."""

    __tablename__ = "document_versions"
    __table_args__ = (Index("ix_doc_versions_document_id", "document_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_state_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    lock_state_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    committed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    git_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="versions")


class AISuggestion(Base):
    """AI-generated suggestion awaiting engineer Accept/Reject (FR-007, FR-008)."""

    __tablename__ = "ai_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    spec_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("spec_items.id"), nullable=True
    )
    suggested_content: Mapped[str] = mapped_column(Text, nullable=False)
    clause_reference: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # e.g. "ISO-26262 Part 6 Clause 7.4.2"
    position_hint: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # section heading or spec_item_id after which to insert
    status: Mapped[AISuggestionStatus] = mapped_column(
        Enum(AISuggestionStatus), nullable=False, default=AISuggestionStatus.PENDING
    )
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_offline_fallback: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # FR-033b
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="ai_suggestions")
