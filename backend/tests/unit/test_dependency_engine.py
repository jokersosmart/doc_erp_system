from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest

from app.models.spec_item import DependencyRelationshipType
from app.services.dependency_engine import (
    build_dependency_graph,
    get_bu_scope,
    get_directly_dependent_specs,
)


class _FakeScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


class _FakeExecuteResult:
    def __init__(self, scalar_values: list[object] | None = None, first_row: object | None = None) -> None:
        self._scalar_values = scalar_values or []
        self._first_row = first_row

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._scalar_values)

    def first(self) -> object | None:
        return self._first_row


@pytest.mark.asyncio
async def test_build_dependency_graph_normalizes_blocked_by_direction() -> None:
    project_id = uuid.uuid4()
    source_item = uuid.uuid4()
    middle_item = uuid.uuid4()
    downstream_item = uuid.uuid4()

    links = [
        SimpleNamespace(
            relationship_type=DependencyRelationshipType.BLOCKING,
            source_item_id=source_item,
            target_item_id=middle_item,
        ),
        SimpleNamespace(
            relationship_type=DependencyRelationshipType.BLOCKED_BY,
            source_item_id=downstream_item,
            target_item_id=middle_item,
        ),
    ]

    db = AsyncMock()
    db.execute.return_value = _FakeExecuteResult(scalar_values=links)

    graph = await build_dependency_graph(project_id=project_id, db=db)

    assert graph[str(source_item)] == [str(middle_item)]
    assert graph[str(middle_item)] == [str(downstream_item)]
    assert graph[str(downstream_item)] == []


@pytest.mark.asyncio
async def test_get_directly_dependent_specs_resolves_both_relationship_types() -> None:
    document_id = uuid.uuid4()
    upstream_item_a = uuid.uuid4()
    upstream_item_b = uuid.uuid4()
    dependent_item_a = uuid.uuid4()
    dependent_item_b = uuid.uuid4()
    dependent_doc_a = uuid.uuid4()
    dependent_doc_b = uuid.uuid4()

    links = [
        SimpleNamespace(
            relationship_type=DependencyRelationshipType.BLOCKING,
            source_item_id=upstream_item_a,
            target_item_id=dependent_item_a,
        ),
        SimpleNamespace(
            relationship_type=DependencyRelationshipType.BLOCKED_BY,
            source_item_id=dependent_item_b,
            target_item_id=upstream_item_b,
        ),
    ]

    db = AsyncMock()
    db.execute.side_effect = [
        _FakeExecuteResult(scalar_values=[upstream_item_a, upstream_item_b]),
        _FakeExecuteResult(scalar_values=links),
        _FakeExecuteResult(scalar_values=[dependent_doc_a, dependent_doc_b, document_id]),
    ]

    dependent_docs = await get_directly_dependent_specs(document_id=document_id, db=db)

    assert dependent_docs == [dependent_doc_a, dependent_doc_b]


@pytest.mark.asyncio
async def test_get_bu_scope_returns_none_when_document_missing() -> None:
    db = AsyncMock()
    db.execute.return_value = _FakeExecuteResult(first_row=None)

    result = await get_bu_scope(document_id=uuid.uuid4(), db=db)

    assert result is None


@pytest.mark.asyncio
async def test_get_bu_scope_returns_uuid_when_document_exists() -> None:
    bu_node_id = uuid.uuid4()
    db = AsyncMock()
    db.execute.return_value = _FakeExecuteResult(first_row=(bu_node_id,))

    result = await get_bu_scope(document_id=uuid.uuid4(), db=db)

    assert result == bu_node_id
