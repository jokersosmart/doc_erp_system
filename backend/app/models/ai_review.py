"""AI review workflow ORM models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PARTIAL = "PARTIAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYABLE = "RETRYABLE"


class FindingSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    MAJOR = "MAJOR"


class SuggestionDecision(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class AIReviewJob(Base):
    __tablename__ = "ai_review_jobs"
    __table_args__ = (
        Index("ix_ai_review_jobs_document_id", "document_id"),
        Index("ix_ai_review_jobs_revision_id", "revision_id"),
        Index("ix_ai_review_jobs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_revisions.id"), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.QUEUED)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_result_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    findings: Mapped[list[AIReviewFinding]] = relationship(
        "AIReviewFinding", back_populates="job", cascade="all, delete-orphan"
    )
    decisions: Mapped[list[AISuggestionDecision]] = relationship(
        "AISuggestionDecision", back_populates="job", cascade="all, delete-orphan"
    )


class AIReviewFinding(Base):
    __tablename__ = "ai_review_findings"
    __table_args__ = (
        Index("ix_ai_review_findings_job_id", "job_id"),
        Index("ix_ai_review_findings_clause_key", "clause_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_review_jobs.id"), nullable=False
    )
    clause_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    severity: Mapped[FindingSeverity] = mapped_column(Enum(FindingSeverity), nullable=False)
    finding_text: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestion_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[AIReviewJob] = relationship("AIReviewJob", back_populates="findings")


class AISuggestionDecision(Base):
    __tablename__ = "ai_suggestion_decisions"
    __table_args__ = (
        Index("ix_ai_suggestion_decisions_job_id", "job_id"),
        Index("ix_ai_suggestion_decisions_suggestion_id", "suggestion_id"),
        UniqueConstraint("suggestion_id", name="uq_ai_suggestion_decision_suggestion"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_review_jobs.id"), nullable=False
    )
    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_review_findings.id"), nullable=False
    )
    decision: Mapped[SuggestionDecision] = mapped_column(Enum(SuggestionDecision), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[AIReviewJob] = relationship("AIReviewJob", back_populates="decisions")
