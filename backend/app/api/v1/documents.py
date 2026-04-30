"""
Documents API (T037 + T043 + T051 + T052 + T054 + T080).
T037: GET /api/v1/projects/{id}/documents — list documents with lifecycle/lock/owner.
T043: GET/PATCH /api/v1/documents/{id}, POST /api/v1/documents/{id}/versions.
Additional Phase 5 endpoints add lifecycle, lock, and diff behaviour.
"""
from __future__ import annotations

import difflib
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.models.audit_package import AuditTrailEntry
from app.models.document import Document, DocumentVersion, LifecycleState, LockState
from app.models.lock_event import LockEvent
from app.models.org import Project, ProjectRoleAssignment, User, WizardSession
from app.tasks.cascade_lock import apply_cascade_lock as apply_cascade_lock_task
from app.tasks.obsolete_scan import scan_obsolete_downstream as scan_obsolete_downstream_task

router = APIRouter(tags=["documents"])


class DocumentSummary(BaseModel):
    id: str
    title: str
    partition: str
    lifecycle_state: str
    lock_state: str
    is_safety_critical: bool
    owner_name: str | None
    updated_at: str


class DocumentDetail(BaseModel):
    id: str
    project_id: str
    title: str
    partition: str
    lifecycle_state: str
    lock_state: str
    is_safety_critical: bool
    current_version: int
    schema_version: str | None
    git_commit_sha: str | None
    owner_name: str | None
    content_markdown: str
    revision_requested: bool
    updated_at: str


class WizardCompleteBody(BaseModel):
    session_id: str
    answers_json: dict[str, Any]


class WizardCompleteOut(BaseModel):
    id: str


class DocumentPatch(BaseModel):
    title: str | None = None
    content_markdown: str | None = None
    current_version: int


class VersionOut(BaseModel):
    id: str
    version_number: int
    created_at: str


class LifecycleTransitionBody(BaseModel):
    target_state: LifecycleState
    comment: str | None = None


class DocumentLockAction(BaseModel):
    action: Literal["mark_reviewed", "qra_approve", "emergency_override", "request_revision"]
    reason: str | None = None
    comment: str | None = None


class DocumentDiffOut(BaseModel):
    upstream_document_id: str
    upstream_title: str
    diff: str


async def _get_document_or_404(document_id: uuid.UUID, db: AsyncSession) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


async def _get_owner_name(owner_id: uuid.UUID | None, db: AsyncSession) -> str | None:
    if owner_id is None:
        return None
    result = await db.execute(select(User).where(User.id == owner_id))
    owner = result.scalar_one_or_none()
    if owner is None:
        return None
    return owner.display_name or owner.username


async def _serialise_document(document: Document, db: AsyncSession) -> DocumentDetail:
    return DocumentDetail(
        id=str(document.id),
        project_id=str(document.project_id),
        title=document.title,
        partition=document.partition or "UNASSIGNED",
        lifecycle_state=document.lifecycle_state.value,
        lock_state=document.lock_state.value,
        is_safety_critical=document.is_safety_critical,
        current_version=document.current_version,
        schema_version=document.schema_version,
        git_commit_sha=document.git_commit_sha,
        owner_name=await _get_owner_name(document.owner_id, db),
        content_markdown=document.content_markdown,
        revision_requested=document.revision_requested,
        updated_at=document.updated_at.isoformat(),
    )


async def _get_project_role_names(
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    db: AsyncSession,
) -> set[str]:
    result = await db.execute(
        select(ProjectRoleAssignment)
        .join(ProjectRoleAssignment.role)
        .where(
            ProjectRoleAssignment.user_id == user_id,
            ProjectRoleAssignment.project_id == project_id,
        )
    )
    return {assignment.role.name for assignment in result.scalars().all()}


@router.get("/projects/{project_id}/documents", response_model=list[DocumentSummary])
async def list_project_documents(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[DocumentSummary]:
    del current_user
    result = await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.partition, Document.title)
    )
    documents = result.scalars().all()

    owner_ids = {document.owner_id for document in documents if document.owner_id}
    owner_map: dict[uuid.UUID, str] = {}
    if owner_ids:
        owner_result = await db.execute(select(User).where(User.id.in_(owner_ids)))
        for owner in owner_result.scalars().all():
            owner_map[owner.id] = owner.display_name or owner.username

    return [
        DocumentSummary(
            id=str(document.id),
            title=document.title,
            partition=document.partition or "UNASSIGNED",
            lifecycle_state=document.lifecycle_state.value,
            lock_state=document.lock_state.value,
            is_safety_critical=document.is_safety_critical,
            owner_name=owner_map.get(document.owner_id) if document.owner_id else None,
            updated_at=document.updated_at.isoformat(),
        )
        for document in documents
    ]


