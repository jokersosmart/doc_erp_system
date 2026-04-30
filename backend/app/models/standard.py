"""Standard ORM model (ASPICE, ISO-26262, ISO-21434)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Standard(Base):
    """Reference standard definition (e.g., ASPICE 3.1, ISO-26262)."""

    __tablename__ = "standards"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    attribute_definitions: Mapped[list["AttributeDefinition"]] = relationship(  # noqa: F821
        "AttributeDefinition", back_populates="standard"
    )
