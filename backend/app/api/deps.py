"""FastAPI shared dependencies: get_current_user, require_role, RBAC helpers (FR-004)."""
import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.org import ProjectRoleAssignment, User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT; return User ORM object."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_exception
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub", "")
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Fetch a project by ID or raise 404."""
    from app.models.org import Project  # local import to avoid circular
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def require_role(*role_names: str):  # type: ignore[no-untyped-def]
    """
    Dependency factory — raises 403 if current user does not hold one of the given roles
    in any project (global role check; project-scoped checks use check_project_permission).
    """
    async def _check(current_user: CurrentUser, db: AsyncSession = Depends(get_db)) -> User:
        result = await db.execute(
            select(ProjectRoleAssignment)
            .join(ProjectRoleAssignment.role)
            .where(ProjectRoleAssignment.user_id == current_user.id)
        )
        assignments = result.scalars().all()
        user_roles = {a.role.name for a in assignments}
        if not user_roles.intersection(set(role_names)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {list(role_names)}",
            )
        return current_user
    return _check


async def check_project_permission(
    user: User,
    project_id: uuid.UUID,
    permission_key: str,
    db: AsyncSession,
) -> bool:
    """Check if user holds a role with `permission_key` in the given project."""
    result = await db.execute(
        select(ProjectRoleAssignment)
        .join(ProjectRoleAssignment.role)
        .where(
            ProjectRoleAssignment.user_id == user.id,
            ProjectRoleAssignment.project_id == project_id,
        )
    )
    assignments = result.scalars().all()
    for assignment in assignments:
        if assignment.role.permissions.get(permission_key):
            return True
    return False
