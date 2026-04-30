"""Project CRUD operations."""
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.project import Project
from app.schemas.project import ProjectCreate


async def create_project(db: AsyncSession, project_in: ProjectCreate) -> Project:
    """Create a new project."""
    project = Project(
        id=uuid.uuid4(),
        name=project_in.name,
        description=project_in.description,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Optional[Project]:
    """Get a project by ID."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def get_projects(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[Project], int]:
    """Get paginated list of projects."""
    offset = (page - 1) * page_size

    count_result = await db.execute(select(func.count(Project.id)))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Project).order_by(Project.created_at.desc()).offset(offset).limit(page_size)
    )
    items = list(result.scalars().all())
    return items, total


async def has_documents(db: AsyncSession, project_id: uuid.UUID) -> bool:
    """Check if a project has any documents."""
    result = await db.execute(
        select(func.count(Document.id)).where(Document.project_id == project_id)
    )
    count = result.scalar_one()
    return count > 0


async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> bool:
    """Delete a project. Returns True if deleted."""
    project = await get_project(db, project_id)
    if not project:
        return False
    await db.delete(project)
    await db.flush()
    return True
