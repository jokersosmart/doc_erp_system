from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from app.services.attribute_validation_service import AttributeValidationService


def test_missing_required_keys_detects_absent_attributes() -> None:
    service = AttributeValidationService(session=AsyncMock())

    missing = service.missing_required_keys(
        required_keys={"safety_goal", "asil_level"},
        attributes=[{"attribute_key": "safety_goal", "value_string": "Brake plausibility"}],
    )

    assert missing == ["asil_level"]


def test_missing_required_keys_accepts_non_string_value_types() -> None:
    service = AttributeValidationService(session=AsyncMock())

    missing = service.missing_required_keys(
        required_keys={"risk_score", "is_redundant"},
        attributes=[
            {"attribute_key": "risk_score", "value_integer": 7},
            {"attribute_key": "is_redundant", "value_boolean": False},
        ],
    )

    assert missing == []


def test_collect_populated_keys_skips_empty_values() -> None:
    service = AttributeValidationService(session=AsyncMock())

    keys = service.collect_populated_attribute_keys(
        attributes=[
            {"attribute_key": "safety_goal", "value_string": ""},
            {"attribute_key": "owner", "value_string": "QRA"},
            {"attribute_key": "next_review", "value_date": None},
        ]
    )

    assert keys == {"owner"}
