"""
Projects API: org hierarchy, project CRUD, AI wizard session endpoints (T028, T030).
FR-001 (org hierarchy), FR-003 (multi-standard config), FR-006 (wizard), FR-043 (auto-save resume).
"""
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.models.org import OrganisationNode, Project, WizardSession

router = APIRouter(tags=["projects"])


# ── Org Hierarchy ─────────────────────────────────────────────────────────────

class OrgNodeOut(BaseModel):
    id: str
    name: str
    level: int
    node_type: str
    bu_scope: str | None
    parent_id: str | None


@router.get("/org/nodes", response_model=list[OrgNodeOut])
async def list_org_nodes(db: AsyncSession = Depends(get_db), _: CurrentUser = Depends()) -> list[OrgNodeOut]:
    result = await db.execute(select(OrganisationNode).order_by(OrganisationNode.level))
    nodes = result.scalars().all()
    return [OrgNodeOut(id=str(n.id), name=n.name, level=n.level, node_type=n.node_type, bu_scope=n.bu_scope, parent_id=str(n.parent_id) if n.parent_id else None) for n in nodes]


# ── Projects ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    bu_node_id: str
    aspice_level: int | None = None
    asil_level: str | None = None
    cal_level: str | None = None
    standards: list[str] = []
    git_backend_type: str = "github"
    git_repo_url: str | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    bu_node_id: str
    aspice_level: int | None
    asil_level: str | None
    cal_level: str | None
    standards: list[str]
    git_backend_type: str


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)) -> ProjectOut:
    project = Project(
        name=body.name,
        bu_node_id=uuid.UUID(body.bu_node_id),
        aspice_level=body.aspice_level,
        asil_level=body.asil_level,
        cal_level=body.cal_level,
        standards=body.standards,
        git_backend_type=body.git_backend_type,
        git_repo_url=body.git_repo_url,
        created_by=current_user.id,
    )
    db.add(project)
    await db.flush()
    return ProjectOut(id=str(project.id), name=project.name, bu_node_id=str(project.bu_node_id), aspice_level=project.aspice_level, asil_level=project.asil_level, cal_level=project.cal_level, standards=project.standards, git_backend_type=project.git_backend_type)


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, _: CurrentUser = Depends(), db: AsyncSession = Depends(get_db)) -> ProjectOut:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectOut(id=str(project.id), name=project.name, bu_node_id=str(project.bu_node_id), aspice_level=project.aspice_level, asil_level=project.asil_level, cal_level=project.cal_level, standards=project.standards, git_backend_type=project.git_backend_type)


# ── Wizard Sessions (FR-043) ──────────────────────────────────────────────────

WIZARD_SESSION_TTL_DAYS = 90


class WizardSessionOut(BaseModel):
    id: str
    step_index: int
    answers_json: dict[str, Any]
    project_context_json: dict[str, Any]
    is_complete: bool
    expires_at: str


class WizardStepPatch(BaseModel):
    step_index: int
    answers_json: dict[str, Any]
    project_context_json: dict[str, Any] = {}


@router.post("/wizard/sessions", response_model=WizardSessionOut, status_code=status.HTTP_201_CREATED)
async def create_wizard_session(current_user: CurrentUser, db: AsyncSession = Depends(get_db)) -> WizardSessionOut:
    session = WizardSession(
        user_id=current_user.id,
        expires_at=datetime.now(UTC) + timedelta(days=WIZARD_SESSION_TTL_DAYS),
    )
    db.add(session)
    await db.flush()
    return _session_out(session)


@router.patch("/wizard/sessions/{session_id}/step", response_model=WizardSessionOut)
async def update_wizard_step(session_id: uuid.UUID, body: WizardStepPatch, current_user: CurrentUser, db: AsyncSession = Depends(get_db)) -> WizardSessionOut:
    result = await db.execute(select(WizardSession).where(WizardSession.id == session_id, WizardSession.user_id == current_user.id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wizard session not found")
    session.step_index = body.step_index
    session.answers_json = body.answers_json
    if body.project_context_json:
        session.project_context_json = body.project_context_json
    await db.flush()
    return _session_out(session)


@router.get("/wizard/sessions/active", response_model=WizardSessionOut | None)
async def get_active_wizard_session(current_user: CurrentUser, db: AsyncSession = Depends(get_db)) -> WizardSessionOut | None:
    result = await db.execute(
        select(WizardSession).where(
            WizardSession.user_id == current_user.id,
            WizardSession.is_complete == False,  # noqa: E712
            WizardSession.expires_at > datetime.now(UTC),
        ).order_by(WizardSession.updated_at.desc()).limit(1)
    )
    session = result.scalar_one_or_none()
    return _session_out(session) if session else None


@router.delete("/wizard/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wizard_session(session_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)) -> None:
    result = await db.execute(select(WizardSession).where(WizardSession.id == session_id, WizardSession.user_id == current_user.id))
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)


def _session_out(session: WizardSession) -> WizardSessionOut:
    return WizardSessionOut(id=str(session.id), step_index=session.step_index, answers_json=session.answers_json, project_context_json=session.project_context_json, is_complete=session.is_complete, expires_at=session.expires_at.isoformat())
