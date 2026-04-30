"""Initial core schema with dependency and lock event tables.

Revision ID: 0001_initial_core_and_lock_events
Revises:
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_core_and_lock_events"
down_revision = None
branch_labels = None
depends_on = None


lifecycle_state_enum = sa.Enum("DRAFT", "REVIEW", "APPROVED", "OBSOLETE", name="lifecyclestate")
lock_state_enum = sa.Enum("UNLOCKED", "LOCKED", "PENDING_QRA", name="lockstate")
dependency_type_enum = sa.Enum("BLOCKING", "BLOCKED_BY", "RELATED", name="dependencyrelationshiptype")


def upgrade() -> None:
    lifecycle_state_enum.create(op.get_bind(), checkfirst=True)
    lock_state_enum.create(op.get_bind(), checkfirst=True)
    dependency_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "organisation_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("bu_scope", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["organisation_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_org_nodes_parent_id", "organisation_nodes", ["parent_id"])
    op.create_index("ix_org_nodes_level", "organisation_nodes", ["level"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.Column("is_local_admin", sa.Boolean(), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("bu_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("git_backend_type", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bu_node_id"], ["organisation_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bu_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("lifecycle_state", lifecycle_state_enum, nullable=False),
        sa.Column("lock_state", lock_state_enum, nullable=False),
        sa.Column("is_safety_critical", sa.Boolean(), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["bu_node_id"], ["organisation_nodes.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_lifecycle_state", "documents", ["lifecycle_state"])
    op.create_index("ix_documents_lock_state", "documents", ["lock_state"])
    op.create_index("ix_documents_bu_node_id", "documents", ["bu_node_id"])

    op.create_table(
        "spec_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_identifier", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spec_items_document_id", "spec_items", ["document_id"])

    op.create_table(
        "dependency_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", dependency_type_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_item_id"], ["spec_items.id"]),
        sa.ForeignKeyConstraint(["target_item_id"], ["spec_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_item_id", "target_item_id", "relationship_type", name="uq_dep_link"),
    )
    op.create_index("ix_dep_links_source_item_id", "dependency_links", ["source_item_id"])
    op.create_index("ix_dep_links_target_item_id", "dependency_links", ["target_item_id"])
    op.create_index("ix_dep_links_relationship_type", "dependency_links", ["relationship_type"])

    op.create_table(
        "lock_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upstream_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bu_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("locked_document_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("upstream_version_at_lock", sa.Integer(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["upstream_document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["bu_node_id"], ["organisation_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lock_events_upstream_document_id", "lock_events", ["upstream_document_id"])
    op.create_index("ix_lock_events_bu_node_id", "lock_events", ["bu_node_id"])
    op.create_index("ix_lock_events_triggered_at", "lock_events", ["triggered_at"])


def downgrade() -> None:
    op.drop_index("ix_lock_events_triggered_at", table_name="lock_events")
    op.drop_index("ix_lock_events_bu_node_id", table_name="lock_events")
    op.drop_index("ix_lock_events_upstream_document_id", table_name="lock_events")
    op.drop_table("lock_events")

    op.drop_index("ix_dep_links_relationship_type", table_name="dependency_links")
    op.drop_index("ix_dep_links_target_item_id", table_name="dependency_links")
    op.drop_index("ix_dep_links_source_item_id", table_name="dependency_links")
    op.drop_table("dependency_links")

    op.drop_index("ix_spec_items_document_id", table_name="spec_items")
    op.drop_table("spec_items")

    op.drop_index("ix_documents_bu_node_id", table_name="documents")
    op.drop_index("ix_documents_lock_state", table_name="documents")
    op.drop_index("ix_documents_lifecycle_state", table_name="documents")
    op.drop_index("ix_documents_project_id", table_name="documents")
    op.drop_table("documents")

    op.drop_table("projects")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_org_nodes_level", table_name="organisation_nodes")
    op.drop_index("ix_org_nodes_parent_id", table_name="organisation_nodes")
    op.drop_table("organisation_nodes")

    dependency_type_enum.drop(op.get_bind(), checkfirst=True)
    lock_state_enum.drop(op.get_bind(), checkfirst=True)
    lifecycle_state_enum.drop(op.get_bind(), checkfirst=True)
