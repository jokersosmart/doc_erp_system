"""AI suggestion decision service."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.models.ai_review import AIReviewFinding, AIReviewJob, AISuggestionDecision, SuggestionDecision


class AIDecisionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_decision(
        self,
        *,
        job_id: uuid.UUID,
        suggestion_id: uuid.UUID,
        decision: SuggestionDecision,
        rationale: str | None,
        actor_user_id: uuid.UUID | None,
    ) -> AISuggestionDecision:
        job = await self._session.get(AIReviewJob, job_id)
        if job is None:
            raise NotFoundError("AI review job not found")

        if decision == SuggestionDecision.REJECTED and not (rationale or "").strip():
            raise ValidationError("Rationale is required when decision is REJECTED")

        finding = await self._session.get(AIReviewFinding, suggestion_id)
        if finding is None or finding.job_id != job_id:
            raise ValidationError("Suggestion does not belong to the specified job")

        existing_result = await self._session.execute(
            select(AISuggestionDecision).where(AISuggestionDecision.suggestion_id == suggestion_id)
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            existing.decision = decision
            existing.rationale = rationale
            existing.decided_by_user_id = actor_user_id
            await self._session.flush()
            return existing

        decision_row = AISuggestionDecision(
            job_id=job_id,
            suggestion_id=suggestion_id,
            decision=decision,
            rationale=rationale,
            decided_by_user_id=actor_user_id,
        )
        self._session.add(decision_row)
        await self._session.flush()
        return decision_row
