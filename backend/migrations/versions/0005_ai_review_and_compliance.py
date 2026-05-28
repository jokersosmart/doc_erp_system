"""Add AI review workflow and compliance records.

Revision ID: 0005_ai_review_and_compliance
Revises: 0004_traceability_suspect_management
Create Date: 2026-05-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005_ai_review_and_compliance"
down_revision = "0004_traceability_suspect_management"
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
)
finding_severity_enum = sa.Enum("INFO", "WARNING", "MAJOR", name="findingseverity")
suggestion_decision_enum = sa.Enum("ACCEPTED", "REJECTED", name="suggestiondecision")


def upgrade() -> None:
    job_status_enum.create(op.get_bind(), checkfirst=True)
    finding_severity_enum.create(op.get_bind(), checkfirst=True)
    suggestion_decision_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "compliance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("standard_code", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("gap_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["document_revisions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compliance_records_document_id", "compliance_records", ["document_id"])
    op.create_index("ix_compliance_records_revision_id", "compliance_records", ["revision_id"])

    op.create_table(
        "ai_review_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", job_status_enum, nullable=False, server_default="QUEUED"),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_result_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["document_revisions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_review_jobs_document_id", "ai_review_jobs", ["document_id"])
    op.create_index("ix_ai_review_jobs_revision_id", "ai_review_jobs", ["revision_id"])
    op.create_index("ix_ai_review_jobs_status", "ai_review_jobs", ["status"])

    op.create_table(
        "ai_review_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clause_key", sa.String(length=120), nullable=True),
        sa.Column("severity", finding_severity_enum, nullable=False),
        sa.Column("finding_text", sa.Text(), nullable=False),
        sa.Column("suggestion_before", sa.Text(), nullable=True),
        sa.Column("suggestion_after", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["ai_review_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_review_findings_job_id", "ai_review_findings", ["job_id"])
    op.create_index("ix_ai_review_findings_clause_key", "ai_review_findings", ["clause_key"])

    op.create_table(
        "ai_suggestion_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suggestion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", suggestion_decision_enum, nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["ai_review_jobs.id"]),
        sa.ForeignKeyConstraint(["suggestion_id"], ["ai_review_findings.id"]),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("suggestion_id", name="uq_ai_suggestion_decision_suggestion"),
    )
    op.create_index("ix_ai_suggestion_decisions_job_id", "ai_suggestion_decisions", ["job_id"])
    op.create_index(
        "ix_ai_suggestion_decisions_suggestion_id",
        "ai_suggestion_decisions",
        ["suggestion_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_suggestion_decisions_suggestion_id", table_name="ai_suggestion_decisions")
    op.drop_index("ix_ai_suggestion_decisions_job_id", table_name="ai_suggestion_decisions")
    op.drop_table("ai_suggestion_decisions")

    op.drop_index("ix_ai_review_findings_clause_key", table_name="ai_review_findings")
    op.drop_index("ix_ai_review_findings_job_id", table_name="ai_review_findings")
    op.drop_table("ai_review_findings")

    op.drop_index("ix_ai_review_jobs_status", table_name="ai_review_jobs")
    op.drop_index("ix_ai_review_jobs_revision_id", table_name="ai_review_jobs")
    op.drop_index("ix_ai_review_jobs_document_id", table_name="ai_review_jobs")
    op.drop_table("ai_review_jobs")

    op.drop_index("ix_compliance_records_revision_id", table_name="compliance_records")
    op.drop_index("ix_compliance_records_document_id", table_name="compliance_records")
    op.drop_table("compliance_records")

    suggestion_decision_enum.drop(op.get_bind(), checkfirst=True)
    finding_severity_enum.drop(op.get_bind(), checkfirst=True)
    job_status_enum.drop(op.get_bind(), checkfirst=True)
