"""Compliance standard and requirement catalog models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Standard(Base):
    __tablename__ = "standards"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_standards_code_version"),
        Index("ix_standards_code", "code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    requirements: Mapped[list["StandardRequirement"]] = relationship(
        "StandardRequirement", back_populates="standard", cascade="all, delete-orphan"
    )


class StandardRequirement(Base):
    __tablename__ = "standard_requirements"
    __table_args__ = (
        UniqueConstraint("standard_id", "clause_key", name="uq_standard_requirement_clause"),
        Index("ix_standard_requirements_standard_id", "standard_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("standards.id"), nullable=False
    )
    clause_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    standard: Mapped[Standard] = relationship("Standard", back_populates="requirements")
