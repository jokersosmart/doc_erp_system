"""Celery tasks for BU-scoped cascade locks and wizard session expiry."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.audit_package import AuditTrailEntry
from app.models.document import Document, LockState
from app.models.lock_event import LockEvent
from app.models.org import User, WizardSession
from app.services.dependency_engine import get_bu_scope, get_directly_dependent_specs
from app.services.notification import send_notification
from app.tasks import celery_app

logger = logging.getLogger(__name__)


async def _apply_cascade_lock_async(
    document_id: uuid.UUID,
    triggered_by_user_id: uuid.UUID,
) -> dict[str, object]:
    async with AsyncSessionLocal() as db:
        upstream_result = await db.execute(select(Document).where(Document.id == document_id))
        upstream_document = upstream_result.scalar_one_or_none()
        if upstream_document is None:
            return {"status": "not_found", "document_id": str(document_id)}

        bu_scope = await get_bu_scope(document_id, db)
        dependent_document_ids = await get_directly_dependent_specs(document_id, db)
        if not dependent_document_ids:
            return {
                "status": "no_dependents",
                "document_id": str(document_id),
                "locked_document_ids": [],
            }

        dependent_result = await db.execute(
            select(Document).where(
                Document.id.in_(dependent_document_ids),
                Document.id != document_id,
                Document.bu_node_id == bu_scope,
            )
        )
        dependent_documents = list(dependent_result.scalars().all())

        locked_document_ids: list[str] = []
        skipped_document_ids: list[str] = []
        notified_owner_ids: set[uuid.UUID] = set()

        for dependent_document in dependent_documents:
            if dependent_document.lock_state != LockState.UNLOCKED:
                skipped_document_ids.append(str(dependent_document.id))
                continue

            dependent_document.lock_state = LockState.LOCKED
            locked_document_ids.append(str(dependent_document.id))

        lock_event: LockEvent | None = None
        if locked_document_ids:
            lock_event = LockEvent(
                upstream_document_id=upstream_document.id,
                triggered_by_user_id=triggered_by_user_id,
                bu_node_id=bu_scope,
                locked_document_ids=[uuid.UUID(value) for value in locked_document_ids],
                upstream_version_at_lock=upstream_document.current_version,
            )
            db.add(lock_event)
            await db.flush()

            for dependent_document in dependent_documents:
                if str(dependent_document.id) not in locked_document_ids:
                    continue

                db.add(
                    AuditTrailEntry(
                        document_id=dependent_document.id,
                        actor_id=triggered_by_user_id,
                        action="cascade_lock_applied",
                        detail={
                            "upstream_document_id": str(upstream_document.id),
                            "upstream_version": upstream_document.current_version,
                            "lock_event_id": str(lock_event.id),
                        },
                    )
                )

                if dependent_document.owner_id and dependent_document.owner_id not in notified_owner_ids:
                    owner_result = await db.execute(
                        select(User).where(User.id == dependent_document.owner_id)
                    )
                    owner = owner_result.scalar_one_or_none()
                    if owner is not None:
                        await send_notification(
                            db=db,
                            recipient_id=owner.id,
                            recipient_email=owner.email,
                            subject="Cascade lock applied",
                            body=(
                                f"Document '{dependent_document.title}' was locked because upstream "
                                f"document '{upstream_document.title}' changed."
                            ),
                            related_document_id=dependent_document.id,
                        )
                        notified_owner_ids.add(owner.id)

        await db.commit()
        return {
            "status": "locked" if locked_document_ids else "no_lockable_dependents",
            "document_id": str(document_id),
            "bu_scope": str(bu_scope) if bu_scope else None,
            "locked_document_ids": locked_document_ids,
            "skipped_document_ids": skipped_document_ids,
            "lock_event_id": str(lock_event.id) if lock_event else None,
        }


@celery_app.task(name="app.tasks.cascade_lock.apply_cascade_lock", bind=True, max_retries=3)
def apply_cascade_lock(self, document_id: str, triggered_by_user_id: str) -> dict[str, object]:  # type: ignore[no-untyped-def]
    """Apply a BU-scoped cascade lock to directly dependent documents."""
    logger.info("apply_cascade_lock: document_id=%s triggered_by=%s", document_id, triggered_by_user_id)
    return asyncio.run(
        _apply_cascade_lock_async(
            document_id=uuid.UUID(document_id),
            triggered_by_user_id=uuid.UUID(triggered_by_user_id),
        )
    )


async def _expire_wizard_sessions_async() -> dict[str, object]:
    async with AsyncSessionLocal() as db:
        now = datetime.now(UTC)
        result = await db.execute(
            select(WizardSession).where(
                WizardSession.is_complete == False,  # noqa: E712
                WizardSession.expires_at < now,
            )
        )
        expired_sessions = list(result.scalars().all())

        expired_count = 0
        for expired_session in expired_sessions:
            await db.delete(expired_session)
            expired_count += 1

        await db.commit()
        return {"status": "ok", "expired_sessions": expired_count}


@celery_app.task(name="app.tasks.cascade_lock.expire_wizard_sessions")
def expire_wizard_sessions() -> dict[str, object]:  # type: ignore[no-untyped-def]
    """Periodic cleanup of expired wizard sessions (FR-043)."""
    logger.info("expire_wizard_sessions: running periodic cleanup")
    return asyncio.run(_expire_wizard_sessions_async())
