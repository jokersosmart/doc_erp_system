"""Import scanning endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.error import ErrorResponse
from app.schemas.imports import (
    NarwhalBatchImportRequest,
    NarwhalBatchImportResponse,
    NarwhalImportDocumentRequest,
    NarwhalImportDocumentResponse,
    NarwhalScanRequest,
    NarwhalScanResponse,
)
from app.services.narwhal_import_service import NarwhalImportService

router = APIRouter(prefix="/imports", tags=["Imports"])


@router.post(
    "/narwhal/scan",
    response_model=NarwhalScanResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def scan_narwhal_workspace(payload: NarwhalScanRequest) -> NarwhalScanResponse:
    service = NarwhalImportService()
    return service.scan_workspace(
        config_path=payload.config_path,
        process_keys=payload.process_keys,
        include_disabled=payload.include_disabled,
    )


@router.post(
    "/narwhal/documents",
    response_model=NarwhalImportDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def import_narwhal_document(
    payload: NarwhalImportDocumentRequest,
    db: AsyncSession = Depends(get_db),
) -> NarwhalImportDocumentResponse:
    service = NarwhalImportService()
    response = await service.import_document(
        session=db,
        config_path=payload.config_path,
        process_key=payload.process_key,
        relative_path=payload.relative_path,
        project_id=payload.project_id,
        owner_id=payload.owner_id,
        partition_id=payload.partition_id,
        standards_scope=payload.standards_scope,
        trace_link_mode=payload.trace_link_mode,
        relationship_strategy=payload.relationship_strategy,
        relationship_type=payload.relationship_type,
    )
    await db.commit()
    return response


@router.post(
    "/narwhal/documents/batch",
    response_model=NarwhalBatchImportResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def batch_import_narwhal_documents(
    payload: NarwhalBatchImportRequest,
    db: AsyncSession = Depends(get_db),
) -> NarwhalBatchImportResponse:
    service = NarwhalImportService()
    response = await service.import_documents(
        session=db,
        config_path=payload.config_path,
        project_id=payload.project_id,
        owner_id=payload.owner_id,
        partition_id=payload.partition_id,
        standards_scope=payload.standards_scope,
        process_keys=payload.process_keys,
        relative_paths=payload.relative_paths,
        include_disabled=payload.include_disabled,
        trace_link_mode=payload.trace_link_mode,
        relationship_strategy=payload.relationship_strategy,
        relationship_type=payload.relationship_type,
    )
    await db.commit()
    return response
