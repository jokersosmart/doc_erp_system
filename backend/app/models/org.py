"""Core organization, project, and user ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class OrganisationNode(Base):
    __tablename__ = "organisation_nodes"
    __table_args__ = (
        Index("ix_org_nodes_parent_id", "parent_id"),
        Index("ix_org_nodes_level", "level"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisation_nodes.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bu_scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parent: Mapped[OrganisationNode | None] = relationship(
        "OrganisationNode", remote_side=[id], back_populates="children"
    )
    children: Mapped[list[OrganisationNode]] = relationship(
        "OrganisationNode", back_populates="parent"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bu_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisation_nodes.id"), nullable=True
    )
    git_backend_type: Mapped[str] = mapped_column(String(20), nullable=False, default="github")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="project")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_username", "username"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="zh-TW")
    is_local_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
