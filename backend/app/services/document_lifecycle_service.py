"""Document lifecycle and revision orchestration service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.document import Document, LifecycleState
from app.models.document_revision import DocumentRevision, DocumentTransitionEvent
from app.services.attribute_validation_service import AttributeValidationService
from app.services.notification_service import NotificationService
from app.services.suspect_service import SuspectService


class DocumentLifecycleService:
    _allowed_transitions: dict[LifecycleState, set[LifecycleState]] = {
        LifecycleState.DRAFT: {LifecycleState.REVIEW},
        LifecycleState.REVIEW: {LifecycleState.DRAFT, LifecycleState.APPROVED},
        LifecycleState.APPROVED: {LifecycleState.OBSOLETE},
        LifecycleState.OBSOLETE: set(),
    }

    def __init__(
        self,
        session: AsyncSession,
        attribute_validation_service: AttributeValidationService | None = None,
        suspect_service: SuspectService | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._session = session
        self._attribute_validation_service = attribute_validation_service or AttributeValidationService(
            session
        )
        self._suspect_service = suspect_service or SuspectService(session)
        self._notification_service = notification_service or NotificationService(session)

    async def create_document(
        self,
        *,
        project_id: uuid.UUID,
        owner_id: uuid.UUID,
        partition_id: uuid.UUID,
        title: str,
        document_type: str = "spec",
        content_markdown: str,
        standards_scope: list[str],
    ) -> Document:
        document = Document(
            project_id=project_id,
            owner_id=owner_id,
            bu_node_id=partition_id,
            title=title,
            document_type=document_type,
            content_markdown=content_markdown,
            standards_scope=standards_scope,
            lifecycle_state=LifecycleState.DRAFT,
            current_version=1,
        )
        self._session.add(document)
        await self._session.flush()

        await self._create_revision(document=document, created_by_user_id=owner_id)
        return document

    async def get_document(self, *, document_id: uuid.UUID) -> Document:
        document = await self._session.get(Document, document_id)
        if document is None:
            raise NotFoundError("Document not found")
        return document

    async def update_document(
        self,
        *,
        document_id: uuid.UUID,
        expected_version: int,
        content_markdown: str,
        actor_user_id: uuid.UUID | None,
    ) -> Document:
        document = await self.get_document(document_id=document_id)

        if document.lifecycle_state == LifecycleState.APPROVED:
            raise ConflictError("APPROVED revisions cannot be directly edited")

        if expected_version != document.current_version:
            raise ConflictError("Expected version does not match current version")

        document.content_markdown = content_markdown
        document.current_version += 1
        await self._create_revision(document=document, created_by_user_id=actor_user_id)
        return document

    async def transition_document(
        self,
        *,
        document_id: uuid.UUID,
        to_state: LifecycleState,
        actor_user_id: uuid.UUID | None,
        rationale: str | None,
        attributes: list[dict],
    ) -> Document:
        document = await self.get_document(document_id=document_id)
        from_state = document.lifecycle_state

        if to_state not in self._allowed_transitions[from_state]:
            raise ValidationError(f"Invalid transition from {from_state} to {to_state}")

        if to_state == LifecycleState.REVIEW:
            await self._attribute_validation_service.ensure_required_attributes(
                document=document,
                attributes=attributes,
            )

        if to_state == LifecycleState.APPROVED:
            suspect_links = await self._suspect_service.mark_document_links_suspect(
                upstream_document_id=document.id,
                rationale=rationale,
                actor_user_id=actor_user_id,
            )
            await self._notification_service.emit_suspect_owner_notifications(
                upstream_document=document,
                links=suspect_links,
            )

        document.lifecycle_state = to_state
        document.last_transition_at = datetime.now(UTC)

        transition_event = DocumentTransitionEvent(
            document_id=document.id,
            from_state=from_state,
            to_state=to_state,
            actor_user_id=actor_user_id,
            rationale=rationale,
            validation_result={"attribute_count": len(attributes)},
        )
        self._session.add(transition_event)
        await self._session.flush()

        return document

    async def _create_revision(
        self,
        *,
        document: Document,
        created_by_user_id: uuid.UUID | None,
    ) -> None:
        revision = DocumentRevision(
            document_id=document.id,
            version_number=document.current_version,
            content_markdown=document.content_markdown,
            lifecycle_state_at_snapshot=document.lifecycle_state,
            created_by_user_id=created_by_user_id,
        )
        self._session.add(revision)
        await self._session.flush()
