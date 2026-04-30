"""ORM models: AuditTrailEntry, NotificationRecord, ComplianceCheckResult, AuditPackage."""
import uuid
from datetime import datetime
from typing import Any

import enum
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


class AuditTrailEntry(Base):
    """Immutable audit log entry — authorship, AI acceptance, lock events (FR-008)."""

    __tablename__ = "audit_trail_entries"
    __table_args__ = (
        Index("ix_audit_trail_document_id", "document_id"),
        Index("ix_audit_trail_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # ai_suggestion_accepted | lock_applied | lifecycle_changed | emergency_override | …
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    git_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NotificationRecord(Base):
    """Per-user notification record (FR-046 — in-app mandatory, email best-effort)."""

    __tablename__ = "notification_records"
    __table_args__ = (
        Index("ix_notif_records_recipient_id", "recipient_id"),
        Index("ix_notif_records_is_read", "is_read"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    related_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_failed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # FR-046 — silently logged failure
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ComplianceCheckResult(Base):
    """Result of a one-click compliance check run (FR-023)."""

    __tablename__ = "compliance_check_results"
    __table_args__ = (Index("ix_compliance_check_project_id", "project_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    standards_checked: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )  # ["ASPICE", "ISO-26262", "ISO-21434"]
    gap_list: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    total_gaps: Mapped[int] = mapped_column(nullable=False, default=0)
    audit_package_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_packages.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    audit_package: Mapped["AuditPackage | None"] = relationship(
        "AuditPackage", back_populates="compliance_check_results"
    )


class AuditPackage(Base):
    """
    Immutable audit export record — all historical packages retained (FR-045).
    Filename convention: <project-id>_audit_<YYYY-MM-DD>_<HHmm>_<username>.xlsx
    """

    __tablename__ = "audit_packages"
    __table_args__ = (
        Index("ix_audit_packages_project_id", "project_id"),
        Index("ix_audit_packages_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    standards_scope: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    xlsx_validation_issues: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )  # FR-044 — warnings report; None = passed validation
    issues_pdf_path: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # FR-044 — issues PDF if validation_issues present
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    compliance_check_results: Mapped[list["ComplianceCheckResult"]] = relationship(
        "ComplianceCheckResult", back_populates="audit_package"
    )
