"""ORM models: AttributeDefinition, SpecItem, AttributeValue, DependencyLink."""
import uuid
from datetime import datetime
from typing import Any

import enum
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ItemType(str, enum.Enum):
    REQUIREMENT = "REQUIREMENT"
    DESIGN_ELEMENT = "DESIGN_ELEMENT"
    TEST_CASE = "TEST_CASE"
    EVIDENCE = "EVIDENCE"


class DependencyRelationshipType(str, enum.Enum):
    BLOCKING = "BLOCKING"
    BLOCKED_BY = "BLOCKED_BY"
    RELATED = "RELATED"


class TraceabilityState(str, enum.Enum):
    """FR-019b — VALID/SUSPECT traceability state (Constitution §II)."""
    VALID = "VALID"
    SUSPECT = "SUSPECT"


class AttributeType(str, enum.Enum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    ENUM = "ENUM"
    UUID_REF = "UUID_REF"


class AttributeDefinition(Base):
    """
    EAV attribute registry per document_type (FR-034, FR-035).
    schema_version allows incremental additions without breaking existing records.
    """

    __tablename__ = "attribute_definitions"
    __table_args__ = (
        Index("ix_attr_def_document_type", "document_type"),
        Index("ix_attr_def_schema_version", "schema_version"),
        UniqueConstraint("document_type", "attribute_key", "schema_version", name="uq_attr_def"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    attribute_key: Mapped[str] = mapped_column(String(100), nullable=False)
    display_label_en: Mapped[str] = mapped_column(String(200), nullable=False)
    display_label_zh: Mapped[str] = mapped_column(String(200), nullable=False)
    attribute_type: Mapped[AttributeType] = mapped_column(
        Enum(AttributeType), nullable=False, default=AttributeType.STRING
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_safety_critical: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # FDTI, FRTI, FHTI, Diagnostic Coverage
    enum_values: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True
    )  # allowed values when attribute_type=ENUM
    validation_regex: Mapped[str | None] = mapped_column(Text, nullable=True)
    codebeamer_column: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # maps to CodeBeamer xlsx column name (FR-024)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SpecItem(Base):
    """
    A single addressable item within a document (requirement, design element, test case, evidence).
    Carries EAV attributes and dependency relationships.
    """

    __tablename__ = "spec_items"
    __table_args__ = (
        Index("ix_spec_items_document_id", "document_id"),
        Index("ix_spec_items_item_type", "item_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    item_identifier: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "SM-001"
    item_type: Mapped[ItemType] = mapped_column(
        Enum(ItemType), nullable=False, default=ItemType.REQUIREMENT
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    section_heading: Mapped[str | None] = mapped_column(
        String(300), nullable=True
    )  # for AI suggestion positioning
    clause_reference: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # e.g. "ISO-26262 Part 6 Clause 7.4.2" (FR-034a)
    upstream_obsolete_warning: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # FR-039
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document: Mapped["Document"] = relationship("Document", back_populates="spec_items")  # type: ignore[name-defined]
    attribute_values: Mapped[list["AttributeValue"]] = relationship(
        "AttributeValue", back_populates="spec_item", cascade="all, delete-orphan"
    )
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


class AttributeValue(Base):
    """EAV value row — one per (SpecItem, AttributeDefinition) pair."""

    __tablename__ = "attribute_values"
    __table_args__ = (
        UniqueConstraint("spec_item_id", "attribute_definition_id", name="uq_attr_value"),
        Index("ix_attr_values_spec_item_id", "spec_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spec_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("spec_items.id"), nullable=False
    )
    attribute_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attribute_definitions.id"), nullable=False
    )
    value_string: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_json: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    spec_item: Mapped["SpecItem"] = relationship("SpecItem", back_populates="attribute_values")
    attribute_definition: Mapped["AttributeDefinition"] = relationship("AttributeDefinition")


class DependencyLink(Base):
    """
    Typed dependency between SpecItems (FR-018, FR-034b/c/d, FR-019b).

    Relationship types:
      BLOCKING   — source blocks target (target cannot proceed if source changes)
      BLOCKED_BY — source is blocked by target (inverse of BLOCKING)
      RELATED    — non-blocking reference link

    traceability_state (FR-019b, Constitution §II):
      VALID   — link is current and verified
      SUSPECT — upstream source changed; downstream owner must re-verify
    """

    __tablename__ = "dependency_links"
    __table_args__ = (
        Index("ix_dep_links_source_item_id", "source_item_id"),
        Index("ix_dep_links_target_item_id", "target_item_id"),
        Index("ix_dep_links_relationship_type", "relationship_type"),
        Index("ix_dep_links_traceability_state", "traceability_state"),
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
    traceability_state: Mapped[TraceabilityState] = mapped_column(
        Enum(TraceabilityState), nullable=False, default=TraceabilityState.VALID
    )  # FR-019b — VALID/SUSPECT (Constitution §II)
    has_cycle_warning: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # FR-015d — async cycle detection flag
    label: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # e.g. "Source HSR", "Source HSI"
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source_item: Mapped["SpecItem"] = relationship(
        "SpecItem", foreign_keys=[source_item_id], back_populates="outgoing_links"
    )
    target_item: Mapped["SpecItem"] = relationship(
        "SpecItem", foreign_keys=[target_item_id], back_populates="incoming_links"
    )
