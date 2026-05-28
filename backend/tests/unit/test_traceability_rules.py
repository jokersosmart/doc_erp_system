from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.core.errors import ConflictError, NotFoundError
from app.models.spec_item import DependencyHealthState, DependencyRelationshipType
from app.services.suspect_service import SuspectService
from app.services.traceability_service import TraceabilityService


class _FakeSelectResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


@pytest.mark.asyncio
async def test_create_link_rejects_self_cycle() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    service = TraceabilityService(session=db)

    item_id = uuid.uuid4()
    with pytest.raises(ConflictError):
        await service.create_link(
            source_item_id=item_id,
            target_item_id=item_id,
            relationship_type=DependencyRelationshipType.BLOCKING,
        )


@pytest.mark.asyncio
async def test_create_link_rejects_duplicate() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [_FakeSelectResult(value=SimpleNamespace())]

    service = TraceabilityService(session=db)

    with pytest.raises(ConflictError):
        await service.create_link(
            source_item_id=uuid.uuid4(),
            target_item_id=uuid.uuid4(),
            relationship_type=DependencyRelationshipType.RELATED,
        )


@pytest.mark.asyncio
async def test_create_link_rejects_reverse_cycle() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [
        _FakeSelectResult(value=None),
        _FakeSelectResult(value=SimpleNamespace()),
    ]

    service = TraceabilityService(session=db)

    with pytest.raises(ConflictError):
        await service.create_link(
            source_item_id=uuid.uuid4(),
            target_item_id=uuid.uuid4(),
            relationship_type=DependencyRelationshipType.BLOCKING,
        )


@pytest.mark.asyncio
async def test_resolve_suspect_missing_link_raises_not_found() -> None:
    db = AsyncMock()
    db.get.return_value = None
    db.add = MagicMock()

    service = SuspectService(session=db)

    with pytest.raises(NotFoundError):
        await service.resolve_suspect(
            link_id=uuid.uuid4(),
            resolution_type="UPDATED",
            rationale="handled",
            actor_user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_resolve_pending_keeps_link_suspect() -> None:
    link = SimpleNamespace(
        id=uuid.uuid4(),
        health_state=DependencyHealthState.HEALTHY,
        last_health_transition_at=None,
        last_health_transition_by=None,
        suspect_reason=None,
    )

    db = AsyncMock()
    db.get.return_value = link
    db.add = MagicMock()

    service = SuspectService(session=db)

    updated = await service.resolve_suspect(
        link_id=link.id,
        resolution_type="PENDING",
        rationale="need further analysis",
        actor_user_id=uuid.uuid4(),
    )

    assert updated.health_state == DependencyHealthState.SUSPECT
    assert updated.last_health_transition_at is not None


@pytest.mark.asyncio
async def test_resolve_updated_marks_link_resolved() -> None:
    link = SimpleNamespace(
        id=uuid.uuid4(),
        health_state=DependencyHealthState.SUSPECT,
        last_health_transition_at=None,
        last_health_transition_by=None,
        suspect_reason=None,
    )

    db = AsyncMock()
    db.get.return_value = link
    db.add = MagicMock()

    service = SuspectService(session=db)

    updated = await service.resolve_suspect(
        link_id=link.id,
        resolution_type="UPDATED",
        rationale="downstream updated",
        actor_user_id=uuid.uuid4(),
    )

    assert updated.health_state == DependencyHealthState.RESOLVED
    assert updated.last_health_transition_at is not None
