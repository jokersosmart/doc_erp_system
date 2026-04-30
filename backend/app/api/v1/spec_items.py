"""Spec Item dependency endpoints (T055)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.models.document import Document
from app.models.spec_item import DependencyLink, DependencyRelationshipType, SpecItem
from app.tasks.cycle_detection import detect_cycles as detect_cycles_task

router = APIRouter(tags=["spec_items"])


class DependencyCreateBody(BaseModel):
    target_item_id: uuid.UUID
    relationship_type: DependencyRelationshipType


class DependencyLinkOut(BaseModel):
    id: str
    source_item_id: str
    target_item_id: str
    relationship_type: str
    has_cycle_warning: bool


async def _get_spec_item_or_404(spec_item_id: uuid.UUID, db: AsyncSession) -> SpecItem:
    result = await db.execute(select(SpecItem).where(SpecItem.id == spec_item_id))
    spec_item = result.scalar_one_or_none()
    if spec_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spec item not found")
    return spec_item


@router.post(
    "/documents/{document_id}/spec-items/{item_id}/dependencies",
    response_model=DependencyLinkOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_dependency_link(
    document_id: uuid.UUID,
    item_id: uuid.UUID,
    body: DependencyCreateBody,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DependencyLinkOut:
    source_item = await _get_spec_item_or_404(item_id, db)
    if source_item.document_id != document_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Spec item is not in the given document")

    target_item = await _get_spec_item_or_404(body.target_item_id, db)
    if target_item.id == source_item.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A spec item cannot depend on itself")

    existing_result = await db.execute(
        select(DependencyLink).where(
            DependencyLink.source_item_id == source_item.id,
            DependencyLink.target_item_id == target_item.id,
            DependencyLink.relationship_type == body.relationship_type,
        )
    )
    existing_link = existing_result.scalar_one_or_none()
    if existing_link is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dependency link already exists")

    link = DependencyLink(
        source_item_id=source_item.id,
        target_item_id=target_item.id,
        relationship_type=body.relationship_type,
        created_by=current_user.id,
    )
    db.add(link)
    await db.flush()

    source_document_result = await db.execute(
        select(Document).where(Document.id == source_item.document_id)
    )
    source_document = source_document_result.scalar_one_or_none()
    await db.commit()

    if source_document is not None:
        detect_cycles_task.delay(str(source_document.project_id))

    return DependencyLinkOut(
        id=str(link.id),
        source_item_id=str(link.source_item_id),
        target_item_id=str(link.target_item_id),
        relationship_type=link.relationship_type.value,
        has_cycle_warning=link.has_cycle_warning,
    )


@router.delete("/dependencies/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dependency_link(
    link_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    del current_user
    result = await db.execute(select(DependencyLink).where(DependencyLink.id == link_id))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dependency link not found")

    source_item = await _get_spec_item_or_404(link.source_item_id, db)
    document_result = await db.execute(select(Document).where(Document.id == source_item.document_id))
    document = document_result.scalar_one_or_none()

    await db.delete(link)
    await db.commit()

    if document is not None:
        detect_cycles_task.delay(str(document.project_id))