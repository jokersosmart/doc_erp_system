"""Export endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.error import ErrorResponse
from app.schemas.export import CreateExportRequest, ExportJobResponse
from app.services.export_service import ExportService

router = APIRouter(prefix="/exports", tags=["Export"])


@router.post("", response_model=ExportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    payload: CreateExportRequest,
    db: AsyncSession = Depends(get_db),
) -> ExportJobResponse:
    service = ExportService(session=db)
    job = await service.create_export_job(
        project_id=payload.project_id,
        mapping_profile=payload.mapping_profile,
    )
    issues = await service.list_export_issues(job_id=job.id)
    await db.commit()
    await db.refresh(job)
    return ExportJobResponse.from_job(job=job, issues=issues)


@router.get("/{jobId}", response_model=ExportJobResponse, responses={404: {"model": ErrorResponse}})
async def get_export(
    jobId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ExportJobResponse:
    service = ExportService(session=db)
    job = await service.get_export_job(job_id=jobId)
    issues = await service.list_export_issues(job_id=job.id)
    return ExportJobResponse.from_job(job=job, issues=issues)
