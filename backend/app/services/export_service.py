"""Export package assembly service."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.ai_review import JobStatus
from app.models.export_job import ExportArtifact, ExportArtifactType, ExportIssue, ExportJob
from app.services.export_validation_service import ExportValidationService


class ExportService:
    def __init__(
        self,
        session: AsyncSession,
        validation_service: ExportValidationService | None = None,
    ) -> None:
        self._session = session
        self._validation_service = validation_service or ExportValidationService()

    async def create_export_job(
        self,
        *,
        project_id: uuid.UUID,
        mapping_profile: str,
    ) -> ExportJob:
        job = ExportJob(
            project_id=project_id,
            mapping_profile=mapping_profile,
            status=JobStatus.RUNNING,
        )
        self._session.add(job)
        await self._session.flush()

        artifact_types = {
            ExportArtifactType.MANIFEST,
            ExportArtifactType.DOCUMENT_BUNDLE,
            ExportArtifactType.VALIDATION_REPORT,
        }

        for artifact_type in artifact_types:
            payload = f"{job.id}:{artifact_type.value}".encode("utf-8")
            checksum = hashlib.sha256(payload).hexdigest()
            artifact = ExportArtifact(
                export_job_id=job.id,
                artifact_type=artifact_type,
                storage_path=f"backend/storage/audit_packages/{job.id}/{artifact_type.value.lower()}.json",
                checksum_sha256=checksum,
            )
            self._session.add(artifact)

        issues = self._validation_service.validate_mapping_completeness(
            mapping_profile=mapping_profile,
            artifact_types=artifact_types,
        )
        for issue in issues:
            self._session.add(
                ExportIssue(
                    export_job_id=job.id,
                    issue_code=issue.issue_code,
                    severity=issue.severity,
                    entity_ref=issue.entity_ref,
                    message=issue.message,
                )
            )

        job.status = JobStatus.PARTIAL if issues else JobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        await self._session.flush()
        return job

    async def get_export_job(self, *, job_id: uuid.UUID) -> ExportJob:
        job = await self._session.get(ExportJob, job_id)
        if job is None:
            raise NotFoundError("Export job not found")
        return job

    async def list_export_issues(self, *, job_id: uuid.UUID) -> list[ExportIssue]:
        result = await self._session.execute(
            select(ExportIssue)
            .where(ExportIssue.export_job_id == job_id)
            .order_by(ExportIssue.created_at.asc())
        )
        return list(result.scalars().all())
