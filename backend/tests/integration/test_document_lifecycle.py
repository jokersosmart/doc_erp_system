from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors import ConflictError, ValidationError
from app.models.document import Document, LifecycleState
from app.services.document_lifecycle_service import DocumentLifecycleService


class _StubAttributeValidationService:
    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    async def ensure_required_attributes(self, *, document: Document, attributes: list[dict]) -> None:
        if self._should_fail:
            raise ValidationError("Missing required attributes: safety_goal")


@pytest.mark.asyncio
async def test_approved_document_cannot_be_directly_updated() -> None:
    document = Document(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Approved spec",
        content_markdown="content",
        lifecycle_state=LifecycleState.APPROVED,
        current_version=3,
    )
    db = AsyncMock()
    db.get.return_value = document
    db.add = MagicMock()

    service = DocumentLifecycleService(session=db)

    with pytest.raises(ConflictError):
        await service.update_document(
            document_id=document.id,
            expected_version=3,
            content_markdown="new",
            actor_user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_draft_to_review_blocks_when_required_attributes_missing() -> None:
    document = Document(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Draft spec",
        content_markdown="content",
        lifecycle_state=LifecycleState.DRAFT,
        current_version=1,
    )
    db = AsyncMock()
    db.get.return_value = document
    db.add = MagicMock()

    service = DocumentLifecycleService(
        session=db,
        attribute_validation_service=_StubAttributeValidationService(should_fail=True),
    )

    with pytest.raises(ValidationError):
        await service.transition_document(
            document_id=document.id,
            to_state=LifecycleState.REVIEW,
            actor_user_id=uuid.uuid4(),
            rationale="ready for review",
            attributes=[],
        )


@pytest.mark.asyncio
async def test_valid_transition_updates_lifecycle_state() -> None:
    document = Document(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Draft spec",
        content_markdown="content",
        lifecycle_state=LifecycleState.DRAFT,
        current_version=1,
    )
    db = AsyncMock()
    db.get.return_value = document
    db.add = MagicMock()

    service = DocumentLifecycleService(
        session=db,
        attribute_validation_service=_StubAttributeValidationService(should_fail=False),
    )

    updated = await service.transition_document(
        document_id=document.id,
        to_state=LifecycleState.REVIEW,
        actor_user_id=uuid.uuid4(),
        rationale="ready for review",
        attributes=[{"attribute_key": "safety_goal", "value_string": "SG-1"}],
    )

    assert updated.lifecycle_state == LifecycleState.REVIEW
    assert updated.last_transition_at is not None


@pytest.mark.asyncio
async def test_create_document_preserves_document_type() -> None:
    db = AsyncMock()
    db.add = MagicMock()

    service = DocumentLifecycleService(session=db)
    document = await service.create_document(
        project_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        partition_id=uuid.uuid4(),
        title="Imported spec",
        document_type="hardware_requirement",
        content_markdown="# Imported spec",
        standards_scope=["ISO26262-8"],
    )

    assert document.document_type == "hardware_requirement"
