"""Audit and notification service scaffolds."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent
from app.models.notification import Notification, NotificationChannel


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_event(
        self,
        *,
        event_type: str,
        actor_user_id: uuid.UUID | None,
        partition_node_id: uuid.UUID | None,
        entity_type: str,
        entity_id: uuid.UUID,
        payload_before_json: dict | None = None,
        payload_after_json: dict | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=event_type,
            actor_user_id=actor_user_id,
            partition_node_id=partition_node_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_before_json=payload_before_json,
            payload_after_json=payload_after_json,
        )
        self._session.add(event)
        await self._session.flush()
        return event


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_notification(
        self,
        *,
        recipient_user_id: uuid.UUID,
        category: str,
        title: str,
        body: str,
        related_entity_type: str | None = None,
        related_entity_id: uuid.UUID | None = None,
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
