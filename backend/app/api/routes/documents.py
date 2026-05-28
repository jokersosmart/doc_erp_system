"""Document lifecycle endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.documents import (
    CreateDocumentRequest,
    DocumentResponse,
    MarkdownConversionResponse,
    LifecycleTransitionRequest,
    UpdateDocumentRequest,
)
from app.schemas.error import ErrorResponse
from app.services.document_conversion_service import DocumentConversionService
from app.services.document_lifecycle_service import DocumentLifecycleService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/convert", response_model=MarkdownConversionResponse)
async def convert_document_to_markdown(file: UploadFile = File(...)) -> MarkdownConversionResponse:
    service = DocumentConversionService()
    result = service.convert_stream(
        file_stream=file.file,
        filename=file.filename,
        content_type=file.content_type,
    )

    return MarkdownConversionResponse(
        source_filename=result.source_filename,
        title=result.title,
        markdown=result.markdown,
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: CreateDocumentRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    service = DocumentLifecycleService(session=db)
    document = await service.create_document(
        project_id=payload.project_id,
        owner_id=payload.owner_id,
        partition_id=payload.partition_id,
        title=payload.title,
        document_type=payload.document_type,
        content_markdown=payload.content_markdown,
        standards_scope=payload.standards_scope,
    )
    await db.commit()
    await db.refresh(document)

    return DocumentResponse.from_document(document=document)


@router.get(
    "/{documentId}",
    response_model=DocumentResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_document(
    documentId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    service = DocumentLifecycleService(session=db)
    document = await service.get_document(document_id=documentId)

    return DocumentResponse.from_document(document=document)


@router.put(
    "/{documentId}",
    response_model=DocumentResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def update_document(
    documentId: uuid.UUID,
    payload: UpdateDocumentRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    service = DocumentLifecycleService(session=db)
    document = await service.update_document(
        document_id=documentId,
        expected_version=payload.expected_version,
        content_markdown=payload.content_markdown,
        actor_user_id=None,
    )
    await db.commit()
    await db.refresh(document)

    return DocumentResponse.from_document(document=document)


@router.post("/{documentId}/transitions", response_model=DocumentResponse)
async def transition_document(
    documentId: uuid.UUID,
    payload: LifecycleTransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    service = DocumentLifecycleService(session=db)
    document = await service.transition_document(
        document_id=documentId,
        to_state=payload.to_state,
        actor_user_id=None,
        rationale=payload.rationale,
        attributes=[],
    )
    await db.commit()
    await db.refresh(document)

    return DocumentResponse.from_document(document=document)
