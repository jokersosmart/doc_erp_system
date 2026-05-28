"""Document ORM models and lifecycle enums."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class LifecycleState(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    OBSOLETE = "OBSOLETE"


class LockState(str, enum.Enum):
    UNLOCKED = "UNLOCKED"
    LOCKED = "LOCKED"
    PENDING_QRA = "PENDING_QRA"


class Document(Base):
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
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, default="spec")
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    standards_scope: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        Enum(LifecycleState), nullable=False, default=LifecycleState.DRAFT
    )
    lock_state: Mapped[LockState] = mapped_column(
        Enum(LockState), nullable=False, default=LockState.UNLOCKED
    )
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_transition_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="documents")
    spec_items: Mapped[list["SpecItem"]] = relationship("SpecItem", back_populates="document")
    revisions: Mapped[list["DocumentRevision"]] = relationship(
        "DocumentRevision", back_populates="document", cascade="all, delete-orphan"
    )
    transition_events: Mapped[list["DocumentTransitionEvent"]] = relationship(
        "DocumentTransitionEvent", back_populates="document", cascade="all, delete-orphan"
    )
    lock_events_triggered: Mapped[list["LockEvent"]] = relationship(
        "LockEvent",
        foreign_keys="LockEvent.upstream_document_id",
        back_populates="upstream_document",
    )
