"""ORM model: LockEvent — cascade lock history (FR-015, FR-041)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class LockEvent(Base):
    """
    Records each cascade lock trigger event.

    Scope: BU-scoped (FR-041) — only documents within the same bu_node subtree are locked.
    The locked_document_ids UUID array tracks which documents were atomically locked.
    """

    __tablename__ = "lock_events"
    __table_args__ = (
        Index("ix_lock_events_upstream_document_id", "upstream_document_id"),
        Index("ix_lock_events_bu_node_id", "bu_node_id"),
        Index("ix_lock_events_triggered_at", "triggered_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upstream_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    bu_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisation_nodes.id"), nullable=True
    )
    locked_document_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    upstream_version_at_lock: Mapped[int | None] = mapped_column(nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    upstream_document: Mapped["Document"] = relationship(  # type: ignore[name-defined]
        "Document",
        foreign_keys=[upstream_document_id],
        back_populates="lock_events_triggered",
    )
