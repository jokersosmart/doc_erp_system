"""Add performance hotspot indexes for workflow-heavy queries.

Revision ID: 0007_performance_hotspot_indexes
Revises: 0006_export_jobs_and_artifacts
Create Date: 2026-05-22
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_performance_hotspot_indexes"
down_revision = "0006_export_jobs_and_artifacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_dep_links_source_rel_health",
        "dependency_links",
        ["source_item_id", "relationship_type", "health_state"],
    )
    op.create_index(
        "ix_doc_transition_events_doc_created_at",
        "document_transition_events",
        ["document_id", "created_at"],
    )
    op.create_index(
        "ix_ai_review_jobs_status_accepted_at",
        "ai_review_jobs",
        ["status", "accepted_at"],
    )
    op.create_index(
        "ix_export_jobs_status_completed_at",
        "export_jobs",
        ["status", "completed_at"],
    )
    op.create_index(
        "ix_notifications_recipient_unread_created",
        "notifications",
        ["recipient_user_id", "is_read", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_recipient_unread_created", table_name="notifications")
    op.drop_index("ix_export_jobs_status_completed_at", table_name="export_jobs")
    op.drop_index("ix_ai_review_jobs_status_accepted_at", table_name="ai_review_jobs")
    op.drop_index("ix_doc_transition_events_doc_created_at", table_name="document_transition_events")
    op.drop_index("ix_dep_links_source_rel_health", table_name="dependency_links")
