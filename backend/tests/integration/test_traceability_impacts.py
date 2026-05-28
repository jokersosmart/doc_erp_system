from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.models.document import Document, LifecycleState
from app.models.spec_item import DependencyHealthState, DependencyRelationshipType
from app.services.document_lifecycle_service import DocumentLifecycleService
from app.services.suspect_service import SuspectService
from app.services.traceability_service import TraceabilityService


class _FakeExecuteResult:
    def __init__(self, rows: list[tuple[object, object, object]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[object, object, object]]:
        return self._rows


class _FakeScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


class _FakeExecuteScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._values)


@pytest.mark.asyncio
async def test_impacts_prioritize_suspect_status_for_same_document() -> None:
    upstream_document_id = uuid.uuid4()
    impacted_document_id = uuid.uuid4()

    upstream_document = SimpleNamespace(current_version=7)
    impacted_document = SimpleNamespace(
        id=impacted_document_id,
        title="Impacted Doc",
        owner_id=uuid.uuid4(),
    )

    healthy_link = SimpleNamespace(
        source_item_id=uuid.uuid4(),
        target_item_id=uuid.uuid4(),
        relationship_type=DependencyRelationshipType.BLOCKING,
        health_state=DependencyHealthState.HEALTHY,
    )
    suspect_link = SimpleNamespace(
        source_item_id=uuid.uuid4(),
        target_item_id=uuid.uuid4(),
        relationship_type=DependencyRelationshipType.BLOCKING,
        health_state=DependencyHealthState.SUSPECT,
    )

    db = AsyncMock()
    db.get.return_value = upstream_document
    db.execute.return_value = _FakeExecuteResult(
        rows=[
            (healthy_link, SimpleNamespace(), impacted_document),
            (suspect_link, SimpleNamespace(), impacted_document),
        ]
    )

    service = TraceabilityService(session=db)

    response = await service.get_document_impacts(document_id=upstream_document_id)

    assert response.upstream_document_id == upstream_document_id
    assert response.upstream_version == 7
    assert len(response.impacted_documents) == 1
    assert response.impacted_documents[0].document_id == impacted_document_id
    assert response.impacted_documents[0].health_status == DependencyHealthState.SUSPECT


@pytest.mark.asyncio
async def test_impacts_returns_empty_list_when_no_links_found() -> None:
    upstream_document_id = uuid.uuid4()

    db = AsyncMock()
    db.get.return_value = None
    db.execute.return_value = _FakeExecuteResult(rows=[])

    service = TraceabilityService(session=db)

    response = await service.get_document_impacts(document_id=upstream_document_id)

    assert response.upstream_document_id == upstream_document_id
    assert response.upstream_version is None
    assert response.impacted_documents == []


@pytest.mark.asyncio
async def test_suspect_propagation_marks_downstream_links() -> None:
    upstream_document_id = uuid.uuid4()
    actor_user_id = uuid.uuid4()

    link_a = SimpleNamespace(
        id=uuid.uuid4(),
        health_state=DependencyHealthState.HEALTHY,
        suspect_reason=None,
        last_health_transition_at=None,
        last_health_transition_by=None,
        relationship_type=DependencyRelationshipType.BLOCKING,
        source_item_id=uuid.uuid4(),
        target_item_id=uuid.uuid4(),
    )
    link_b = SimpleNamespace(
        id=uuid.uuid4(),
        health_state=DependencyHealthState.RESOLVED,
        suspect_reason=None,
        last_health_transition_at=None,
        last_health_transition_by=None,
        relationship_type=DependencyRelationshipType.BLOCKED_BY,
        source_item_id=uuid.uuid4(),
        target_item_id=uuid.uuid4(),
    )

    db = AsyncMock()
    db.execute.side_effect = [
        _FakeExecuteScalarResult(values=[uuid.uuid4(), uuid.uuid4()]),
        _FakeExecuteScalarResult(values=[link_a, link_b]),
    ]

    service = SuspectService(session=db)
    updated_links = await service.mark_document_links_suspect(
        upstream_document_id=upstream_document_id,
        rationale="upstream approved",
        actor_user_id=actor_user_id,
    )

    assert len(updated_links) == 2
    assert all(link.health_state == DependencyHealthState.SUSPECT for link in updated_links)
    assert all(link.suspect_reason == "upstream approved" for link in updated_links)
    assert all(link.last_health_transition_by == actor_user_id for link in updated_links)


@pytest.mark.asyncio
async def test_approved_transition_triggers_suspect_flow_and_notifications() -> None:
    document = Document(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Upstream Spec",
        content_markdown="content",
        lifecycle_state=LifecycleState.REVIEW,
        current_version=2,
    )

    db = AsyncMock()
    db.get.return_value = document
    db.add = MagicMock()

    suspect_service = AsyncMock()
    suspect_service.mark_document_links_suspect.return_value = [
        SimpleNamespace(id=uuid.uuid4(), relationship_type=DependencyRelationshipType.BLOCKING)
    ]

    notification_service = AsyncMock()

    service = DocumentLifecycleService(
        session=db,
        suspect_service=suspect_service,
        notification_service=notification_service,
    )

    updated = await service.transition_document(
        document_id=document.id,
        to_state=LifecycleState.APPROVED,
        actor_user_id=uuid.uuid4(),
        rationale="approved for release",
        attributes=[],
    )

    assert updated.lifecycle_state == LifecycleState.APPROVED
    suspect_service.mark_document_links_suspect.assert_awaited_once()
    notification_service.emit_suspect_owner_notifications.assert_awaited_once()
