"""Partition CRUD operations."""
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.partition import Partition
from app.schemas.partition import PartitionCreate


async def create_partition(
    db: AsyncSession, partition_in: PartitionCreate
) -> Partition:
    """Create a new partition."""
    partition = Partition(
        id=uuid.uuid4(),
        project_id=partition_in.project_id,
        name=partition_in.name,
        description=partition_in.description,
    )
    db.add(partition)
    await db.flush()
    await db.refresh(partition)
    return partition


async def get_partition(
    db: AsyncSession, partition_id: uuid.UUID
) -> Optional[Partition]:
    """Get a partition by ID."""
    result = await db.execute(
        select(Partition).where(Partition.id == partition_id)
    )
    return result.scalar_one_or_none()


async def get_partitions(
    db: AsyncSession,
    project_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Partition], int]:
    """Get paginated list of partitions, optionally filtered by project."""
    query = select(Partition)
    count_query = select(func.count(Partition.id))
    if project_id:
        query = query.where(Partition.project_id == project_id)
        count_query = count_query.where(Partition.project_id == project_id)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Partition.created_at.desc()).offset(offset).limit(page_size)
    )
    items = list(result.scalars().all())
    return items, total


async def validate_partition_belongs_to_project(
    db: AsyncSession, partition_id: uuid.UUID, project_id: uuid.UUID
) -> bool:
    """Check if a partition belongs to a given project."""
    result = await db.execute(
        select(Partition).where(
            Partition.id == partition_id, Partition.project_id == project_id
        )
    )
    return result.scalar_one_or_none() is not None
