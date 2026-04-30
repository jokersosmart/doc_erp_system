"""Celery task: async circular dependency detection (FR-015d)."""
from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import and_, or_, select

from app.core.database import AsyncSessionLocal
from app.models.document import Document
from app.models.org import User
from app.models.spec_item import DependencyLink, DependencyRelationshipType, SpecItem
from app.services.dependency_engine import build_dependency_graph
from app.services.notification import send_notification
from app.tasks import celery_app

logger = logging.getLogger(__name__)


def _normalise_cycle(cycle: list[str]) -> tuple[str, ...]:
    core = cycle[:-1] if cycle and cycle[0] == cycle[-1] else cycle
    rotations = [tuple(core[index:] + core[:index]) for index in range(len(core))]
    return min(rotations)


def _find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    visited: set[str] = set()
    in_stack: set[str] = set()
    stack: list[str] = []
    cycles: dict[tuple[str, ...], list[str]] = {}

    def dfs(node: str) -> None:
        visited.add(node)
        in_stack.add(node)
        stack.append(node)

        for neighbour in graph.get(node, []):
            if neighbour not in visited:
                dfs(neighbour)
            elif neighbour in in_stack:
                cycle_start = stack.index(neighbour)
                cycle = stack[cycle_start:] + [neighbour]
                cycles.setdefault(_normalise_cycle(cycle), cycle)

        stack.pop()
        in_stack.remove(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return list(cycles.values())


async def _detect_cycles_async(project_id: uuid.UUID) -> dict[str, object]:
    async with AsyncSessionLocal() as db:
        graph = await build_dependency_graph(project_id, db)
        cycles = _find_cycles(graph)
        if not cycles:
            return {"status": "ok", "project_id": str(project_id), "cycles_found": 0}

        flagged_link_ids: set[str] = set()
        notified_owner_ids: set[uuid.UUID] = set()

        for cycle in cycles:
            cycle_pairs = list(zip(cycle, cycle[1:]))
            for upstream_item_id, downstream_item_id in cycle_pairs:
                link_result = await db.execute(
                    select(DependencyLink).where(
                        or_(
                            and_(
                                DependencyLink.relationship_type == DependencyRelationshipType.BLOCKING,
                                DependencyLink.source_item_id == uuid.UUID(upstream_item_id),
                                DependencyLink.target_item_id == uuid.UUID(downstream_item_id),
                            ),
                            and_(
                                DependencyLink.relationship_type == DependencyRelationshipType.BLOCKED_BY,
                                DependencyLink.source_item_id == uuid.UUID(downstream_item_id),
                                DependencyLink.target_item_id == uuid.UUID(upstream_item_id),
                            ),
                        )
                    )
                )
                link = link_result.scalar_one_or_none()
                if link is not None:
                    link.has_cycle_warning = True
                    flagged_link_ids.add(str(link.id))

            cycle_item_ids = {uuid.UUID(item_id) for item_id in cycle[:-1]}
            item_result = await db.execute(select(SpecItem).where(SpecItem.id.in_(cycle_item_ids)))
            cycle_items = list(item_result.scalars().all())

            for cycle_item in cycle_items:
                document_result = await db.execute(
                    select(Document).where(Document.id == cycle_item.document_id)
                )
                document = document_result.scalar_one_or_none()
                if (
                    document is None
                    or document.owner_id is None
                    or document.owner_id in notified_owner_ids
                ):
                    continue

                owner_result = await db.execute(select(User).where(User.id == document.owner_id))
                owner = owner_result.scalar_one_or_none()
                if owner is None:
                    continue

                await send_notification(
                    db=db,
                    recipient_id=owner.id,
                    recipient_email=owner.email,
                    subject="Circular dependency detected",
                    body=(
                        "A circular dependency was detected in the project dependency graph: "
                        + " -> ".join(cycle)
                    ),
                    related_document_id=document.id,
                )
                notified_owner_ids.add(owner.id)

        await db.commit()
        return {
            "status": "warning",
            "project_id": str(project_id),
            "cycles_found": len(cycles),
            "flagged_link_ids": sorted(flagged_link_ids),
        }


@celery_app.task(name="app.tasks.cycle_detection.detect_cycles")
def detect_cycles(project_id: str) -> dict[str, object]:  # type: ignore[no-untyped-def]
    """Run DFS over the normalized dependency graph and flag circular paths."""
    logger.info("detect_cycles: project_id=%s", project_id)
    return asyncio.run(_detect_cycles_async(uuid.UUID(project_id)))
