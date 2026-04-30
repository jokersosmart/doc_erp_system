"""Attribute Definition CRUD operations."""
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute import AttributeDefinition, DocumentAttributeValue
from app.schemas.attribute import AttributeDefinitionCreate


async def create_attribute_definition(
    db: AsyncSession, attr_in: AttributeDefinitionCreate
) -> AttributeDefinition:
    """Create a new attribute definition."""
    attr = AttributeDefinition(
        id=uuid.uuid4(),
        name=attr_in.name,
        data_type=attr_in.data_type,
        allowed_values=attr_in.allowed_values,
        is_required=attr_in.is_required,
        standard_id=attr_in.standard_id,
    )
    db.add(attr)
    await db.flush()
    await db.refresh(attr)
    return attr


async def get_attribute_definition(
    db: AsyncSession, attr_id: uuid.UUID
) -> Optional[AttributeDefinition]:
    """Get an attribute definition by ID."""
    result = await db.execute(
        select(AttributeDefinition).where(AttributeDefinition.id == attr_id)
    )
    return result.scalar_one_or_none()


async def get_attribute_definitions(
    db: AsyncSession,
    standard_id: Optional[uuid.UUID] = None,
    is_required: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AttributeDefinition], int]:
    """Get paginated attribute definitions with optional filters."""
    query = select(AttributeDefinition)
    count_query = select(func.count(AttributeDefinition.id))

    if standard_id is not None:
        query = query.where(AttributeDefinition.standard_id == standard_id)
        count_query = count_query.where(AttributeDefinition.standard_id == standard_id)
    if is_required is not None:
        query = query.where(AttributeDefinition.is_required == is_required)
        count_query = count_query.where(AttributeDefinition.is_required == is_required)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(AttributeDefinition.created_at.asc()).offset(offset).limit(page_size)
    )
    items = list(result.scalars().all())
    return items, total


async def get_required_attribute_ids(db: AsyncSession) -> list[uuid.UUID]:
    """Get IDs of all required attribute definitions."""
    result = await db.execute(
        select(AttributeDefinition.id).where(AttributeDefinition.is_required == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def get_attributes_by_ids(
    db: AsyncSession, attr_ids: list[uuid.UUID]
) -> list[AttributeDefinition]:
    """Batch fetch attribute definitions by IDs."""
    if not attr_ids:
        return []
    result = await db.execute(
        select(AttributeDefinition).where(AttributeDefinition.id.in_(attr_ids))
    )
    return list(result.scalars().all())
