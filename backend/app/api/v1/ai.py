"""
AI Consultant API (T039, T041, T042, T044).
POST /api/v1/ai/consult — gap analysis (suggestion-only, FR-007)
POST /api/v1/ai/suggestions/{id}/accept — insert suggestion, write audit trail (FR-008)
POST /api/v1/ai/suggestions/{id}/reject — mark rejected (FR-007, no doc modification)
POST /api/v1/ai/compliance/{document_id} — template compliance check (T044)
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.models.audit_package import AuditTrailEntry
from app.models.document import AISuggestion, AISuggestionStatus, Document
from app.models.spec_item import SpecItem
from app.services import ai_consultant

router = APIRouter(prefix="/ai", tags=["ai"])


# ── T039: POST /consult ────────────────────────────────────────────────────

class ConsultRequest(BaseModel):
    document_id: str
    spec_item_id: str | None = None


class SuggestionOut(BaseModel):
    id: str
    suggested_content: str
    clause_reference: str | None
    severity: str
    type: str
    gap: str | None
    ai_offline_mode: bool


@router.post("/consult", response_model=list[SuggestionOut])
async def consult(
    body: ConsultRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[SuggestionOut]:
    """
    FR-007: Invoke AI gap analysis. Returns suggestions only — no document writes.
    Offline mode returns static rule checklist and ai_offline_mode=True.
    """
    result = await db.execute(select(Document).where(Document.id == uuid.UUID(body.document_id)))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    analysis = await ai_consultant.gap_analysis(body.document_id, body.spec_item_id, db)

    suggestions_out: list[SuggestionOut] = []
    for raw in analysis.get("suggestions", []):
        # Persist pending suggestion record
        suggestion = AISuggestion(
            document_id=doc.id,
            spec_item_id=uuid.UUID(body.spec_item_id) if body.spec_item_id else None,
            suggested_content=raw.get("suggested_content", ""),
            clause_reference=raw.get("clause_reference"),
            status=AISuggestionStatus.PENDING,
        )
        db.add(suggestion)
        await db.flush()
        suggestions_out.append(SuggestionOut(
            id=str(suggestion.id),
            suggested_content=suggestion.suggested_content,
            clause_reference=suggestion.clause_reference,
            severity=raw.get("severity", "info"),
            type=raw.get("type", "ai"),
            gap=raw.get("gap"),
            ai_offline_mode=analysis.get("ai_offline_mode", False),
        ))

    await db.commit()
    return suggestions_out


# ── T041: POST /suggestions/{id}/accept ──────────────────────────────────────

class AcceptOut(BaseModel):
    suggestion_id: str
    spec_item_id: str | None
    audit_entry_id: str


@router.post("/suggestions/{suggestion_id}/accept", response_model=AcceptOut)
async def accept_suggestion(
    suggestion_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AcceptOut:
    """
    FR-008: Accept AI suggestion — inserts content into SpecItem,
    writes audit_trail_entries with 'Suggested by AI, accepted by [user]'.
    """
    result = await db.execute(select(AISuggestion).where(AISuggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
    if suggestion.status != AISuggestionStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Suggestion already {suggestion.status.value}")

    # Insert accepted content into the target SpecItem (if linked)
    if suggestion.spec_item_id:
        si_result = await db.execute(select(SpecItem).where(SpecItem.id == suggestion.spec_item_id))
        spec_item = si_result.scalar_one_or_none()
        if spec_item:
            spec_item.content_markdown = (spec_item.content_markdown or "") + "\n\n" + suggestion.suggested_content

    suggestion.status = AISuggestionStatus.ACCEPTED
    suggestion.accepted_by = current_user.id
    suggestion.accepted_at = datetime.now(UTC)

    # FR-008: audit trail entry
    audit_entry = AuditTrailEntry(
        entity_type="document",
        entity_id=suggestion.document_id,
        action="ai_suggestion_accepted",
        actor_id=current_user.id,
        details={
            "suggestion_id": str(suggestion_id),
            "clause_reference": suggestion.clause_reference,
            "note": f"Suggested by AI, accepted by {current_user.username} on {datetime.now(UTC).isoformat()}",
        },
    )
    db.add(audit_entry)
    await db.flush()
    await db.commit()

    return AcceptOut(
        suggestion_id=str(suggestion_id),
        spec_item_id=str(suggestion.spec_item_id) if suggestion.spec_item_id else None,
        audit_entry_id=str(audit_entry.id),
    )


# ── T042: POST /suggestions/{id}/reject ──────────────────────────────────────

@router.post("/suggestions/{suggestion_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_suggestion(
    suggestion_id: uuid.UUID,
    current_user: CurrentUser,  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    FR-007: Reject suggestion — sets status=REJECTED. No document modification.
    No audit entry written for rejects (FR-007 spec).
    """
    result = await db.execute(select(AISuggestion).where(AISuggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
    suggestion.status = AISuggestionStatus.REJECTED
    await db.commit()


# ── T044: POST /compliance/{document_id} ─────────────────────────────────────

class ComplianceGap(BaseModel):
    attribute_key: str
    label: str
    clause_reference: str | None
    severity: str
    suggested_content: str


@router.post("/compliance/{document_id}", response_model=list[ComplianceGap])
async def check_compliance(
    document_id: uuid.UUID,
    _: CurrentUser = Depends(),
    db: AsyncSession = Depends(get_db),
) -> list[ComplianceGap]:
    """T044: Template compliance check against attribute_definitions registry."""
    gaps = await ai_consultant.check_template_compliance(str(document_id), db)
    return [
        ComplianceGap(
            attribute_key=g["attribute_key"],
            label=g["label"],
            clause_reference=g.get("clause_reference"),
            severity=g["severity"],
            suggested_content=g["suggested_content"],
        )
        for g in gaps
    ]
