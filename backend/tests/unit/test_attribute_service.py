"""Unit tests for EAV attribute validation service."""
import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.services.attribute_service import (
    resolve_value_from_dav,
    validate_attribute_value,
)


def _make_attr(data_type: str, allowed_values=None, name: str = "TestAttr"):
    attr = MagicMock()
    attr.name = name
    attr.data_type = data_type
    attr.allowed_values = allowed_values
    return attr


class TestValidateStringValue:
    def test_validate_string_value_success(self):
        attr = _make_attr("STRING")
        value, col = validate_attribute_value(attr, "hello world")
        assert value == "hello world"
        assert col == "value_string"

    def test_string_coerces_non_string(self):
        """STRING type should coerce non-string to string."""
        attr = _make_attr("STRING")
        value, col = validate_attribute_value(attr, 42)
        assert value == "42"
        assert col == "value_string"


class TestValidateIntegerValue:
    def test_validate_integer_value_success(self):
        attr = _make_attr("INTEGER")
        value, col = validate_attribute_value(attr, 42)
        assert value == 42
        assert col == "value_integer"

    def test_validate_integer_from_string(self):
        attr = _make_attr("INTEGER")
        value, col = validate_attribute_value(attr, "123")
        assert value == 123

    def test_validate_integer_fail_on_non_numeric_string(self):
        attr = _make_attr("INTEGER", name="count")
        with pytest.raises(HTTPException) as exc_info:
            validate_attribute_value(attr, "forty-two")
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "INVALID_ATTRIBUTE_VALUE"

    def test_validate_integer_rejects_boolean(self):
        """Booleans should not be accepted as integers."""
        attr = _make_attr("INTEGER")
        with pytest.raises(HTTPException) as exc_info:
            validate_attribute_value(attr, True)
        assert exc_info.value.status_code == 422


class TestValidateEnumValue:
    def test_validate_enum_value_in_allowed_values(self):
        attr = _make_attr("ENUM", allowed_values=["QM", "ASIL A", "ASIL B", "ASIL C", "ASIL D"])
        value, col = validate_attribute_value(attr, "ASIL B")
        assert value == "ASIL B"
        assert col == "value_string"

    def test_validate_enum_value_not_in_allowed_values(self):
        attr = _make_attr("ENUM", allowed_values=["QM", "ASIL A", "ASIL B", "ASIL C", "ASIL D"])
        with pytest.raises(HTTPException) as exc_info:
            validate_attribute_value(attr, "ASIL E")
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "INVALID_ATTRIBUTE_VALUE"
        assert "ASIL E" in exc_info.value.detail["detail"]

    def test_validate_enum_case_sensitive(self):
        attr = _make_attr("ENUM", allowed_values=["Option_A", "Option_B"])
        with pytest.raises(HTTPException):
            validate_attribute_value(attr, "option_a")  # lowercase fails


class TestValidateBooleanValue:
    def test_validate_boolean_strict(self):
        """BOOLEAN type only accepts actual booleans, not strings."""
        attr = _make_attr("BOOLEAN")
        value, col = validate_attribute_value(attr, True)
        assert value is True
        assert col == "value_boolean"

    def test_validate_boolean_false(self):
        attr = _make_attr("BOOLEAN")
        value, col = validate_attribute_value(attr, False)
        assert value is False

    def test_validate_boolean_rejects_string_yes(self):
        attr = _make_attr("BOOLEAN")
        with pytest.raises(HTTPException) as exc_info:
            validate_attribute_value(attr, "yes")
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == "INVALID_ATTRIBUTE_VALUE"

    def test_validate_boolean_rejects_string_true(self):
        attr = _make_attr("BOOLEAN")
        with pytest.raises(HTTPException):
            validate_attribute_value(attr, "true")

    def test_validate_boolean_rejects_integer_one(self):
        attr = _make_attr("BOOLEAN")
        with pytest.raises(HTTPException):
            validate_attribute_value(attr, 1)


class TestResolveValueColumn:
    def test_resolve_value_column_string(self):
        dav = MagicMock()
        dav.value_string = "hello"
        dav.value_integer = None
        dav.value_boolean = None
        assert resolve_value_from_dav(dav) == "hello"

    def test_resolve_value_column_integer(self):
        dav = MagicMock()
        dav.value_string = None
        dav.value_integer = 42
        dav.value_boolean = None
        assert resolve_value_from_dav(dav) == 42

    def test_resolve_value_column_boolean(self):
        dav = MagicMock()
        dav.value_string = None
        dav.value_integer = None
        dav.value_boolean = True
        assert resolve_value_from_dav(dav) is True

    def test_resolve_value_all_null(self):
        dav = MagicMock()
        dav.value_string = None
        dav.value_integer = None
        dav.value_boolean = None
        assert resolve_value_from_dav(dav) is None

    def test_resolve_value_boolean_takes_priority_over_integer(self):
        """Boolean is checked first in resolve logic."""
        dav = MagicMock()
        dav.value_boolean = False  # not None (falsy but set)
        dav.value_integer = None
        dav.value_string = None
        result = resolve_value_from_dav(dav)
        assert result is False
