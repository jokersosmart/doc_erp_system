"""Suspect propagation and resolution service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.spec_item import (
    DependencyHealthState,
    DependencyLink,
    DependencyRelationshipType,
    SpecItem,
)
from app.models.suspect_resolution import SuspectResolution


class SuspectService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve_suspect(
        self,
        *,
        link_id: uuid.UUID,
        resolution_type: str,
        rationale: str | None,
        actor_user_id: uuid.UUID | None,
    ) -> DependencyLink:
        link = await self._session.get(DependencyLink, link_id)
        if link is None:
            raise NotFoundError("Dependency link not found")

        link.health_state = (
            DependencyHealthState.SUSPECT
            if resolution_type == "PENDING"
            else DependencyHealthState.RESOLVED
        )
        link.last_health_transition_at = datetime.now(UTC)
        link.last_health_transition_by = actor_user_id
        link.suspect_reason = rationale

        resolution = SuspectResolution(
            dependency_link_id=link.id,
            resolution_type=resolution_type,
            rationale=rationale,
            resolved_by=actor_user_id,
        )
        self._session.add(resolution)
        await self._session.flush()

        return link

    async def mark_document_links_suspect(
        self,
        *,
        upstream_document_id: uuid.UUID,
        rationale: str | None,
        actor_user_id: uuid.UUID | None,
    ) -> list[DependencyLink]:
        upstream_items_result = await self._session.execute(
            select(SpecItem.id).where(SpecItem.document_id == upstream_document_id)
        )
        upstream_item_ids = list(upstream_items_result.scalars().all())
        if not upstream_item_ids:
            return []

        links_result = await self._session.execute(
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
        links = links_result.scalars().all()

        transition_at = datetime.now(UTC)
        for link in links:
            link.health_state = DependencyHealthState.SUSPECT
            link.suspect_reason = rationale
            link.last_health_transition_at = transition_at
            link.last_health_transition_by = actor_user_id

        await self._session.flush()
        return list(links)
