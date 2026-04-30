"""Partitions API endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.crud import partition as crud_partition
from app.crud import project as crud_project
from app.db.session import get_db
from app.schemas.partition import PartitionCreate, PartitionListResponse, PartitionRead
from app.schemas.user import UserInToken

router = APIRouter()


@router.post("", response_model=PartitionRead, status_code=status.HTTP_201_CREATED)
async def create_partition(
    partition_in: PartitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(require_role("Admin")),
) -> PartitionRead:
    """Create a new partition. Admin only."""
    # Verify project exists
    project = await crud_project.get_project(db, partition_in.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Project '{partition_in.project_id}' not found",
                "code": "NOT_FOUND",
            },
        )

    partition = await crud_partition.create_partition(db, partition_in)
    return PartitionRead.model_validate(partition)


@router.get("", response_model=PartitionListResponse)
async def list_partitions(
    project_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> PartitionListResponse:
    """List partitions with optional project filter."""
    items, total = await crud_partition.get_partitions(
        db, project_id=project_id, page=page, page_size=page_size
    )
    return PartitionListResponse(
        items=[PartitionRead.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{partition_id}", response_model=PartitionRead)
async def get_partition(
    partition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> PartitionRead:
    """Get a partition by ID."""
    partition = await crud_partition.get_partition(db, partition_id)
    if not partition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Partition '{partition_id}' not found", "code": "NOT_FOUND"},
        )
    return PartitionRead.model_validate(partition)
