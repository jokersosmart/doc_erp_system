"""Add export jobs, artifacts, and validation issues.

Revision ID: 0006_export_jobs_and_artifacts
Revises: 0005_ai_review_and_compliance
Create Date: 2026-05-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0006_export_jobs_and_artifacts"
down_revision = "0005_ai_review_and_compliance"
branch_labels = None
depends_on = None


job_status_enum = sa.Enum(
    "QUEUED",
    "RUNNING",
    "PARTIAL",
    "COMPLETED",
    "FAILED",
    "RETRYABLE",
    name="jobstatus",
    create_type=False,
)
export_artifact_type_enum = sa.Enum(
    "MANIFEST",
    "DOCUMENT_BUNDLE",
    "TRACEABILITY",
    "COMPLIANCE",
    "VALIDATION_REPORT",
    name="exportartifacttype",
)
export_issue_severity_enum = sa.Enum("ERROR", "WARNING", name="exportissueseverity")


def upgrade() -> None:
    export_artifact_type_enum.create(op.get_bind(), checkfirst=True)
    export_issue_severity_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mapping_profile", sa.String(length=120), nullable=False),
        sa.Column("status", job_status_enum, nullable=False, server_default="QUEUED"),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_jobs_project_id", "export_jobs", ["project_id"])
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"])
    op.create_index("ix_export_jobs_requested_at", "export_jobs", ["requested_at"])

    op.create_table(
        "export_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("export_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", export_artifact_type_enum, nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["export_job_id"], ["export_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_artifacts_export_job_id", "export_artifacts", ["export_job_id"])

    op.create_table(
        "export_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("export_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issue_code", sa.String(length=120), nullable=False),
        sa.Column("severity", export_issue_severity_enum, nullable=False),
        sa.Column("entity_ref", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["export_job_id"], ["export_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_issues_export_job_id", "export_issues", ["export_job_id"])


def downgrade() -> None:
    op.drop_index("ix_export_issues_export_job_id", table_name="export_issues")
    op.drop_table("export_issues")

    op.drop_index("ix_export_artifacts_export_job_id", table_name="export_artifacts")
    op.drop_table("export_artifacts")

    op.drop_index("ix_export_jobs_requested_at", table_name="export_jobs")
    op.drop_index("ix_export_jobs_status", table_name="export_jobs")
    op.drop_index("ix_export_jobs_project_id", table_name="export_jobs")
    op.drop_table("export_jobs")

    export_issue_severity_enum.drop(op.get_bind(), checkfirst=True)
    export_artifact_type_enum.drop(op.get_bind(), checkfirst=True)
