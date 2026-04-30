"""Documents API endpoints - full CRUD, status machine, version history."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.crud import document as crud_document
from app.crud import partition as crud_partition
from app.db.session import get_db
from app.models.document import Document
from app.schemas.attribute import AttributeValueRead
from app.schemas.document import (
    DocumentCreate,
    DocumentListResponse,
    DocumentRead,
    DocumentUpdate,
    StatusTransitionRequest,
    VersionHistoryResponse,
    VersionListItem,
    VersionRead,
)
from app.schemas.user import UserInToken
from app.services import attribute_service
from app.services import document_state_machine as state_machine

router = APIRouter()


def _serialize_document(doc: Document) -> DocumentRead:
    """Serialize a document ORM object to DocumentRead schema."""
    attributes: list[AttributeValueRead] = []
    for dav in doc.attribute_values:
        value = attribute_service.resolve_value_from_dav(dav)
        attr_def = dav.attribute_definition
        attributes.append(
            AttributeValueRead(
                attribute_id=dav.attribute_id,
                name=attr_def.name if attr_def else str(dav.attribute_id),
                data_type=attr_def.data_type if attr_def else "STRING",
                value=value,
            )
        )

    return DocumentRead(
        id=doc.id,
        project_id=doc.project_id,
        partition_id=doc.partition_id,
        title=doc.title,
        content_md=doc.content_md,
        version=doc.version,
        status=doc.status,
        owner_id=doc.owner_id,
        version_lock=doc.version_lock,
        attributes=attributes,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


async def _check_partition_access_for_document(
    db: AsyncSession, doc: Document, user: UserInToken
) -> None:
    """Check if user has access to the document's partition."""
    if user.role == "Admin":
        return
    partition = await crud_partition.get_partition(db, doc.partition_id)
    if not partition:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "Access denied", "code": "FORBIDDEN"},
        )
    if partition.name not in user.partition_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "No access to this document's partition", "code": "FORBIDDEN"},
        )


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(
    doc_in: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> DocumentRead:
    """Create a new document with initial version 1.0 and DRAFT status."""
    # Validate partition belongs to project
    valid = await crud_partition.validate_partition_belongs_to_project(
        db, doc_in.partition_id, doc_in.project_id
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "detail": "partition_id does not belong to the specified project_id",
                "code": "PARTITION_PROJECT_MISMATCH",
            },
        )

    # Validate and check required attributes
    validated_attrs = await attribute_service.validate_and_prepare_attributes(
        db, doc_in.attributes
    )
    await attribute_service.check_required_attributes(db, validated_attrs)

    # Create document
    doc = await crud_document.create_document(db, doc_in, owner_id=current_user.user_id)

    # Upsert attribute values
    if validated_attrs:
        await crud_document.upsert_attribute_values(db, doc.id, validated_attrs)

    # Write audit log
    await state_machine.write_audit_log(
        db,
        doc_id=doc.id,
        operator_id=current_user.user_id,
        action_type="DOCUMENT_CREATED",
        new_status="DRAFT",
    )

    # Reload with attributes
    await db.refresh(doc)
    doc = await crud_document.get_document(db, doc.id)
    return _serialize_document(doc)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    project_id: Optional[uuid.UUID] = Query(None),
    partition_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    owner_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> DocumentListResponse:
    """List documents with optional filters and pagination."""
    items, total = await crud_document.get_documents(
        db,
        project_id=project_id,
        partition_id=partition_id,
        status=status_filter,
        owner_id=owner_id,
        page=page,
        page_size=page_size,
    )

    # Filter by partition access for non-admin users
    if current_user.role != "Admin":
        filtered_items = []
        for doc in items:
            partition = await crud_partition.get_partition(db, doc.partition_id)
            if partition and partition.name in current_user.partition_access:
                filtered_items.append(doc)
        items = filtered_items
        total = len(filtered_items)

    from app.schemas.document import DocumentListItem
    return DocumentListResponse(
        items=[DocumentListItem.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{doc_id}", response_model=DocumentRead)
async def get_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> DocumentRead:
    """Get a document by ID with all attributes."""
    doc = await crud_document.get_document(db, doc_id)
    if not doc:
        # Return 403 to not reveal existence (per spec US1 AC-4)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "Access denied or document not found", "code": "FORBIDDEN"},
        )

    await _check_partition_access_for_document(db, doc, current_user)
    return _serialize_document(doc)


@router.put("/{doc_id}", response_model=DocumentRead)
async def update_document(
    doc_id: uuid.UUID,
    doc_update: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> DocumentRead:
    """Update a document. Creates version snapshot before update."""
    doc = await crud_document.get_document(db, doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Document '{doc_id}' not found", "code": "NOT_FOUND"},
        )

    await _check_partition_access_for_document(db, doc, current_user)

    # Approved documents cannot be directly modified
    if doc.status == "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": "Cannot modify an APPROVED document. Create a new version (Version Fork) instead.",
                "code": "DOCUMENT_APPROVED",
            },
        )

    # Optimistic lock check
    if doc_update.version_lock is not None and doc_update.version_lock != doc.version_lock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": f"Version conflict. Current version_lock is {doc.version_lock}",
                "code": "VERSION_CONFLICT",
            },
        )

    # Save current state as version snapshot before updating
    await crud_document.save_version_snapshot(
        db,
        doc,
        modified_by=current_user.user_id,
        commit_message=doc_update.commit_message,
    )

    # Compute new version
    new_version = state_machine.increment_minor_version(doc.version)

    # Update document
    await crud_document.update_document_fields(
        db,
        doc,
        title=doc_update.title,
        content_md=doc_update.content_md,
        new_version=new_version,
        version_lock=doc.version_lock + 1,
    )

    # Handle attributes update
    if doc_update.attributes is not None:
        validated_attrs = await attribute_service.validate_and_prepare_attributes(
            db, doc_update.attributes
        )
        await crud_document.upsert_attribute_values(db, doc_id, validated_attrs)

    # Write audit log
    await state_machine.write_audit_log(
        db,
        doc_id=doc.id,
        operator_id=current_user.user_id,
        action_type="CONTENT_UPDATE",
        metadata={"new_version": new_version, "commit_message": doc_update.commit_message},
    )

    # Reload
    doc = await crud_document.get_document(db, doc_id)
    return _serialize_document(doc)


