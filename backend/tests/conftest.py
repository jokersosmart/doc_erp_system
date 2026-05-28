from __future__ import annotations

import uuid
from collections.abc import Callable
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def uuid_value() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def uuid_factory() -> Callable[[], uuid.UUID]:
    return uuid.uuid4


@pytest.fixture
def db_session() -> AsyncSession:
    return AsyncMock(spec=AsyncSession)
