"""Attribute Definition and Document Attribute Value ORM models (EAV)."""
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AttributeDefinition(Base):
    """EAV attribute definition - the 'A' in Entity-Attribute-Value."""

    __tablename__ = "attribute_definitions"

    __table_args__ = (
        CheckConstraint(
            "data_type IN ('STRING', 'INTEGER', 'BOOLEAN', 'ENUM')",
            name="ck_attribute_definitions_data_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    data_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # JSON list of allowed string values for ENUM type
    allowed_values: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    standard_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("standards.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    standard: Mapped["Standard | None"] = relationship(  # noqa: F821
        "Standard", back_populates="attribute_definitions"
    )
    document_values: Mapped[list["DocumentAttributeValue"]] = relationship(
        "DocumentAttributeValue",
        back_populates="attribute_definition",
        cascade="all, delete-orphan",
    )


class DocumentAttributeValue(Base):
    """EAV attribute value - the 'V' in Entity-Attribute-Value."""

    __tablename__ = "document_attribute_values"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "attribute_id",
            name="uq_document_attribute_values_doc_attr",
        ),
        CheckConstraint(
            "(CASE WHEN value_string IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN value_integer IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN value_boolean IS NOT NULL THEN 1 ELSE 0 END) <= 1",
            name="ck_document_attribute_values_single_value",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attribute_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attribute_definitions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    value_string: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_integer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    document: Mapped["Document"] = relationship(  # noqa: F821
        "Document", back_populates="attribute_values"
    )
    attribute_definition: Mapped["AttributeDefinition"] = relationship(
        "AttributeDefinition", back_populates="document_values"
    )
