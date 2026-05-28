"""Dashboard summary aggregation service."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_review import JobStatus
from app.models.compliance import ComplianceRecord
from app.models.document import Document, LifecycleState
from app.models.export_job import ExportJob
from app.models.spec_item import DependencyHealthState, DependencyLink
from app.schemas.export import DashboardSummaryResponse


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_summary(self) -> DashboardSummaryResponse:
        open_suspect_result = await self._session.execute(
            select(func.count()).select_from(DependencyLink).where(
                DependencyLink.health_state == DependencyHealthState.SUSPECT
            )
        )
        pending_review_result = await self._session.execute(
            select(func.count()).select_from(Document).where(
                Document.lifecycle_state == LifecycleState.REVIEW
            )
        )
        compliance_gap_result = await self._session.execute(
            select(func.coalesce(func.sum(ComplianceRecord.gap_count), 0)).select_from(ComplianceRecord)
        )
        export_ready_result = await self._session.execute(
            select(func.count()).select_from(ExportJob).where(ExportJob.status == JobStatus.COMPLETED)
        )

        return DashboardSummaryResponse(
            open_suspect_count=int(open_suspect_result.scalar_one()),
            pending_review_count=int(pending_review_result.scalar_one()),
            compliance_gap_count=int(compliance_gap_result.scalar_one()),
            export_ready_count=int(export_ready_result.scalar_one()),
        )
