from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.dashboard_service import DashboardService


class _FakeScalarResult:
    def __init__(self, value: int) -> None:
        self._value = value

    def scalar_one(self) -> int:
        return self._value


@pytest.mark.asyncio
async def test_dashboard_summary_aggregates_all_counters() -> None:
    db = AsyncMock()
    db.execute.side_effect = [
        _FakeScalarResult(4),
        _FakeScalarResult(3),
        _FakeScalarResult(9),
        _FakeScalarResult(2),
    ]

    service = DashboardService(session=db)

    summary = await service.get_summary()

    assert summary.open_suspect_count == 4
    assert summary.pending_review_count == 3
    assert summary.compliance_gap_count == 9
    assert summary.export_ready_count == 2
