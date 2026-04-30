"""Celery tasks: obsolete downstream scan + audit package storage check (FR-039, FR-045)."""
from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import and_, or_, select

from app.core.database import AsyncSessionLocal
from app.models.audit_package import AuditTrailEntry
from app.models.document import Document
from app.models.org import User
from app.models.spec_item import DependencyLink, DependencyRelationshipType, SpecItem
from app.services.notification import send_notification
from app.tasks import celery_app

logger = logging.getLogger(__name__)


async def _scan_obsolete_downstream_async(document_id: uuid.UUID) -> dict[str, object]:
    async with AsyncSessionLocal() as db:
        upstream_items_result = await db.execute(
            select(SpecItem.id).where(SpecItem.document_id == document_id)
        )
        upstream_item_ids = list(upstream_items_result.scalars().all())
        if not upstream_item_ids:
            return {"status": "no_items", "document_id": str(document_id)}

        links_result = await db.execute(
            select(DependencyLink).where(
                or_(
                    and_(
                        DependencyLink.relationship_type.in_(
                            (
                                DependencyRelationshipType.BLOCKING,
                                DependencyRelationshipType.RELATED,
                            )
                        ),
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
        if not links:
            return {"status": "no_dependents", "document_id": str(document_id)}

        downstream_item_ids: set[uuid.UUID] = set()
        for link in links:
            if link.relationship_type == DependencyRelationshipType.BLOCKED_BY:
                downstream_item_ids.add(link.source_item_id)
            else:
                downstream_item_ids.add(link.target_item_id)

        downstream_items_result = await db.execute(
            select(SpecItem).where(SpecItem.id.in_(downstream_item_ids))
        )
        downstream_items = list(downstream_items_result.scalars().all())

        notified_owner_ids: set[uuid.UUID] = set()
        for downstream_item in downstream_items:
            downstream_item.upstream_obsolete_warning = True
            db.add(
                AuditTrailEntry(
                    document_id=downstream_item.document_id,
                    actor_id=None,
                    action="upstream_obsolete_warning_set",
                    detail={
                        "source_document_id": str(document_id),
                        "spec_item_id": str(downstream_item.id),
                    },
                )
            )

            document_result = await db.execute(
                select(Document).where(Document.id == downstream_item.document_id)
            )
            downstream_document = document_result.scalar_one_or_none()
            if (
                downstream_document is not None
                and downstream_document.owner_id is not None
                and downstream_document.owner_id not in notified_owner_ids
            ):
                owner_result = await db.execute(
                    select(User).where(User.id == downstream_document.owner_id)
                )
                owner = owner_result.scalar_one_or_none()
                if owner is not None:
                    await send_notification(
                        db=db,
                        recipient_id=owner.id,
                        recipient_email=owner.email,
                        subject="Upstream document marked obsolete",
                        body=(
                            f"A dependency linked to document {document_id} is now obsolete. "
                            f"Please re-evaluate Spec Item '{downstream_item.title}'."
                        ),
                        related_document_id=downstream_item.document_id,
                    )
                    notified_owner_ids.add(owner.id)

        await db.commit()
        return {
            "status": "scanned",
            "document_id": str(document_id),
            "affected_spec_item_ids": [str(item_id) for item_id in downstream_item_ids],
        }


@celery_app.task(name="app.tasks.obsolete_scan.scan_obsolete_downstream")
def scan_obsolete_downstream(document_id: str) -> dict[str, object]:  # type: ignore[no-untyped-def]
    """Flag downstream spec items when an upstream document becomes obsolete."""
    logger.info("scan_obsolete_downstream: document_id=%s", document_id)
    return asyncio.run(_scan_obsolete_downstream_async(uuid.UUID(document_id)))


@celery_app.task(name="app.tasks.obsolete_scan.check_audit_package_storage")
def check_audit_package_storage() -> dict:  # type: ignore[no-untyped-def]
    """Daily storage quota check for audit packages (FR-045)."""
    import os
    from app.core.config import get_settings
    settings = get_settings()
    path = settings.AUDIT_PACKAGE_STORAGE_PATH
    try:
        total_bytes = sum(
            os.path.getsize(os.path.join(dirpath, f))
            for dirpath, _, files in os.walk(path)
            for f in files
        )
        total_gb = total_bytes / (1024 ** 3)
        if total_gb >= settings.AUDIT_PACKAGE_QUOTA_WARNING_GB:
            logger.warning("Audit package storage quota warning: %.2f GB used (threshold: %.2f GB)", total_gb, settings.AUDIT_PACKAGE_QUOTA_WARNING_GB)
        return {"status": "ok", "used_gb": round(total_gb, 3)}
    except Exception as exc:
        logger.error("Storage check failed: %s", exc)
        return {"status": "error", "error": str(exc)}
