"""
Dependency Engine Service (T049).
Builds in-memory directed dependency graph for a project and exposes
helpers used by cascade lock, cycle detection, and obsolete scan.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.document import Document
from app.models.spec_item import DependencyLink, DependencyRelationshipType, SpecItem

if TYPE_CHECKING:
    pass


async def build_dependency_graph(project_id: uuid.UUID, db: AsyncSession) -> dict[str, list[str]]:
    """
    Return adjacency list: {upstream_spec_item_id: [downstream_spec_item_id, ...]}.

    The graph is normalized to a single upstream -> downstream direction:
    - BLOCKING: source -> target
    - BLOCKED_BY: target -> source
    """
    source_item = aliased(SpecItem)
    target_item = aliased(SpecItem)
    source_document = aliased(Document)
    target_document = aliased(Document)

    result = await db.execute(
        select(DependencyLink)
        .join(source_item, DependencyLink.source_item_id == source_item.id)
        .join(source_document, source_item.document_id == source_document.id)
        .join(target_item, DependencyLink.target_item_id == target_item.id)
        .join(target_document, target_item.document_id == target_document.id)
        .where(
            source_document.project_id == project_id,
            target_document.project_id == project_id,
            DependencyLink.relationship_type.in_(
                (
                    DependencyRelationshipType.BLOCKING,
                    DependencyRelationshipType.BLOCKED_BY,
                )
            ),
        )
    )
    links = result.scalars().all()

    graph: dict[str, list[str]] = {}
    for link in links:
        if link.relationship_type == DependencyRelationshipType.BLOCKING:
            upstream_item_id = link.source_item_id
            downstream_item_id = link.target_item_id
        else:
            upstream_item_id = link.target_item_id
            downstream_item_id = link.source_item_id

        graph.setdefault(str(upstream_item_id), []).append(str(downstream_item_id))
        graph.setdefault(str(downstream_item_id), [])

    return graph


async def get_directly_dependent_specs(document_id: uuid.UUID, db: AsyncSession) -> list[uuid.UUID]:
    """
    Return the document IDs that directly depend on the given upstream document.

    Supported link patterns:
    - BLOCKING: upstream source item blocks downstream target item
    - BLOCKED_BY: downstream source item is blocked by upstream target item
    """
    upstream_items_result = await db.execute(
        select(SpecItem.id).where(SpecItem.document_id == document_id)
    )
    upstream_item_ids = list(upstream_items_result.scalars().all())
    if not upstream_item_ids:
        return []

    links_result = await db.execute(
        select(DependencyLink).where(
            or_(
                and_(
                    DependencyLink.relationship_type == DependencyRelationshipType.BLOCKING,
                    DependencyLink.source_item_id.in_(upstream_item_ids),
                ),
                and_(
                    DependencyLink.relationship_type == DependencyRelationshipType.BLOCKED_BY,
                    DependencyLink.target_item_id.in_(upstream_item_ids),
                ),
            )
        )
    )
    dependent_item_ids: list[uuid.UUID] = []
    for link in links_result.scalars().all():
        if link.relationship_type == DependencyRelationshipType.BLOCKING:
            dependent_item_ids.append(link.target_item_id)
        else:
            dependent_item_ids.append(link.source_item_id)

    if not dependent_item_ids:
        return []

    dependent_documents_result = await db.execute(
        select(SpecItem.document_id).where(SpecItem.id.in_(dependent_item_ids)).distinct()
    )
    return [
        dependent_document_id
        for dependent_document_id in dependent_documents_result.scalars().all()
        if dependent_document_id != document_id
    ]


async def get_bu_scope(document_id: uuid.UUID, db: AsyncSession) -> uuid.UUID | None:
    """Return bu_node_id of the document for BU-scoped lock filtering (FR-041)."""
    result = await db.execute(select(Document.bu_node_id).where(Document.id == document_id))
    row = result.first()
    return row[0] if row else None
