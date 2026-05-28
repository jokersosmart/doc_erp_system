from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.models.spec_item import DependencyRelationshipType
from app.services.notification_service import NotificationService


class _FakeExecuteResult:
    def __init__(self, rows: list[tuple[uuid.UUID, uuid.UUID | None, str]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[uuid.UUID, uuid.UUID | None, str]]:
        return self._rows


@pytest.mark.asyncio
async def test_emit_suspect_owner_notifications_creates_owner_alerts() -> None:
    owner_id = uuid.uuid4()
    downstream_document_id = uuid.uuid4()

    db = AsyncMock()
    db.add = MagicMock()
    db.execute.return_value = _FakeExecuteResult(
        rows=[(downstream_document_id, owner_id, "Downstream Doc")]
    )

    service = NotificationService(session=db)

    created = await service.emit_suspect_owner_notifications(
        upstream_document=SimpleNamespace(title="Upstream Doc"),
        links=[
            SimpleNamespace(
                relationship_type=DependencyRelationshipType.BLOCKING,
                target_item_id=uuid.uuid4(),
                source_item_id=uuid.uuid4(),
            )
        ],
    )

    assert created == 1
    assert db.add.call_count == 1


@pytest.mark.asyncio
async def test_emit_suspect_owner_notifications_skips_when_no_links() -> None:
    db = AsyncMock()

    service = NotificationService(session=db)

    created = await service.emit_suspect_owner_notifications(
        upstream_document=SimpleNamespace(title="Upstream Doc"),
        links=[],
    )

    assert created == 0
