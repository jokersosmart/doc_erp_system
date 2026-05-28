"""Add document lifecycle history and dynamic attribute schema.

Revision ID: 0003_document_lifecycle_and_eav
Revises: 0002_audit_and_notifications
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003_document_lifecycle_and_eav"
down_revision = "0002_audit_and_notifications"
branch_labels = None
depends_on = None


lifecycle_state_enum = sa.Enum(
    "DRAFT",
    "REVIEW",
    "APPROVED",
    "OBSOLETE",
    name="lifecyclestate",
    create_type=False,
)
attribute_data_type_enum = sa.Enum(
    "STRING",
    "INTEGER",
    "BOOLEAN",
    "ENUM",
    "DATE",
    name="attributedatatype",
)


def upgrade() -> None:
    attribute_data_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "documents",
        sa.Column(
            "standards_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("documents", sa.Column("last_transition_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "document_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("lifecycle_state_at_snapshot", lifecycle_state_enum, nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("version_number > 0", name="ck_document_revision_positive_version"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_revision_version"),
    )
    op.create_index("ix_document_revisions_document_id", "document_revisions", ["document_id"])

    op.create_table(
        "document_transition_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_state", lifecycle_state_enum, nullable=False),
        sa.Column("to_state", lifecycle_state_enum, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("validation_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_doc_transition_events_document_id",
        "document_transition_events",
        ["document_id"],
    )
    op.create_index(
        "ix_doc_transition_events_created_at",
        "document_transition_events",
        ["created_at"],
    )

    op.create_table(
        "standards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "version", name="uq_standards_code_version"),
    )
    op.create_index("ix_standards_code", "standards", ["code"])

    op.create_table(
        "standard_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("standard_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clause_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["standard_id"], ["standards.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("standard_id", "clause_key", name="uq_standard_requirement_clause"),
    )
    op.create_index(
        "ix_standard_requirements_standard_id",
        "standard_requirements",
        ["standard_id"],
    )

    op.create_table(
        "attribute_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("data_type", attribute_data_type_enum, nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("standard_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("partition_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("allowed_values_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_rule_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["partition_node_id"], ["organisation_nodes.id"]),
        sa.ForeignKeyConstraint(["standard_id"], ["standards.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "standard_id", "partition_node_id", name="uq_attribute_definition_scope"),
    )
    op.create_index(
        "ix_attribute_definitions_partition_node_id",
        "attribute_definitions",
        ["partition_node_id"],
    )
    op.create_index("ix_attribute_definitions_standard_id", "attribute_definitions", ["standard_id"])

    op.create_table(
        "document_attribute_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attribute_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("value_string", sa.String(length=500), nullable=True),
        sa.Column("value_integer", sa.Integer(), nullable=True),
        sa.Column("value_boolean", sa.Boolean(), nullable=True),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["attribute_definition_id"], ["attribute_definitions.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["document_revisions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id", "attribute_definition_id", name="uq_document_attr_value"),
    )
    op.create_index(
        "ix_document_attribute_values_document_id",
        "document_attribute_values",
        ["document_id"],
    )
    op.create_index(
        "ix_document_attribute_values_revision_id",
        "document_attribute_values",
        ["revision_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_attribute_values_revision_id", table_name="document_attribute_values")
    op.drop_index("ix_document_attribute_values_document_id", table_name="document_attribute_values")
    op.drop_table("document_attribute_values")

    op.drop_index("ix_attribute_definitions_standard_id", table_name="attribute_definitions")
    op.drop_index("ix_attribute_definitions_partition_node_id", table_name="attribute_definitions")
    op.drop_table("attribute_definitions")

    op.drop_index("ix_standard_requirements_standard_id", table_name="standard_requirements")
    op.drop_table("standard_requirements")

    op.drop_index("ix_standards_code", table_name="standards")
    op.drop_table("standards")

    op.drop_index("ix_doc_transition_events_created_at", table_name="document_transition_events")
    op.drop_index("ix_doc_transition_events_document_id", table_name="document_transition_events")
    op.drop_table("document_transition_events")

    op.drop_index("ix_document_revisions_document_id", table_name="document_revisions")
    op.drop_table("document_revisions")

    op.drop_column("documents", "last_transition_at")
    op.drop_column("documents", "standards_scope")

    attribute_data_type_enum.drop(op.get_bind(), checkfirst=True)
