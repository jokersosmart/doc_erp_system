from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors import NotFoundError, ValidationError
from app.models.ai_review import SuggestionDecision
from app.services.ai_decision_service import AIDecisionService


class _FakeSelectResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


@pytest.mark.asyncio
async def test_rejected_decision_requires_rationale() -> None:
    job_id = uuid.uuid4()
    suggestion_id = uuid.uuid4()

    fake_job = type("Job", (), {"id": job_id})()
    fake_finding = type("Finding", (), {"id": suggestion_id, "job_id": job_id})()

    db = AsyncMock()
    db.get.side_effect = [fake_job, fake_finding]
    db.add = MagicMock()

    service = AIDecisionService(session=db)

    with pytest.raises(ValidationError):
        await service.record_decision(
            job_id=job_id,
            suggestion_id=suggestion_id,
            decision=SuggestionDecision.REJECTED,
            rationale="",
            actor_user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_accept_decision_without_rationale_is_allowed() -> None:
    job_id = uuid.uuid4()
    suggestion_id = uuid.uuid4()

    fake_job = type("Job", (), {"id": job_id})()
    fake_finding = type("Finding", (), {"id": suggestion_id, "job_id": job_id})()

    db = AsyncMock()
    db.get.side_effect = [fake_job, fake_finding]
    db.execute.return_value = _FakeSelectResult(value=None)
    db.add = MagicMock()

    service = AIDecisionService(session=db)

    decision = await service.record_decision(
        job_id=job_id,
        suggestion_id=suggestion_id,
        decision=SuggestionDecision.ACCEPTED,
        rationale=None,
        actor_user_id=uuid.uuid4(),
    )

    assert decision.decision == SuggestionDecision.ACCEPTED


@pytest.mark.asyncio
async def test_decision_fails_when_job_missing() -> None:
    db = AsyncMock()
    db.get.return_value = None

    service = AIDecisionService(session=db)

    with pytest.raises(NotFoundError):
        await service.record_decision(
            job_id=uuid.uuid4(),
            suggestion_id=uuid.uuid4(),
            decision=SuggestionDecision.ACCEPTED,
            rationale=None,
            actor_user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_decision_fails_when_suggestion_not_in_job() -> None:
    job_id = uuid.uuid4()
    fake_job = type("Job", (), {"id": job_id})()
    foreign_finding = type("Finding", (), {"id": uuid.uuid4(), "job_id": uuid.uuid4()})()

    db = AsyncMock()
    db.get.side_effect = [fake_job, foreign_finding]

    service = AIDecisionService(session=db)

    with pytest.raises(ValidationError):
        await service.record_decision(
            job_id=job_id,
            suggestion_id=foreign_finding.id,
            decision=SuggestionDecision.REJECTED,
            rationale="not applicable",
            actor_user_id=uuid.uuid4(),
        )
