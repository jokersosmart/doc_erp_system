"""Required dynamic attribute validation for lifecycle transitions."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.models.attribute_definition import AttributeDefinition
from app.models.document import Document
from app.models.standard import Standard


class AttributeValidationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def collect_populated_attribute_keys(attributes: list[dict]) -> set[str]:
        populated_keys: set[str] = set()

        for attribute in attributes:
            key = attribute.get("attribute_key")
            if not key:
                continue

            has_value = any(
                attribute.get(value_field) not in (None, "")
                for value_field in (
                    "value_string",
                    "value_integer",
                    "value_boolean",
                    "value_date",
                )
            )
            if has_value:
                populated_keys.add(key)

        return populated_keys

    @classmethod
    def missing_required_keys(cls, required_keys: set[str], attributes: list[dict]) -> list[str]:
        populated_keys = cls.collect_populated_attribute_keys(attributes)
        return sorted(required_keys.difference(populated_keys))

    async def get_required_keys_for_document(self, document: Document) -> set[str]:
        stmt = select(AttributeDefinition.key).where(AttributeDefinition.is_required.is_(True))
        stmt = stmt.where(
            or_(
                AttributeDefinition.partition_node_id.is_(None),
                AttributeDefinition.partition_node_id == document.bu_node_id,
            )
        )

        standards_scope = document.standards_scope or []
        if standards_scope:
            stmt = stmt.outerjoin(Standard, AttributeDefinition.standard_id == Standard.id)
            stmt = stmt.where(
                or_(
                    AttributeDefinition.standard_id.is_(None),
                    Standard.code.in_(standards_scope),
                )
            )
        else:
            stmt = stmt.where(AttributeDefinition.standard_id.is_(None))

        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def ensure_required_attributes(self, *, document: Document, attributes: list[dict]) -> None:
        required_keys = await self.get_required_keys_for_document(document)
        missing_keys = self.missing_required_keys(required_keys=required_keys, attributes=attributes)

        if missing_keys:
            raise ValidationError(f"Missing required attributes: {', '.join(missing_keys)}")
