"""Document state machine and business logic service."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import document as crud_document
from app.models.audit_log import AuditLog
from app.models.document import Document

# Valid status transitions (from -> set of allowed "to" statuses)
VALID_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"REVIEW"},
    "REVIEW": {"APPROVED", "DRAFT"},
    "APPROVED": {"OBSOLETE"},
    "OBSOLETE": set(),
}

# Role-based transition permissions
# Who can move a document to each target status
TRANSITION_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "REVIEW": {"Admin", "RD", "QA", "PM"},
    "APPROVED": {"Admin", "QA"},
    "OBSOLETE": {"Admin", "QA"},
    "DRAFT": {"Admin", "QA"},
}


def increment_minor_version(version: str) -> str:
    """Increment the minor version number. e.g., '1.0' -> '1.1'"""
    parts = version.split(".")
    major = int(parts[0])
    minor = int(parts[1]) if len(parts) > 1 else 0
    return f"{major}.{minor + 1}"


def increment_major_version(version: str) -> str:
    """Increment the major version (Version Fork). e.g., '1.5' -> '2.0'"""
    parts = version.split(".")
    major = int(parts[0])
    return f"{major + 1}.0"


def validate_status_transition(current_status: str, new_status: str) -> None:
    """Validate that the status transition is legal.

    Raises HTTPException 422 if transition is not allowed.
    """
    if current_status == new_status:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": f"Document is already in status '{current_status}'",
                "code": "INVALID_STATUS_TRANSITION",
            },
        )

    allowed = VALID_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": (
                    f"Cannot transition from '{current_status}' to '{new_status}'. "
                    f"Allowed transitions: {sorted(allowed) if allowed else 'none'}"
                ),
                "code": "INVALID_STATUS_TRANSITION",
            },
        )


def check_transition_permission(
    new_status: str, user_role: str, doc: Document, user_id: str
) -> None:
    """Check if the user has permission to perform the status transition.

    Raises HTTPException 403 if not permitted.
    """
    allowed_roles = TRANSITION_ROLE_PERMISSIONS.get(new_status, set())

    # Admin can do anything
    if user_role == "Admin":
        return

    # RD can only push their own documents to REVIEW
    if user_role == "RD" and new_status == "REVIEW":
        if doc.owner_id != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "detail": "Only the document owner or Admin/QA can advance to REVIEW",
                    "code": "FORBIDDEN",
                },
            )
        return

    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail={
                "detail": f"Role '{user_role}' is not permitted to transition document to '{new_status}'",
                "code": "FORBIDDEN",
            },
        )


async def write_audit_log(
    db: AsyncSession,
    doc_id: uuid.UUID,
    operator_id: str,
    action_type: str,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> AuditLog:
    """Write an audit log entry atomically within the current transaction."""
    log = AuditLog(
        id=uuid.uuid4(),
        document_id=doc_id,
        operator_id=operator_id,
        action_type=action_type,
        old_status=old_status,
        new_status=new_status,
        metadata_=metadata,
    )
    db.add(log)
    # Note: flush to DB but commit is handled by the session context
    await db.flush()
    return log
