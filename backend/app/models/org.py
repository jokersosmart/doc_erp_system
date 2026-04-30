"""ORM models: OrganisationNode, Project, User, Role, ProjectRoleAssignment, WizardSession."""
import uuid
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class OrganisationNode(Base):
    """Hierarchical org node (up to 5 levels): Company > BU > Process > Dept > Sub-dept."""

    __tablename__ = "organisation_nodes"
    __table_args__ = (
        Index("ix_org_nodes_parent_id", "parent_id"),
        Index("ix_org_nodes_bu_scope", "bu_scope"),
        Index("ix_org_nodes_level", "level"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=Company … 5=Sub-dept
    node_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # company|bu|process|dept|sub_dept
    bu_scope: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # "ssd_controller" | "emmc"
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisation_nodes.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    parent: Mapped["OrganisationNode | None"] = relationship(
        "OrganisationNode", remote_side="OrganisationNode.id", back_populates="children"
    )
    children: Mapped[list["OrganisationNode"]] = relationship(
        "OrganisationNode", back_populates="parent"
    )
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="bu_node")


class Project(Base):
    """Project — anchored to a BU node with compliance standard configuration."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bu_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisation_nodes.id"), nullable=False
    )
    aspice_level: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 | 2 | 3
    asil_level: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # A | B | C | D | QM
    cal_level: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # CAL1 | CAL2 | CAL3 | CAL4
    standards: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    git_backend_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="github"
    )  # gerrit|github|gitlab
    git_repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    bu_node: Mapped["OrganisationNode"] = relationship("OrganisationNode", back_populates="projects")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="project")  # type: ignore[name-defined]


class User(Base):
    """User — primary LDAP, local admin fallback (FR-038)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ldap_dn: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_local_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    password_hash: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # bcrypt, local admin only
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="zh-TW")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    role_assignments: Mapped[list["ProjectRoleAssignment"]] = relationship(
        "ProjectRoleAssignment", back_populates="user"
    )
    wizard_sessions: Mapped[list["WizardSession"]] = relationship(
        "WizardSession", back_populates="user"
    )


class Role(Base):
    """Role — permission set stored as JSONB (FR-004)."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    permissions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    assignments: Mapped[list["ProjectRoleAssignment"]] = relationship(
        "ProjectRoleAssignment", back_populates="role"
    )


class ProjectRoleAssignment(Base):
    """Maps a User to a Role within a Project (RBAC, FR-004)."""

    __tablename__ = "project_role_assignments"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_role_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="role_assignments")
    role: Mapped["Role"] = relationship("Role", back_populates="assignments")


class WizardSession(Base):
    """Persists AI onboarding wizard progress per user+project (FR-043)."""

    __tablename__ = "wizard_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answers_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    project_context_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="wizard_sessions")
