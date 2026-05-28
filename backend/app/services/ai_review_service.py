"""AI review job lifecycle service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.models.ai_review import AIReviewFinding, AIReviewJob, FindingSeverity, JobStatus


class AIReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_review_job(
        self,
        *,
        document_id: uuid.UUID,
        revision_id: uuid.UUID,
        standards: list[str],
    ) -> AIReviewJob:
        now = datetime.now(UTC)
        job = AIReviewJob(
            document_id=document_id,
            revision_id=revision_id,
            status=JobStatus.QUEUED,
            accepted_at=now,
        )
        self._session.add(job)
        await self._session.flush()

        if standards:
            finding = AIReviewFinding(
                job_id=job.id,
                clause_key=standards[0],
                severity=FindingSeverity.INFO,
                finding_text="AI review request accepted and queued.",
                suggestion_before=None,
                suggestion_after=None,
            )
            self._session.add(finding)
            job.first_result_at = now
            job.status = JobStatus.PARTIAL

        return job

    async def get_review_job(self, *, job_id: uuid.UUID) -> AIReviewJob:
        job = await self._session.get(AIReviewJob, job_id)
        if job is None:
            raise NotFoundError("AI review job not found")
        return job

    async def list_job_findings(self, *, job_id: uuid.UUID) -> list[AIReviewFinding]:
        result = await self._session.execute(
            select(AIReviewFinding)
            .where(AIReviewFinding.job_id == job_id)
            .order_by(AIReviewFinding.created_at.asc())
        )
        return list(result.scalars().all())

    async def mark_running(self, *, job_id: uuid.UUID) -> AIReviewJob:
        job = await self.get_review_job(job_id=job_id)
        if job.status not in {JobStatus.QUEUED, JobStatus.RETRYABLE}:
            raise ValidationError("Job can only move to RUNNING from QUEUED or RETRYABLE")
        job.status = JobStatus.RUNNING
        await self._session.flush()
        return job

    async def mark_partial(
        self,
        *,
        job_id: uuid.UUID,
        clause_key: str | None,
        finding_text: str,
    ) -> AIReviewJob:
        job = await self.get_review_job(job_id=job_id)
        if job.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
            raise ValidationError("Job can only move to PARTIAL from QUEUED or RUNNING")

        finding = AIReviewFinding(
            job_id=job.id,
            clause_key=clause_key,
            severity=FindingSeverity.WARNING,
            finding_text=finding_text,
        )
        self._session.add(finding)

        now = datetime.now(UTC)
        job.status = JobStatus.PARTIAL
        if job.first_result_at is None:
            job.first_result_at = now
        await self._session.flush()
        return job

    async def mark_retryable(self, *, job_id: uuid.UUID, error_message: str) -> AIReviewJob:
        job = await self.get_review_job(job_id=job_id)
        if job.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
            raise ValidationError("Job can only move to RETRYABLE from QUEUED or RUNNING")
        job.status = JobStatus.RETRYABLE
        job.error_message = error_message
        await self._session.flush()
        return job
