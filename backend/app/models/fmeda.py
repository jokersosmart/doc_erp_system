"""ORM models: FMEDAWorksheet, FailureModeLibrary, FailureModeLibraryAudit (FR-027–030, FR-042)."""
import uuid
from datetime import datetime
from typing import Any

import enum
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class FMEDAWorksheet(Base):
    """
    FMEDA worksheet for ISO-26262 quantitative safety analysis.
    Pins library_version_used at calculation time — historical versions preserved (FR-042e).
    """

    __tablename__ = "fmeda_worksheets"
    __table_args__ = (Index("ix_fmeda_worksheets_project_id", "project_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    component_rows: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    # Computed metrics — stored after calculation
    spfm: Mapped[float | None] = mapped_column(Float, nullable=True)  # Single Point Fault Metric
    lfm: Mapped[float | None] = mapped_column(Float, nullable=True)  # Latent Fault Metric
    pmhf: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # Probabilistic Metric for HW Failure
    asil_target: Mapped[str | None] = mapped_column(String(5), nullable=True)  # A|B|C|D
    threshold_failures: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    library_version_used: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # pinned at calculate time (FR-042e)
    calculation_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # increments per calculation run
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FailureModeLibrary(Base):
    """
    Reusable IC design component failure mode entries (FR-042a/b/c).
    Supports versioned entries; soft-delete via is_active flag.
    """

    __tablename__ = "failure_mode_library"
    __table_args__ = (
        Index("ix_fml_component_type", "component_type"),
        Index("ix_fml_library_version", "library_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # flip-flop|SRAM|Flash|PLL|ADC|DAC|power_reg
    component_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lambda_value: Mapped[float] = mapped_column(Float, nullable=False)  # failure rate per hour
    failure_mode_distribution: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    diagnostic_coverage_default: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    library_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    audit_records: Mapped[list["FailureModeLibraryAudit"]] = relationship(
        "FailureModeLibraryAudit", back_populates="library_entry"
    )


class FailureModeLibraryAudit(Base):
    """Versioned audit record for every FailureModeLibrary mutation (FR-042d)."""

    __tablename__ = "failure_mode_library_audit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    library_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("failure_mode_library.id"), nullable=False
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)  # created|updated|deleted
    snapshot_before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    snapshot_after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    library_entry: Mapped["FailureModeLibrary"] = relationship(
        "FailureModeLibrary", back_populates="audit_records"
    )
