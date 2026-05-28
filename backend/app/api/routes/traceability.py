"""Traceability endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.error import ErrorResponse
from app.schemas.traceability import (
    CreateTraceabilityLinkRequest,
    ImpactAnalysisResponse,
    ResolveSuspectRequest,
    TraceabilityLinkResponse,
)
from app.services.suspect_service import SuspectService
from app.services.traceability_service import TraceabilityService

router = APIRouter(tags=["Traceability"])


@router.post(
    "/traceability/links",
    response_model=TraceabilityLinkResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
async def create_traceability_link(
    payload: CreateTraceabilityLinkRequest,
    db: AsyncSession = Depends(get_db),
) -> TraceabilityLinkResponse:
    service = TraceabilityService(session=db)
    link = await service.create_link(
        source_item_id=payload.source_item_id,
        target_item_id=payload.target_item_id,
        relationship_type=payload.relationship_type,
    )
    await db.commit()
    await db.refresh(link)
    return TraceabilityLinkResponse.from_link(link=link)


@router.get(
    "/documents/{documentId}/impacts",
    response_model=ImpactAnalysisResponse,
)
async def get_impact_analysis(
    documentId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ImpactAnalysisResponse:
    service = TraceabilityService(session=db)
    return await service.get_document_impacts(document_id=documentId)


@router.post(
    "/traceability/links/{linkId}/resolve",
    response_model=TraceabilityLinkResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def resolve_suspect_link(
    linkId: uuid.UUID,
    payload: ResolveSuspectRequest,
    db: AsyncSession = Depends(get_db),
) -> TraceabilityLinkResponse:
    service = SuspectService(session=db)
    link = await service.resolve_suspect(
        link_id=linkId,
        resolution_type=payload.resolution_type,
        rationale=payload.rationale,
        actor_user_id=None,
    )
    await db.commit()
    await db.refresh(link)
    return TraceabilityLinkResponse.from_link(link=link)