@router.patch("/{doc_id}/status", response_model=DocumentRead)
async def transition_status(
    doc_id: uuid.UUID,
    transition: StatusTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> DocumentRead:
    """Transition document status. Validates state machine and RBAC."""
    doc = await crud_document.get_document(db, doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Document '{doc_id}' not found", "code": "NOT_FOUND"},
        )

    await _check_partition_access_for_document(db, doc, current_user)

    old_status = doc.status
    new_status = transition.status

    # Validate state machine transition
    state_machine.validate_status_transition(old_status, new_status)

    # Check RBAC permission for this transition
    state_machine.check_transition_permission(
        new_status, current_user.role, doc, current_user.user_id
    )

    # Update status
    await crud_document.update_document_status(db, doc, new_status)

    # Write audit log (atomic with status update)
    await state_machine.write_audit_log(
        db,
        doc_id=doc.id,
        operator_id=current_user.user_id,
        action_type="STATUS_TRANSITION",
        old_status=old_status,
        new_status=new_status,
    )

    # Reload
    doc = await crud_document.get_document(db, doc_id)
    return _serialize_document(doc)


@router.get("/{doc_id}/versions", response_model=VersionHistoryResponse)
async def get_version_history(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> VersionHistoryResponse:
    """Get version history for a document."""
    doc = await crud_document.get_document(db, doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Document '{doc_id}' not found", "code": "NOT_FOUND"},
        )

    await _check_partition_access_for_document(db, doc, current_user)

    versions = await crud_document.get_document_versions(db, doc_id)
    return VersionHistoryResponse(
        document_id=doc_id,
        current_version=doc.version,
        versions=[VersionListItem.model_validate(v) for v in versions],
    )


@router.get("/{doc_id}/versions/{version}", response_model=VersionRead)
async def get_version_snapshot(
    doc_id: uuid.UUID,
    version: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> VersionRead:
    """Get a specific version snapshot of a document."""
    doc = await crud_document.get_document(db, doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Document '{doc_id}' not found", "code": "NOT_FOUND"},
        )

    await _check_partition_access_for_document(db, doc, current_user)

    ver = await crud_document.get_document_version(db, doc_id, version)
    if not ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Version '{version}' not found for document '{doc_id}'",
                "code": "NOT_FOUND",
            },
        )

    return VersionRead.model_validate(ver)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> None:
    """Delete a document. Admin only. Fails if document has traceability links."""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "Only Admin can delete documents", "code": "FORBIDDEN"},
        )

    doc = await crud_document.get_document(db, doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Document '{doc_id}' not found", "code": "NOT_FOUND"},
        )

    # Check for traceability links
    has_links = await crud_document.has_traceability_links(db, doc_id)
    if has_links:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": "Cannot delete document with existing traceability links. Remove links first or set status to OBSOLETE.",
                "code": "DOCUMENT_HAS_DEPENDENCIES",
            },
        )

    await crud_document.delete_document(db, doc)
