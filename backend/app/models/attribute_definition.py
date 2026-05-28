"""Dynamic attribute definition and per-revision value models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class AttributeDataType(str, enum.Enum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    ENUM = "ENUM"
    DATE = "DATE"


class AttributeDefinition(Base):
    __tablename__ = "attribute_definitions"
    __table_args__ = (
        UniqueConstraint("key", "standard_id", "partition_node_id", name="uq_attribute_definition_scope"),
        Index("ix_attribute_definitions_partition_node_id", "partition_node_id"),
        Index("ix_attribute_definitions_standard_id", "standard_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[AttributeDataType] = mapped_column(Enum(AttributeDataType), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    standard_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("standards.id"), nullable=True
    )
    partition_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisation_nodes.id"), nullable=True
    )
    allowed_values_json: Mapped[list[str] | dict | None] = mapped_column(JSONB, nullable=True)
    validation_rule_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentAttributeValue(Base):
    __tablename__ = "document_attribute_values"
    __table_args__ = (
        UniqueConstraint("revision_id", "attribute_definition_id", name="uq_document_attr_value"),
        Index("ix_document_attribute_values_document_id", "document_id"),
        Index("ix_document_attribute_values_revision_id", "revision_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_revisions.id"), nullable=False
    )
    attribute_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attribute_definitions.id"), nullable=False
    )
    value_string: Mapped[str | None] = mapped_column(String(500), nullable=True)
    value_integer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