@router.get("/documents/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    del current_user
    document = await _get_document_or_404(document_id, db)
    return await _serialise_document(document, db)


@router.post("/wizard/complete", response_model=WizardCompleteOut, status_code=status.HTTP_201_CREATED)
async def wizard_complete(
    body: WizardCompleteBody,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WizardCompleteOut:
    from app.services.ai_consultant import generate_document_framework

    session_result = await db.execute(
        select(WizardSession).where(
            WizardSession.id == uuid.UUID(body.session_id),
            WizardSession.user_id == current_user.id,
        )
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wizard session not found")

    answers = body.answers_json
    bu_node_id_map = {
        "SSD_CONTROLLER": uuid.UUID("10000000-0000-0000-0000-000000000002"),
        "EMMC": uuid.UUID("10000000-0000-0000-0000-000000000003"),
        "NAND_FLASH": uuid.UUID("10000000-0000-0000-0000-000000000004"),
    }
    bu = answers.get("bu", "SSD_CONTROLLER")
    bu_node_id = bu_node_id_map.get(bu, uuid.UUID("10000000-0000-0000-0000-000000000002"))

    project = Project(
        name=answers.get("project_name", "Unnamed Project"),
        bu_node_id=bu_node_id,
        aspice_level=answers.get("aspice_level"),
        asil_level=(
            answers.get("asil_cal_level")
            if str(answers.get("asil_cal_level", "")).startswith("ASIL")
            else None
        ),
        cal_level=(
            answers.get("asil_cal_level")
            if str(answers.get("asil_cal_level", "")).startswith("CAL")
            else None
        ),
        standards=[standard for standard in answers.get("safety_standards", []) if standard != "NONE"],
        git_backend_type=answers.get("git_backend", "gerrit"),
        created_by=current_user.id,
    )
    db.add(project)
    await db.flush()

    session.answers_json = answers
    session.is_complete = True

    await generate_document_framework(session, project, db)
    await db.commit()

    return WizardCompleteOut(id=str(project.id))


@router.get("/wizard/questions")
async def get_wizard_questions(current_user: CurrentUser) -> list[dict[str, Any]]:
    del current_user
    from app.services.ai_consultant import generate_wizard_questions

    return generate_wizard_questions()


@router.patch("/documents/{document_id}", response_model=DocumentDetail)
async def patch_document(
    document_id: uuid.UUID,
    body: DocumentPatch,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    """FR-015b: optimistic lock update with version snapshot creation."""
    document = await _get_document_or_404(document_id, db)

    if document.current_version != body.current_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "conflict": True,
                "your_version": body.current_version,
                "db_version": document.current_version,
                "detail": "Concurrent modification detected — resolve conflict manually",
            },
        )

    content_changed = body.content_markdown is not None and body.content_markdown != document.content_markdown
    if body.title is not None:
        document.title = body.title
    if body.content_markdown is not None:
        document.content_markdown = body.content_markdown

    document.current_version += 1
    db.add(
        DocumentVersion(
            document_id=document.id,
            version_number=document.current_version,
            content_markdown=document.content_markdown,
            lifecycle_state_snapshot=document.lifecycle_state.value,
            lock_state_snapshot=document.lock_state.value,
            committed_by=current_user.id,
        )
    )
    db.add(
        AuditTrailEntry(
            document_id=document.id,
            actor_id=current_user.id,
            action="document_updated",
            detail={"current_version": document.current_version},
        )
    )

    await db.commit()
    await db.refresh(document)

    if (
        content_changed
        and document.partition == "SYS"
        and document.lifecycle_state in {LifecycleState.REVIEW, LifecycleState.APPROVED}
    ):
        apply_cascade_lock_task.delay(str(document.id), str(current_user.id))

    return await _serialise_document(document, db)


@router.patch("/documents/{document_id}/lifecycle", response_model=DocumentDetail)
async def transition_document_lifecycle(
    document_id: uuid.UUID,
    body: LifecycleTransitionBody,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    document = await _get_document_or_404(document_id, db)

    allowed_transitions = {
        LifecycleState.DRAFT: {LifecycleState.REVIEW},
        LifecycleState.REVIEW: {LifecycleState.APPROVED},
        LifecycleState.APPROVED: {LifecycleState.OBSOLETE},
        LifecycleState.OBSOLETE: set(),
    }
    if body.target_state not in allowed_transitions[document.lifecycle_state]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid lifecycle transition: {document.lifecycle_state.value} -> "
                f"{body.target_state.value}"
            ),
        )

    previous_state = document.lifecycle_state
    document.lifecycle_state = body.target_state
    if body.target_state == LifecycleState.APPROVED:
        document.lock_state = LockState.UNLOCKED
        document.revision_requested = False

    db.add(
        AuditTrailEntry(
            document_id=document.id,
            actor_id=current_user.id,
            action="lifecycle_changed",
            detail={
                "from": previous_state.value,
                "to": body.target_state.value,
                "comment": body.comment,
            },
        )
    )

    await db.commit()
    await db.refresh(document)

    if body.target_state == LifecycleState.OBSOLETE:
        scan_obsolete_downstream_task.delay(str(document.id))

    return await _serialise_document(document, db)


@router.patch("/documents/{document_id}/lock", response_model=DocumentDetail)
async def update_document_lock(
    document_id: uuid.UUID,
    body: DocumentLockAction,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    document = await _get_document_or_404(document_id, db)
    role_names = await _get_project_role_names(current_user.id, document.project_id, db)

    if body.action == "mark_reviewed":
        if document.lock_state != LockState.LOCKED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is not locked")
        if document.is_safety_critical:
            document.lock_state = LockState.PENDING_QRA
            audit_action = "pending_qra_approval"
        else:
            document.lock_state = LockState.UNLOCKED
            document.lifecycle_state = LifecycleState.APPROVED
            document.revision_requested = False
            audit_action = "lock_cleared"
    elif body.action == "qra_approve":
        if not role_names.intersection({"AUDITOR_QRA", "QRA", "ADMIN"}):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="QRA approval required")
        if document.lock_state != LockState.PENDING_QRA:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is not pending QRA")
        document.lock_state = LockState.UNLOCKED
        document.lifecycle_state = LifecycleState.APPROVED
        document.revision_requested = False
        audit_action = "qra_approved"
    elif body.action == "emergency_override":
        if not role_names.intersection({"PM", "MANAGER", "ADMIN"}):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="PM, Manager, or Admin role required",
            )
        if document.lock_state != LockState.PENDING_QRA:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is not pending QRA")
        if not body.reason:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="reason is required")
        document.lock_state = LockState.UNLOCKED
        document.lifecycle_state = LifecycleState.APPROVED
        document.revision_requested = False
        audit_action = "emergency_override"
    else:
        if not role_names.intersection({"AUDITOR_QRA", "QRA", "ADMIN"}):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="QRA role required")
        if document.lock_state != LockState.PENDING_QRA:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document is not pending QRA")
        document.revision_requested = True
        audit_action = "revision_requested"

    db.add(
        AuditTrailEntry(
            document_id=document.id,
            actor_id=current_user.id,
            action=audit_action,
            detail={"reason": body.reason, "comment": body.comment},
        )
    )

    await db.commit()
    await db.refresh(document)
    return await _serialise_document(document, db)


