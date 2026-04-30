"""Attribute EAV validation service."""
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.attribute import get_attributes_by_ids, get_required_attribute_ids
from app.models.attribute import AttributeDefinition
from app.schemas.attribute import AttributeValueInput


def validate_attribute_value(
    attr_def: AttributeDefinition, value: Any
) -> tuple[Any, str]:
    """Validate a single attribute value against its definition.

    Returns (validated_value, value_column) tuple.
    Raises HTTPException 422 on invalid value.

    value_column is one of: value_string, value_integer, value_boolean
    """
    data_type = attr_def.data_type

    if data_type == "STRING":
        if not isinstance(value, str):
            value = str(value)
        return value, "value_string"

    elif data_type == "INTEGER":
        if isinstance(value, bool):
            raise HTTPException(
                status_code=422,
                detail={
                    "detail": f"Attribute '{attr_def.name}' expects INTEGER, got boolean",
                    "code": "INVALID_ATTRIBUTE_VALUE",
                },
            )
        try:
            int_val = int(value)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=422,
                detail={
                    "detail": f"Attribute '{attr_def.name}' expects INTEGER, got '{value}'",
                    "code": "INVALID_ATTRIBUTE_VALUE",
                },
            )
        return int_val, "value_integer"

    elif data_type == "BOOLEAN":
        if not isinstance(value, bool):
            raise HTTPException(
                status_code=422,
                detail={
                    "detail": (
                        f"Attribute '{attr_def.name}' expects BOOLEAN (true/false), "
                        f"got '{value}'. String values like 'yes'/'no' are not accepted."
                    ),
                    "code": "INVALID_ATTRIBUTE_VALUE",
                },
            )
        return value, "value_boolean"

    elif data_type == "ENUM":
        allowed = attr_def.allowed_values or []
        if value not in allowed:
            raise HTTPException(
                status_code=422,
                detail={
                    "detail": (
                        f"Attribute '{attr_def.name}' value '{value}' is not in allowed values: {allowed}"
                    ),
                    "code": "INVALID_ATTRIBUTE_VALUE",
                },
            )
        return str(value), "value_string"

    else:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": f"Unknown data_type '{data_type}' for attribute '{attr_def.name}'",
                "code": "INVALID_ATTRIBUTE_VALUE",
            },
        )


async def validate_and_prepare_attributes(
    db: AsyncSession,
    attribute_inputs: list[AttributeValueInput],
) -> list[AttributeValueInput]:
    """Validate all attribute inputs against their definitions.

    Returns updated list with properly typed values.
    Raises HTTPException 422 on any validation failure.
    """
    if not attribute_inputs:
        return []

    # De-duplicate (last wins)
    deduped: dict[uuid.UUID, AttributeValueInput] = {}
    for inp in attribute_inputs:
        deduped[inp.attribute_id] = inp

    # Fetch all attribute definitions in one query
    attr_ids = list(deduped.keys())
    attr_defs = await get_attributes_by_ids(db, attr_ids)
    attr_def_map: dict[uuid.UUID, AttributeDefinition] = {
        a.id: a for a in attr_defs
    }

    # Validate each
    validated: list[AttributeValueInput] = []
    for attr_id, inp in deduped.items():
        attr_def = attr_def_map.get(attr_id)
        if not attr_def:
            raise HTTPException(
                status_code=404,
                detail={
                    "detail": f"Attribute definition '{attr_id}' not found",
                    "code": "ATTRIBUTE_NOT_FOUND",
                },
            )
        validated_value, _ = validate_attribute_value(attr_def, inp.value)
        validated.append(AttributeValueInput(attribute_id=attr_id, value=validated_value))

    return validated


async def check_required_attributes(
    db: AsyncSession,
    attribute_inputs: list[AttributeValueInput],
) -> None:
    """Ensure all required attribute definitions have values provided.

    Raises HTTPException 422 if any required attribute is missing.
    """
    required_ids = await get_required_attribute_ids(db)
    if not required_ids:
        return

    provided_ids = {inp.attribute_id for inp in attribute_inputs}
    missing = [str(rid) for rid in required_ids if rid not in provided_ids]

    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "detail": f"Missing required attributes: {missing}",
                "code": "REQUIRED_ATTRIBUTE_MISSING",
            },
        )


def resolve_value_from_dav(dav: Any) -> Any:
    """Extract the unified value from a DocumentAttributeValue ORM object."""
    if dav.value_boolean is not None:
        return dav.value_boolean
    if dav.value_integer is not None:
        return dav.value_integer
    if dav.value_string is not None:
        return dav.value_string
    return None
