"""AI review endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.ai_review import (
    AIReviewJobResponse,
    CreateAIReviewRequest,
    SuggestionDecisionRequest,
    SuggestionDecisionResponse,
)
from app.schemas.error import ErrorResponse
from app.services.ai_decision_service import AIDecisionService
from app.services.ai_review_service import AIReviewService

router = APIRouter(prefix="/ai/reviews", tags=["AI"])


@router.post("", response_model=AIReviewJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_ai_review(
    payload: CreateAIReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> AIReviewJobResponse:
    service = AIReviewService(session=db)
    job = await service.create_review_job(
        document_id=payload.document_id,
        revision_id=payload.revision_id,
        standards=payload.standards,
    )
    findings = await service.list_job_findings(job_id=job.id)
    await db.commit()
    await db.refresh(job)
    return AIReviewJobResponse.from_job(job=job, findings=findings)


@router.get("/{jobId}", response_model=AIReviewJobResponse, responses={404: {"model": ErrorResponse}})
async def get_ai_review(
    jobId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AIReviewJobResponse:
    service = AIReviewService(session=db)
    job = await service.get_review_job(job_id=jobId)
    findings = await service.list_job_findings(job_id=job.id)
    return AIReviewJobResponse.from_job(job=job, findings=findings)


@router.post(
    "/{jobId}/suggestions/{suggestionId}/decisions",
    response_model=SuggestionDecisionResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def decide_ai_suggestion(
    jobId: uuid.UUID,
    suggestionId: uuid.UUID,
    payload: SuggestionDecisionRequest,
    db: AsyncSession = Depends(get_db),
) -> SuggestionDecisionResponse:
    service = AIDecisionService(session=db)
    decision = await service.record_decision(
        job_id=jobId,
        suggestion_id=suggestionId,
        decision=payload.decision,
        rationale=payload.rationale,
        actor_user_id=None,
    )
    await db.commit()
    await db.refresh(decision)
    return SuggestionDecisionResponse.from_decision(decision=decision)
