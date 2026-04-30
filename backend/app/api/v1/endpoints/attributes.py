"""Attribute Definitions API endpoints."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.crud import attribute as crud_attribute
from app.db.session import get_db
from app.models.standard import Standard
from app.schemas.attribute import (
    AttributeDefinitionCreate,
    AttributeDefinitionListResponse,
    AttributeDefinitionRead,
)
from app.schemas.user import UserInToken

router = APIRouter()


@router.post(
    "", response_model=AttributeDefinitionRead, status_code=status.HTTP_201_CREATED
)
async def create_attribute_definition(
    attr_in: AttributeDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(require_role("Admin")),
) -> AttributeDefinitionRead:
    """Create a new attribute definition. Admin only."""
    # Validate standard_id if provided
    standard_name = None
    if attr_in.standard_id:
        result = await db.execute(
            select(Standard).where(Standard.id == attr_in.standard_id)
        )
        standard = result.scalar_one_or_none()
        if not standard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "detail": f"Standard '{attr_in.standard_id}' not found",
                    "code": "NOT_FOUND",
                },
            )
        standard_name = standard.name

    attr = await crud_attribute.create_attribute_definition(db, attr_in)
    return AttributeDefinitionRead(
        id=attr.id,
        name=attr.name,
        data_type=attr.data_type,
        allowed_values=attr.allowed_values,
        is_required=attr.is_required,
        standard_id=attr.standard_id,
        standard_name=standard_name,
        created_at=attr.created_at,
        updated_at=attr.updated_at,
    )


@router.get("", response_model=AttributeDefinitionListResponse)
async def list_attribute_definitions(
    standard_id: Optional[uuid.UUID] = Query(None),
    is_required: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> AttributeDefinitionListResponse:
    """List attribute definitions with optional filters."""
    items, total = await crud_attribute.get_attribute_definitions(
        db, standard_id=standard_id, is_required=is_required, page=page, page_size=page_size
    )

    result_items = []
    for attr in items:
        standard_name = None
        if attr.standard_id and attr.standard:
            standard_name = attr.standard.name
        result_items.append(
            AttributeDefinitionRead(
                id=attr.id,
                name=attr.name,
                data_type=attr.data_type,
                allowed_values=attr.allowed_values,
                is_required=attr.is_required,
                standard_id=attr.standard_id,
                standard_name=standard_name,
                created_at=attr.created_at,
                updated_at=attr.updated_at,
            )
        )

    return AttributeDefinitionListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{attr_id}", response_model=AttributeDefinitionRead)
async def get_attribute_definition(
    attr_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user),
) -> AttributeDefinitionRead:
    """Get an attribute definition by ID."""
    attr = await crud_attribute.get_attribute_definition(db, attr_id)
    if not attr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Attribute definition '{attr_id}' not found", "code": "NOT_FOUND"},
        )

    standard_name = None
    if attr.standard_id and attr.standard:
        standard_name = attr.standard.name

    return AttributeDefinitionRead(
        id=attr.id,
        name=attr.name,
        data_type=attr.data_type,
        allowed_values=attr.allowed_values,
        is_required=attr.is_required,
        standard_id=attr.standard_id,
        standard_name=standard_name,
        created_at=attr.created_at,
        updated_at=attr.updated_at,
    )
