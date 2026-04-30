"""Integration tests for Project and Partition endpoints."""
import pytest

pytestmark = pytest.mark.asyncio


class TestCreateProject:
    async def test_create_project_as_admin(self, async_client, admin_token):
        resp = await async_client.post(
            "/api/v1/projects",
            json={"name": "My Test Project", "description": "Test description"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Test Project"
        assert "id" in data

    async def test_create_project_as_non_admin_returns_403(self, async_client, rd_token):
        resp = await async_client.post(
            "/api/v1/projects",
            json={"name": "Unauthorized Project"},
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    async def test_create_project_as_qa_returns_403(self, async_client, qa_token):
        resp = await async_client.post(
            "/api/v1/projects",
            json={"name": "QA Project"},
            headers={"Authorization": f"Bearer {qa_token}"},
        )
        assert resp.status_code == 403

    async def test_list_projects(self, async_client, admin_token, sample_project):
        resp = await async_client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_get_project_by_id(self, async_client, admin_token, sample_project):
        resp = await async_client.get(
            f"/api/v1/projects/{sample_project.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(sample_project.id)
        assert data["name"] == sample_project.name

    async def test_get_nonexistent_project_returns_404(self, async_client, admin_token):
        import uuid
        resp = await async_client.get(
            f"/api/v1/projects/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    async def test_delete_project_with_documents_returns_409(
        self, async_client, admin_token, sample_project, sample_document
    ):
        """Cannot delete a project that has documents."""
        resp = await async_client.delete(
            f"/api/v1/projects/{sample_project.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "PROJECT_HAS_DOCUMENTS"


class TestCreatePartition:
    async def test_create_partition_as_admin(
        self, async_client, admin_token, sample_project
    ):
        resp = await async_client.post(
            "/api/v1/partitions",
            json={
                "project_id": str(sample_project.id),
                "name": "Safety",
                "description": "Safety partition",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Safety"
        assert data["project_id"] == str(sample_project.id)

    async def test_create_partition_as_non_admin_returns_403(
        self, async_client, rd_token, sample_project
    ):
        resp = await async_client.post(
            "/api/v1/partitions",
            json={
                "project_id": str(sample_project.id),
                "name": "Security",
            },
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        assert resp.status_code == 403

    async def test_list_partitions(
        self, async_client, admin_token, sample_project, sample_partition
    ):
        resp = await async_client.get(
            f"/api/v1/partitions?project_id={sample_project.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_create_partition_invalid_project_returns_404(
        self, async_client, admin_token
    ):
        import uuid
        resp = await async_client.post(
            "/api/v1/partitions",
            json={"project_id": str(uuid.uuid4()), "name": "SYS"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