@router.get("/documents/{document_id}/diff", response_model=DocumentDiffOut)
async def get_document_diff(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DocumentDiffOut:
    del current_user
    lock_events_result = await db.execute(
        select(LockEvent).order_by(LockEvent.triggered_at.desc())
    )
    lock_event = next(
        (
            event
            for event in lock_events_result.scalars().all()
            if document_id in (event.locked_document_ids or [])
        ),
        None,
    )
    if lock_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No lock event found")

    upstream_document = await _get_document_or_404(lock_event.upstream_document_id, db)
    version_result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == upstream_document.id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(2)
    )
    versions = list(version_result.scalars().all())

    current_content = versions[0].content_markdown if versions else upstream_document.content_markdown
    previous_content = versions[1].content_markdown if len(versions) > 1 else ""
    diff = lock_event.notes or "".join(
        difflib.unified_diff(
            previous_content.splitlines(keepends=True),
            current_content.splitlines(keepends=True),
            fromfile="upstream_previous.md",
            tofile="upstream_current.md",
        )
    )

    return DocumentDiffOut(
        upstream_document_id=str(upstream_document.id),
        upstream_title=upstream_document.title,
        diff=diff,
    )


@router.post("/documents/{document_id}/versions", response_model=VersionOut, status_code=status.HTTP_201_CREATED)
async def create_version_snapshot(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> VersionOut:
    document = await _get_document_or_404(document_id, db)
    version = DocumentVersion(
        document_id=document.id,
        version_number=document.current_version,
        content_markdown=document.content_markdown,
        lifecycle_state_snapshot=document.lifecycle_state.value,
        lock_state_snapshot=document.lock_state.value,
        committed_by=current_user.id,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return VersionOut(
        id=str(version.id),
        version_number=version.version_number,
        created_at=version.created_at.isoformat(),
    )
