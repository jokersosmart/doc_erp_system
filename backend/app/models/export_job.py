"""Export workflow ORM models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.ai_review import JobStatus


class ExportArtifactType(str, enum.Enum):
    MANIFEST = "MANIFEST"
    DOCUMENT_BUNDLE = "DOCUMENT_BUNDLE"
    TRACEABILITY = "TRACEABILITY"
    COMPLIANCE = "COMPLIANCE"
    VALIDATION_REPORT = "VALIDATION_REPORT"


class ExportIssueSeverity(str, enum.Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class ExportJob(Base):
    __tablename__ = "export_jobs"
    __table_args__ = (
        Index("ix_export_jobs_project_id", "project_id"),
        Index("ix_export_jobs_status", "status"),
        Index("ix_export_jobs_requested_at", "requested_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    mapping_profile: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.QUEUED)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    artifacts: Mapped[list["ExportArtifact"]] = relationship(
        "ExportArtifact", back_populates="export_job", cascade="all, delete-orphan"
    )
    issues: Mapped[list["ExportIssue"]] = relationship(
        "ExportIssue", back_populates="export_job", cascade="all, delete-orphan"
    )


class ExportArtifact(Base):
    __tablename__ = "export_artifacts"
    __table_args__ = (Index("ix_export_artifacts_export_job_id", "export_job_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    export_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("export_jobs.id"), nullable=False
    )
    artifact_type: Mapped[ExportArtifactType] = mapped_column(Enum(ExportArtifactType), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    export_job: Mapped[ExportJob] = relationship("ExportJob", back_populates="artifacts")


class ExportIssue(Base):
    __tablename__ = "export_issues"
    __table_args__ = (Index("ix_export_issues_export_job_id", "export_job_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    export_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("export_jobs.id"), nullable=False
    )
    issue_code: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[ExportIssueSeverity] = mapped_column(Enum(ExportIssueSeverity), nullable=False)
    entity_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    export_job: Mapped[ExportJob] = relationship("ExportJob", back_populates="issues")
