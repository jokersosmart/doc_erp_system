"""Spec item and dependency link ORM models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class DependencyRelationshipType(str, enum.Enum):
    BLOCKING = "BLOCKING"
    BLOCKED_BY = "BLOCKED_BY"
    RELATED = "RELATED"


class DependencyHealthState(str, enum.Enum):
    HEALTHY = "HEALTHY"
    SUSPECT = "SUSPECT"
    RESOLVED = "RESOLVED"


class SpecItem(Base):
    __tablename__ = "spec_items"
    __table_args__ = (Index("ix_spec_items_document_id", "document_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    item_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="spec_items")
    outgoing_links: Mapped[list["DependencyLink"]] = relationship(
        "DependencyLink",
        foreign_keys="DependencyLink.source_item_id",
        back_populates="source_item",
        cascade="all, delete-orphan",
    )
    incoming_links: Mapped[list["DependencyLink"]] = relationship(
        "DependencyLink",
        foreign_keys="DependencyLink.target_item_id",
        back_populates="target_item",
    )


class DependencyLink(Base):
    __tablename__ = "dependency_links"
    __table_args__ = (
        Index("ix_dep_links_source_item_id", "source_item_id"),
        Index("ix_dep_links_target_item_id", "target_item_id"),
        Index("ix_dep_links_relationship_type", "relationship_type"),
        Index("ix_dep_links_target_health_state", "target_item_id", "health_state"),
        Index("ix_dep_links_source_health_state", "source_item_id", "health_state"),
        UniqueConstraint(
            "source_item_id", "target_item_id", "relationship_type", name="uq_dep_link"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("spec_items.id"), nullable=False
    )
    target_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("spec_items.id"), nullable=False
    )
    relationship_type: Mapped[DependencyRelationshipType] = mapped_column(
        Enum(DependencyRelationshipType), nullable=False
    )
    health_state: Mapped[DependencyHealthState] = mapped_column(
        Enum(DependencyHealthState), nullable=False, default=DependencyHealthState.HEALTHY
    )
    suspect_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_health_transition_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_transition_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_item: Mapped[SpecItem] = relationship(
        "SpecItem", foreign_keys=[source_item_id], back_populates="outgoing_links"
    )
    target_item: Mapped[SpecItem] = relationship(
        "SpecItem", foreign_keys=[target_item_id], back_populates="incoming_links"
    )
    suspect_resolutions: Mapped[list["SuspectResolution"]] = relationship(
        "SuspectResolution",
        back_populates="dependency_link",
        cascade="all, delete-orphan",
    )
