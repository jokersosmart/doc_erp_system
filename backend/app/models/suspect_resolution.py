"""Suspect resolution ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SuspectResolution(Base):
    __tablename__ = "suspect_resolutions"
    __table_args__ = (
        Index("ix_suspect_resolutions_dependency_link_id", "dependency_link_id"),
        Index("ix_suspect_resolutions_resolved_at", "resolved_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dependency_link_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dependency_links.id"), nullable=False
    )
    resolution_type: Mapped[str] = mapped_column(String(30), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dependency_link: Mapped["DependencyLink"] = relationship(
        "DependencyLink", back_populates="suspect_resolutions"
    )
