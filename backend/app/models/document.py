"""Document and DocumentVersion ORM models."""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

VALID_STATUSES = ("DRAFT", "REVIEW", "APPROVED", "OBSOLETE")


class Document(Base):
    """Core document entity with state machine and optimistic locking."""

    __tablename__ = "documents"

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'REVIEW', 'APPROVED', 'OBSOLETE')",
            name="ck_documents_status",
        ),
        CheckConstraint(
            "length(trim(content_md)) > 0",
            name="ck_documents_content_not_empty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    partition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("partitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Optimistic locking column
    version_lock: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
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
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project", back_populates="documents"
    )
    partition: Mapped["Partition"] = relationship(  # noqa: F821
        "Partition", back_populates="documents"
    )
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.created_at.desc()",
    )
    attribute_values: Mapped[list["DocumentAttributeValue"]] = relationship(  # noqa: F821
        "DocumentAttributeValue",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # noqa: F821
        "AuditLog",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    # Traceability links where this doc is the source
    source_links: Mapped[list["TraceabilityLink"]] = relationship(  # noqa: F821
        "TraceabilityLink",
        foreign_keys="TraceabilityLink.source_document_id",
        back_populates="source_document",
    )
    # Traceability links where this doc is the target
    target_links: Mapped[list["TraceabilityLink"]] = relationship(  # noqa: F821
        "TraceabilityLink",
        foreign_keys="TraceabilityLink.target_document_id",
        back_populates="target_document",
    )


class DocumentVersion(Base):
    """Snapshot of a document at a specific version."""

    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    modified_by: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="versions"
    )
