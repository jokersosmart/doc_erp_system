"""Notification workflows for traceability and lifecycle events."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.notification import Notification, NotificationChannel
from app.models.spec_item import DependencyLink, DependencyRelationshipType, SpecItem


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_notification(
        self,
        *,
        recipient_user_id,
        category: str,
        title: str,
        body: str,
        related_entity_type: str | None = None,
        related_entity_id=None,
        channel: NotificationChannel = NotificationChannel.IN_APP,
    ) -> Notification:
        notification = Notification(
            recipient_user_id=recipient_user_id,
            channel=channel,
            category=category,
            title=title,
            body=body,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )
        self._session.add(notification)
        await self._session.flush()
        return notification

    async def emit_suspect_owner_notifications(
        self,
        *,
        upstream_document: Document,
        links: list[DependencyLink],
    ) -> int:
        if not links:
            return 0

        downstream_item_ids = []
        for link in links:
            if link.relationship_type == DependencyRelationshipType.BLOCKING:
                downstream_item_ids.append(link.target_item_id)
            else:
                downstream_item_ids.append(link.source_item_id)

        if not downstream_item_ids:
            return 0

        result = await self._session.execute(
            select(Document.id, Document.owner_id, Document.title)
            .join(SpecItem, SpecItem.document_id == Document.id)
            .where(SpecItem.id.in_(downstream_item_ids))
            .distinct()
        )

        created = 0
        for downstream_document_id, owner_id, downstream_title in result.all():
            if owner_id is None:
                continue
            await self.create_notification(
                recipient_user_id=owner_id,
                category="SUSPECT",
                title="Dependency marked as SUSPECT",
                body=(
                    f"Upstream document '{upstream_document.title}' was approved. "
                    f"Please review impacted document '{downstream_title}'."
                ),
                related_entity_type="document",
                related_entity_id=downstream_document_id,
            )
            created += 1

        return created
