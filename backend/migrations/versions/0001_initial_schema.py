"""Initial database schema - all tables.

Revision ID: 0001
Revises:
Create Date: 2025-04-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create projects table (no FK dependencies)
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        sa.UniqueConstraint("name", name="uq_projects_name"),
    )

    # Create standards table (no FK dependencies)
    op.create_table(
        "standards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_standards"),
        sa.UniqueConstraint("name", name="uq_standards_name"),
    )

    # Create refresh_tokens table (no FK dependencies)
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # Create partitions table (depends on projects)
    op.create_table(
        "partitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_partitions"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_partitions_project_id_projects",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "project_id", "name", name="uq_partitions_project_name"
        ),
    )
    op.create_index("ix_partitions_project_id", "partitions", ["project_id"])

    # Create attribute_definitions table (depends on standards)
    op.create_table(
        "attribute_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("data_type", sa.String(20), nullable=False),
        sa.Column("allowed_values", postgresql.JSONB, nullable=True),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("standard_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_attribute_definitions"),
        sa.UniqueConstraint("name", name="uq_attribute_definitions_name"),
        sa.ForeignKeyConstraint(
            ["standard_id"],
            ["standards.id"],
            name="fk_attribute_definitions_standard_id_standards",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "data_type IN ('STRING', 'INTEGER', 'BOOLEAN', 'ENUM')",
            name="ck_attribute_definitions_data_type",
        ),
    )
    op.create_index(
        "ix_attribute_definitions_standard_id",
        "attribute_definitions",
        ["standard_id"],
    )

    # Create documents table (depends on projects, partitions)
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content_md", sa.Text, nullable=False),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("owner_id", sa.String(255), nullable=False),
        sa.Column("version_lock", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_documents_project_id_projects",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["partition_id"],
            ["partitions.id"],
            name="fk_documents_partition_id_partitions",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'REVIEW', 'APPROVED', 'OBSOLETE')",
            name="ck_documents_status",
        ),
        sa.CheckConstraint(
            "length(trim(content_md)) > 0",
            name="ck_documents_content_not_empty",
        ),
    )
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_partition_id", "documents", ["partition_id"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_index("ix_documents_updated_at", "documents", ["updated_at"])

    # Create document_versions table (depends on documents)
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("content_md", sa.Text, nullable=False),
        sa.Column("modified_by", sa.String(255), nullable=False),
        sa.Column("commit_message", sa.String(1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_versions"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_versions_document_id_documents",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_document_versions_document_id", "document_versions", ["document_id"]
    )

    # Create document_attribute_values table (depends on documents, attribute_definitions)
    op.create_table(
        "document_attribute_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attribute_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("value_string", sa.Text, nullable=True),
        sa.Column("value_integer", sa.Integer, nullable=True),
        sa.Column("value_boolean", sa.Boolean, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_attribute_values"),
        sa.UniqueConstraint(
            "document_id",
            "attribute_id",
            name="uq_document_attribute_values_doc_attr",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_attribute_values_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["attribute_id"],
            ["attribute_definitions.id"],
            name="fk_document_attribute_values_attribute_id_attribute_definitions",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(value_string IS NOT NULL)::int + (value_integer IS NOT NULL)::int + "
            "(value_boolean IS NOT NULL)::int <= 1",
            name="ck_document_attribute_values_single_value",
        ),
    )
    op.create_index(
        "ix_document_attribute_values_document_id",
        "document_attribute_values",
        ["document_id"],
    )
    op.create_index(
        "ix_document_attribute_values_attribute_id",
        "document_attribute_values",
        ["attribute_id"],
    )

    # Create audit_logs table (depends on documents)
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operator_id", sa.String(255), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("old_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_audit_logs_document_id_documents",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_audit_logs_document_id", "audit_logs", ["document_id"])

    # Create traceability_links table (depends on documents)
    op.create_table(
        "traceability_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("link_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="VALID"),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_traceability_links"),
        sa.UniqueConstraint(
            "source_document_id",
            "target_document_id",
            "link_type",
            name="uq_traceability_links_source_target_type",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["documents.id"],
            name="fk_traceability_links_source_document_id_documents",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_document_id"],
            ["documents.id"],
            name="fk_traceability_links_target_document_id_documents",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_traceability_links_source_document_id",
        "traceability_links",
        ["source_document_id"],
    )
    op.create_index(
        "ix_traceability_links_target_document_id",
        "traceability_links",
        ["target_document_id"],
    )


def downgrade() -> None:
    op.drop_table("traceability_links")
    op.drop_table("audit_logs")
    op.drop_table("document_attribute_values")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_table("attribute_definitions")
    op.drop_table("partitions")
    op.drop_table("refresh_tokens")
    op.drop_table("standards")
    op.drop_table("projects")
