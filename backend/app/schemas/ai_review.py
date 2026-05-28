"""AI review API request and response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.ai_review import FindingSeverity, JobStatus, SuggestionDecision


class CreateAIReviewRequest(BaseModel):
    document_id: uuid.UUID
    revision_id: uuid.UUID
    standards: list[str]


class AIReviewFindingResponse(BaseModel):
    id: uuid.UUID
    clause_key: str | None = None
    severity: FindingSeverity
    finding_text: str
    suggestion_before: str | None = None
    suggestion_after: str | None = None

    @classmethod
    def from_finding(cls, *, finding) -> "AIReviewFindingResponse":
        return cls(
            id=finding.id,
            clause_key=finding.clause_key,
            severity=finding.severity,
            finding_text=finding.finding_text,
            suggestion_before=finding.suggestion_before,
            suggestion_after=finding.suggestion_after,
        )


class AIReviewJobResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    revision_id: uuid.UUID
    status: JobStatus
    accepted_at: datetime | None = None
    first_result_at: datetime | None = None
    completed_at: datetime | None = None
    findings: list[AIReviewFindingResponse] = []
    error_message: str | None = None

    @classmethod
    def from_job(cls, *, job, findings: list[object]) -> "AIReviewJobResponse":
        return cls(
            id=job.id,
            document_id=job.document_id,
            revision_id=job.revision_id,
            status=job.status,
            accepted_at=job.accepted_at,
            first_result_at=job.first_result_at,
            completed_at=job.completed_at,
            findings=[AIReviewFindingResponse.from_finding(finding=finding) for finding in findings],
            error_message=job.error_message,
        )


class SuggestionDecisionRequest(BaseModel):
    decision: SuggestionDecision
    rationale: str | None = None


class SuggestionDecisionResponse(BaseModel):
    suggestion_id: uuid.UUID
    decision: SuggestionDecision
    rationale: str | None = None
    decided_at: datetime

    @classmethod
    def from_decision(cls, *, decision) -> "SuggestionDecisionResponse":
        return cls(
            suggestion_id=decision.suggestion_id,
            decision=decision.decision,
            rationale=decision.rationale,
            decided_at=decision.decided_at,
        )
