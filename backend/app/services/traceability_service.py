"""Traceability graph and link management service."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.models.document import Document
from app.models.spec_item import DependencyHealthState, DependencyLink, DependencyRelationshipType, SpecItem
from app.schemas.traceability import ImpactAnalysisResponse, ImpactedDocument


class TraceabilityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_link(
        self,
        *,
        source_item_id: uuid.UUID,
        target_item_id: uuid.UUID,
        relationship_type: DependencyRelationshipType,
    ) -> DependencyLink:
        if source_item_id == target_item_id:
            raise ConflictError("Circular link is not allowed")

        existing = await self._session.execute(
            select(DependencyLink).where(
                DependencyLink.source_item_id == source_item_id,
                DependencyLink.target_item_id == target_item_id,
                DependencyLink.relationship_type == relationship_type,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("Duplicate dependency link")

        reverse = await self._session.execute(
            select(DependencyLink).where(
                DependencyLink.source_item_id == target_item_id,
                DependencyLink.target_item_id == source_item_id,
            )
        )
        if reverse.scalar_one_or_none() is not None:
            raise ConflictError("Circular link is not allowed")

        link = DependencyLink(
            source_item_id=source_item_id,
            target_item_id=target_item_id,
            relationship_type=relationship_type,
            health_state=DependencyHealthState.HEALTHY,
        )
        self._session.add(link)
        await self._session.flush()
        return link

    async def get_document_impacts(self, *, document_id: uuid.UUID) -> ImpactAnalysisResponse:
        upstream_document = await self._session.get(Document, document_id)

        links_result = await self._session.execute(
            select(DependencyLink, SpecItem, Document)
            .join(SpecItem, DependencyLink.target_item_id == SpecItem.id)
            .join(Document, SpecItem.document_id == Document.id)
            .where(
                DependencyLink.source_item_id.in_(
                    select(SpecItem.id).where(SpecItem.document_id == document_id)
                )
            )
        )

        impacted_by_document: dict[uuid.UUID, ImpactedDocument] = {}
        for link, _target_item, impacted_document in links_result.all():
            current = impacted_by_document.get(impacted_document.id)
            candidate_status = link.health_state
            candidate_resolution = None

            if current is None:
                impacted_by_document[impacted_document.id] = ImpactedDocument(
                    document_id=impacted_document.id,
                    title=impacted_document.title,
                    owner_id=impacted_document.owner_id,
                    health_status=candidate_status,
                    current_resolution=candidate_resolution,
                )
                continue

            if (
                current.health_status != DependencyHealthState.SUSPECT
                and candidate_status == DependencyHealthState.SUSPECT
            ):
                current.health_status = DependencyHealthState.SUSPECT
                current.current_resolution = candidate_resolution

        return ImpactAnalysisResponse(
            upstream_document_id=document_id,
            upstream_version=upstream_document.current_version if upstream_document else None,
            impacted_documents=list(impacted_by_document.values()),
        )
