"""Integration tests for Attribute Definition endpoints."""
import uuid

import pytest

pytestmark = pytest.mark.asyncio


class TestCreateAttributeDefinition:
    async def test_create_attribute_definition_as_admin(
        self, async_client, admin_token
    ):
        """US4 AC-4: Admin creates attribute definition - 201."""
        resp = await async_client.post(
            "/api/v1/attribute-definitions",
            json={
                "name": f"My_Attr_{uuid.uuid4().hex[:6]}",
                "data_type": "STRING",
                "is_required": False,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["data_type"] == "STRING"
        assert "id" in data

    async def test_create_enum_attribute_with_allowed_values(
        self, async_client, admin_token
    ):
        resp = await async_client.post(
            "/api/v1/attribute-definitions",
            json={
                "name": f"Risk_Level_{uuid.uuid4().hex[:4]}",
                "data_type": "ENUM",
                "allowed_values": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                "is_required": False,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["allowed_values"] == ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    async def test_create_enum_without_allowed_values_returns_422(
        self, async_client, admin_token
    ):
        """ENUM without allowed_values should fail validation."""
        resp = await async_client.post(
            "/api/v1/attribute-definitions",
            json={
                "name": "Bad_Enum_Attr",
                "data_type": "ENUM",
                # No allowed_values provided
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    async def test_create_attribute_definition_non_admin_returns_403(
        self, async_client, rd_token
    ):
        resp = await async_client.post(
            "/api/v1/attribute-definitions",
            json={"name": "Unauthorized_Attr", "data_type": "STRING"},
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        assert resp.status_code == 403


class TestDocumentWithAttributes:
    async def test_create_document_missing_required_attribute_returns_422(
        self,
        async_client,
        admin_token,
        sample_project,
        sample_partition,
        required_attribute_definition,
    ):
        """US4 AC-2: Missing required attribute -> 422."""
        resp = await async_client.post(
            "/api/v1/documents",
            json={
                "project_id": str(sample_project.id),
                "partition_id": str(sample_partition.id),
                "title": "Missing Required Attr",
                "content_md": "# Content",
                # No attributes provided, but required_attribute_definition is_required=True
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "REQUIRED_ATTRIBUTE_MISSING"

    async def test_create_document_with_invalid_enum_value_returns_422(
        self,
        async_client,
        admin_token,
        sample_project,
        sample_partition,
        required_attribute_definition,
    ):
        """US4 AC-3: Invalid ENUM value -> 422."""
        resp = await async_client.post(
            "/api/v1/documents",
            json={
                "project_id": str(sample_project.id),
                "partition_id": str(sample_partition.id),
                "title": "Invalid Enum Value Doc",
                "content_md": "# Content",
                "attributes": [
                    {
                        "attribute_id": str(required_attribute_definition.id),
                        "value": "Invalid_Option",  # not in allowed_values
                    }
                ],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "INVALID_ATTRIBUTE_VALUE"

    async def test_duplicate_attribute_id_merges(
        self,
        async_client,
        admin_token,
        sample_project,
        sample_partition,
        required_attribute_definition,
    ):
        """Edge case: duplicate attribute_id - last value wins."""
        resp = await async_client.post(
            "/api/v1/documents",
            json={
                "project_id": str(sample_project.id),
                "partition_id": str(sample_partition.id),
                "title": "Duplicate Attr Test",
                "content_md": "# Content",
                "attributes": [
                    {
                        "attribute_id": str(required_attribute_definition.id),
                        "value": "Option_A",  # First (will be overridden)
                    },
                    {
                        "attribute_id": str(required_attribute_definition.id),
                        "value": "Option_B",  # Second (should win)
                    },
                ],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        # Should have only one attribute value
        attrs = data["attributes"]
        assert len(attrs) == 1
        assert attrs[0]["value"] == "Option_B"


class TestListAttributeDefinitions:
    async def test_list_attribute_definitions(
        self, async_client, admin_token, sample_attribute_definition
    ):
        resp = await async_client.get(
            "/api/v1/attribute-definitions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_filter_required_attributes(
        self,
        async_client,
        admin_token,
        required_attribute_definition,
    ):
        resp = await async_client.get(
            "/api/v1/attribute-definitions?is_required=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # All returned items should be required
        for item in data["items"]:
            assert item["is_required"] is True
