"""Contract tests: Verify OpenAPI schema completeness."""
import pytest

pytestmark = pytest.mark.asyncio

EXPECTED_PATHS = [
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/projects",
    "/api/v1/partitions",
    "/api/v1/documents",
    "/api/v1/documents/{doc_id}",
    "/api/v1/documents/{doc_id}/status",
    "/api/v1/documents/{doc_id}/versions",
    "/api/v1/documents/{doc_id}/versions/{version}",
    "/api/v1/attribute-definitions",
    "/health",
]


class TestOpenAPISchema:
    async def test_openapi_json_accessible(self, async_client):
        """OpenAPI JSON endpoint should return 200."""
        resp = await async_client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "openapi" in data
        assert "paths" in data

    async def test_all_expected_paths_exist(self, async_client):
        """All core API paths must be defined in the OpenAPI schema."""
        resp = await async_client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        defined_paths = list(schema.get("paths", {}).keys())

        for expected_path in EXPECTED_PATHS:
            assert any(
                expected_path == path or expected_path in path
                for path in defined_paths
            ), f"Expected path '{expected_path}' not found in OpenAPI schema. Defined paths: {defined_paths}"

    async def test_docs_endpoint_accessible(self, async_client):
        """Swagger UI should be accessible."""
        resp = await async_client.get("/docs")
        assert resp.status_code == 200

    async def test_redoc_endpoint_accessible(self, async_client):
        """ReDoc UI should be accessible."""
        resp = await async_client.get("/redoc")
        assert resp.status_code == 200

    async def test_required_security_scheme_defined(self, async_client):
        """OpenAPI schema should define Bearer token security."""
        resp = await async_client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()

        components = schema.get("components", {})
        security_schemes = components.get("securitySchemes", {})

        # FastAPI generates HTTPBearer as a securityScheme
        assert len(security_schemes) > 0, "No security schemes defined in OpenAPI schema"

    async def test_openapi_version_is_3(self, async_client):
        """API should use OpenAPI 3.x."""
        resp = await async_client.get("/openapi.json")
        data = resp.json()
        assert data["openapi"].startswith("3.")

    async def test_api_info_fields(self, async_client):
        """API info section should have required fields."""
        resp = await async_client.get("/openapi.json")
        data = resp.json()
        info = data.get("info", {})
        assert "title" in info
        assert "version" in info
