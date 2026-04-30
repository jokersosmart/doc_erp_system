"""Projects and Partitions API endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.crud import project as crud_project
from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectRead
from app.schemas.user import UserInToken

router = APIRouter()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(require_role("Admin")),
) -> ProjectRead:
    """Create a new project. Admin only."""
    project = await crud_project.create_project(db, project_in)
    return ProjectRead.model_validate(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> ProjectListResponse:
    """List all projects with pagination."""
    items, total = await crud_project.get_projects(db, page=page, page_size=page_size)
    return ProjectListResponse(
        items=[ProjectRead.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> ProjectRead:
    """Get a project by ID."""
    project = await crud_project.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Project '{project_id}' not found", "code": "NOT_FOUND"},
        )
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(require_role("Admin")),
) -> None:
    """Delete a project. Fails if project has documents."""
    project = await crud_project.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Project '{project_id}' not found", "code": "NOT_FOUND"},
        )

    has_docs = await crud_project.has_documents(db, project_id)
    if has_docs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": "Cannot delete project with existing documents. Remove all documents first or archive the project.",
                "code": "PROJECT_HAS_DOCUMENTS",
            },
        )

    await crud_project.delete_project(db, project_id)
