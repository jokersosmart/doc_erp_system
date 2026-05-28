"""Add dependency health tracking and suspect resolution records.

Revision ID: 0004_traceability_suspect_management
Revises: 0003_document_lifecycle_and_eav
Create Date: 2026-05-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0004_traceability_suspect_management"
down_revision = "0003_document_lifecycle_and_eav"
branch_labels = None
depends_on = None


dependency_health_state_enum = sa.Enum(
    "HEALTHY",
    "SUSPECT",
    "RESOLVED",
    name="dependencyhealthstate",
)


def upgrade() -> None:
    dependency_health_state_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "dependency_links",
        sa.Column(
            "health_state",
            dependency_health_state_enum,
            nullable=False,
            server_default="HEALTHY",
        ),
    )
    op.add_column("dependency_links", sa.Column("suspect_reason", sa.Text(), nullable=True))
    op.add_column(
        "dependency_links",
        sa.Column("last_health_transition_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "dependency_links",
        sa.Column("last_health_transition_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_dependency_links_last_health_transition_by_users",
        "dependency_links",
        "users",
        ["last_health_transition_by"],
        ["id"],
    )
    op.create_index(
        "ix_dep_links_target_health_state",
        "dependency_links",
        ["target_item_id", "health_state"],
    )
    op.create_index(
        "ix_dep_links_source_health_state",
        "dependency_links",
        ["source_item_id", "health_state"],
    )

    op.create_table(
        "suspect_resolutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dependency_link_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resolution_type", sa.String(length=30), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dependency_link_id"], ["dependency_links.id"]),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_suspect_resolutions_dependency_link_id",
        "suspect_resolutions",
        ["dependency_link_id"],
    )
    op.create_index(
        "ix_suspect_resolutions_resolved_at",
        "suspect_resolutions",
        ["resolved_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_suspect_resolutions_resolved_at", table_name="suspect_resolutions")
    op.drop_index("ix_suspect_resolutions_dependency_link_id", table_name="suspect_resolutions")
    op.drop_table("suspect_resolutions")

    op.drop_index("ix_dep_links_source_health_state", table_name="dependency_links")
    op.drop_index("ix_dep_links_target_health_state", table_name="dependency_links")
    op.drop_constraint(
        "fk_dependency_links_last_health_transition_by_users",
        "dependency_links",
        type_="foreignkey",
    )
    op.drop_column("dependency_links", "last_health_transition_by")
    op.drop_column("dependency_links", "last_health_transition_at")
    op.drop_column("dependency_links", "suspect_reason")
    op.drop_column("dependency_links", "health_state")

    dependency_health_state_enum.drop(op.get_bind(), checkfirst=True)
