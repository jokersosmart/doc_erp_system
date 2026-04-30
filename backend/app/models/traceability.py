"""TraceabilityLink ORM model (schema stub)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TraceabilityLink(Base):
    """Traceability link between documents (schema stub for future use)."""

    __tablename__ = "traceability_links"

    __table_args__ = (
        UniqueConstraint(
            "source_document_id",
            "target_document_id",
            "link_type",
            name="uq_traceability_links_source_target_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    target_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    link_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="VALID")
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
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
    source_document: Mapped["Document"] = relationship(  # noqa: F821
        "Document",
        foreign_keys=[source_document_id],
        back_populates="source_links",
    )
    target_document: Mapped["Document"] = relationship(  # noqa: F821
        "Document",
        foreign_keys=[target_document_id],
        back_populates="target_links",
    )
