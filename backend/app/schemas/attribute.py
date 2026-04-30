"""Attribute Definition Pydantic schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

VALID_DATA_TYPES = ("STRING", "INTEGER", "BOOLEAN", "ENUM")


class AttributeValueInput(BaseModel):
    """Input for setting an attribute value on a document."""
    attribute_id: uuid.UUID
    value: Any  # string, int, bool — validated by service layer


class AttributeDefinitionCreate(BaseModel):
    name: str
    data_type: str
    allowed_values: list[str] | None = None
    is_required: bool = False
    standard_id: uuid.UUID | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Attribute name cannot be empty")
        if len(v) > 100:
            raise ValueError("Attribute name must be 100 characters or less")
        return v

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, v: str) -> str:
        if v not in VALID_DATA_TYPES:
            raise ValueError(f"data_type must be one of {VALID_DATA_TYPES}")
        return v

    @model_validator(mode="after")
    def validate_enum_allowed_values(self) -> "AttributeDefinitionCreate":
        if self.data_type == "ENUM":
            if not self.allowed_values:
                raise ValueError(
                    "allowed_values must be a non-empty list when data_type is ENUM"
                )
        return self


class AttributeDefinitionRead(BaseModel):
    id: uuid.UUID
    name: str
    data_type: str
    allowed_values: list[str] | None
    is_required: bool
    standard_id: uuid.UUID | None
    standard_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AttributeValueRead(BaseModel):
    """Serialized attribute value for document responses."""
    attribute_id: uuid.UUID
    name: str
    data_type: str
    value: Any  # Unified value field


class AttributeDefinitionListResponse(BaseModel):
    items: list[AttributeDefinitionRead]
    total: int
    page: int
    page_size: int
