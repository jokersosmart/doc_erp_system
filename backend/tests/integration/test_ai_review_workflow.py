from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.ai_review import JobStatus
from app.services.ai_review_service import AIReviewService


class _FakeScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


class _FakeExecuteResult:
    def __init__(self, scalar_values: list[object]) -> None:
        self._scalar_values = scalar_values

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._scalar_values)


@pytest.mark.asyncio
async def test_create_review_job_with_standards_starts_partial_with_first_result() -> None:
    db = AsyncMock()
    db.add = MagicMock()

    service = AIReviewService(session=db)

    job = await service.create_review_job(
        document_id=uuid.uuid4(),
        revision_id=uuid.uuid4(),
        standards=["ASPICE-SWE.1"],
    )

    assert job.status == JobStatus.PARTIAL
    assert job.accepted_at is not None
    assert job.first_result_at is not None


@pytest.mark.asyncio
async def test_retryable_transition_and_retry_back_to_running() -> None:
    job_id = uuid.uuid4()

    queued_job = type("Job", (), {"status": JobStatus.QUEUED, "error_message": None})()
    retryable_job = type("Job", (), {"status": JobStatus.RETRYABLE, "error_message": None})()

    db = AsyncMock()
    db.add = MagicMock()
    db.get.side_effect = [queued_job, retryable_job]

    service = AIReviewService(session=db)

    updated_retryable = await service.mark_retryable(
        job_id=job_id,
        error_message="Temporary AI provider timeout",
    )
    assert updated_retryable.status == JobStatus.RETRYABLE
    assert updated_retryable.error_message == "Temporary AI provider timeout"

    updated_running = await service.mark_running(job_id=job_id)
    assert updated_running.status == JobStatus.RUNNING


@pytest.mark.asyncio
async def test_partial_transition_adds_finding_and_sets_first_result_once() -> None:
    job_id = uuid.uuid4()
    first_result_marker = object()
    running_job = type("Job", (), {"id": job_id, "status": JobStatus.RUNNING, "first_result_at": None})()
    partial_job = type(
        "Job",
        (),
        {"id": job_id, "status": JobStatus.RUNNING, "first_result_at": first_result_marker},
    )()

    db = AsyncMock()
    db.add = MagicMock()
    db.get.side_effect = [running_job, partial_job]
    db.execute.return_value = _FakeExecuteResult(scalar_values=[])

    service = AIReviewService(session=db)

    first = await service.mark_partial(
        job_id=job_id,
        clause_key="ISO26262-6.4.5",
        finding_text="Missing evidence linkage",
    )
    second = await service.mark_partial(
        job_id=job_id,
        clause_key=None,
        finding_text="Mapping incomplete",
    )

    assert first.status == JobStatus.PARTIAL
    assert first.first_result_at is not None
    assert second.status == JobStatus.PARTIAL
    assert second.first_result_at is first_result_marker
