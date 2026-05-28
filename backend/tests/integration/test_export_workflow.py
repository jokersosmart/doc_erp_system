from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.models.export_job import ExportArtifactType, ExportIssueSeverity
from app.services.export_service import ExportService
from app.services.export_validation_service import ValidationIssue


class _StubValidationService:
    def __init__(self, issues: list[ValidationIssue]) -> None:
        self._issues = issues

    def validate_mapping_completeness(self, *, mapping_profile: str, artifact_types: set[ExportArtifactType]) -> list[ValidationIssue]:
        _ = mapping_profile
        _ = artifact_types
        return self._issues


@pytest.mark.asyncio
async def test_export_job_becomes_completed_when_no_validation_issues() -> None:
    db = AsyncMock()
    db.add = MagicMock()

    service = ExportService(
        session=db,
        validation_service=_StubValidationService(issues=[]),
    )

    job = await service.create_export_job(
        project_id=uuid.uuid4(),
        mapping_profile="default",
    )

    assert job.status.value == "COMPLETED"
    assert job.completed_at is not None


@pytest.mark.asyncio
async def test_export_job_becomes_partial_with_validation_issues() -> None:
    db = AsyncMock()
    db.add = MagicMock()

    service = ExportService(
        session=db,
        validation_service=_StubValidationService(
            issues=[
                ValidationIssue(
                    issue_code="MISSING_MAPPING",
                    severity=ExportIssueSeverity.ERROR,
                    message="Missing mapping entry",
                    entity_ref="document:123",
                )
            ]
        ),
    )

    job = await service.create_export_job(
        project_id=uuid.uuid4(),
        mapping_profile="strict",
    )

    assert job.status.value == "PARTIAL"
    assert job.completed_at is not None
