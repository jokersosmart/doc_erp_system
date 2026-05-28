"""Export and dashboard API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.ai_review import JobStatus
from app.models.export_job import ExportIssueSeverity


class CreateExportRequest(BaseModel):
    project_id: uuid.UUID
    mapping_profile: str


class ExportIssueResponse(BaseModel):
    issue_code: str
    severity: ExportIssueSeverity
    entity_ref: str | None = None
    message: str

    @classmethod
    def from_issue(cls, *, issue) -> "ExportIssueResponse":
        return cls(
            issue_code=issue.issue_code,
            severity=issue.severity,
            entity_ref=issue.entity_ref,
            message=issue.message,
        )


class ExportJobResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    mapping_profile: str
    status: JobStatus
    requested_at: datetime | None = None
    completed_at: datetime | None = None
    artifact_count: int
    issues: list[ExportIssueResponse]

    @classmethod
    def from_job(cls, *, job, issues: list[object]) -> "ExportJobResponse":
        return cls(
            id=job.id,
            project_id=job.project_id,
            mapping_profile=job.mapping_profile,
            status=job.status,
            requested_at=job.requested_at,
            completed_at=job.completed_at,
            artifact_count=len(job.artifacts),
            issues=[ExportIssueResponse.from_issue(issue=issue) for issue in issues],
        )


class DashboardSummaryResponse(BaseModel):
    open_suspect_count: int
    pending_review_count: int
    compliance_gap_count: int
    export_ready_count: int
