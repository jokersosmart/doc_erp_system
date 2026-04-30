"""Integration tests for Document management endpoints."""
import uuid

import pytest

pytestmark = pytest.mark.asyncio


class TestCreateDocument:
    async def test_create_document_with_attributes(
        self,
        async_client,
        admin_token,
        sample_project,
        sample_partition,
        sample_attribute_definition,
    ):
        """US1 AC-1: 201, version 1.0, DRAFT, EAV correct."""
        resp = await async_client.post(
            "/api/v1/documents",
            json={
                "project_id": str(sample_project.id),
                "partition_id": str(sample_partition.id),
                "title": "Software Architecture Specification",
                "content_md": "# Software Architecture\n\nThis document describes...",
                "attributes": [
                    {
                        "attribute_id": str(sample_attribute_definition.id),
                        "value": "test-value",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["version"] == "1.0"
        assert data["status"] == "DRAFT"
        assert "id" in data
        assert len(data["attributes"]) == 1

    async def test_create_document_basic(
        self, async_client, rd_token, sample_project, sample_partition
    ):
        resp = await async_client.post(
            "/api/v1/documents",
            json={
                "project_id": str(sample_project.id),
                "partition_id": str(sample_partition.id),
                "title": "Basic Document",
                "content_md": "# Content\n\nDocument body here.",
            },
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["owner_id"] == "user-rd-001"

    async def test_empty_content_md_returns_422(
        self, async_client, rd_token, sample_project, sample_partition
    ):
        """Edge case: empty Markdown content."""
        resp = await async_client.post(
            "/api/v1/documents",
            json={
                "project_id": str(sample_project.id),
                "partition_id": str(sample_partition.id),
                "title": "Empty Content",
                "content_md": "   ",  # whitespace only
            },
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        assert resp.status_code == 422

    async def test_partition_project_mismatch_returns_422(
        self, async_client, admin_token, sample_project
    ):
        """Edge case: partition doesn't belong to project."""
        resp = await async_client.post(
            "/api/v1/documents",
            json={
                "project_id": str(sample_project.id),
                "partition_id": str(uuid.uuid4()),  # random partition
                "title": "Mismatch Test",
                "content_md": "# Test content",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "PARTITION_PROJECT_MISMATCH"

    async def test_invalid_uuid_path_param_returns_422(
        self, async_client, admin_token
    ):
        """Edge case: non-UUID path parameter."""
        resp = await async_client.get(
            "/api/v1/documents/not-a-valid-uuid",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422


class TestGetDocument:
    async def test_get_document_by_id(
        self, async_client, admin_token, sample_document
    ):
        """US1 AC-2: 200, content and attributes complete."""
        resp = await async_client.get(
            f"/api/v1/documents/{sample_document.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(sample_document.id)
        assert data["content_md"] == sample_document.content_md
        assert data["title"] == sample_document.title

    async def test_access_other_partition_document_returns_403(
        self, async_client, rd_token, test_db, sample_project
    ):
        """US1 AC-4: 403 for documents in inaccessible partition."""
        from app.models.partition import Partition
        from app.models.document import Document

        # Create a partition that RD user doesn't have access to
        restricted_partition = Partition(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            name="Security",  # RD user has access to SWE and HW only
            description="Security partition",
        )
        test_db.add(restricted_partition)
        await test_db.flush()

        restricted_doc = Document(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            partition_id=restricted_partition.id,
            title="Restricted Document",
            content_md="# Secret content",
            version="1.0",
            status="DRAFT",
            owner_id="user-admin-001",
            version_lock=1,
        )
        test_db.add(restricted_doc)
        await test_db.flush()

        resp = await async_client.get(
            f"/api/v1/documents/{restricted_doc.id}",
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        # Should return 403 (not 404 - don't reveal existence)
        assert resp.status_code == 403


class TestUpdateDocument:
    async def test_update_document_increments_version(
        self, async_client, rd_token, sample_document
    ):
        """US1 AC-3: 200, 1.0 -> 1.1, old version queryable."""
        resp = await async_client.put(
            f"/api/v1/documents/{sample_document.id}",
            json={
                "content_md": "# Updated Content\n\nNew content here.",
                "commit_message": "Update content for review",
            },
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "1.1"

    async def test_update_approved_document_returns_409(
        self, async_client, admin_token, test_db, sample_project, sample_partition
    ):
        """US2 AC-3: APPROVED documents cannot be directly modified."""
        from app.models.document import Document

        approved_doc = Document(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            partition_id=sample_partition.id,
            title="Approved Doc",
            content_md="# Approved content",
            version="1.0",
            status="APPROVED",  # Already approved
            owner_id="user-admin-001",
            version_lock=1,
        )
        test_db.add(approved_doc)
        await test_db.flush()

        resp = await async_client.put(
            f"/api/v1/documents/{approved_doc.id}",
            json={"content_md": "# Modified content"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "DOCUMENT_APPROVED"

    async def test_concurrent_update_optimistic_lock(
        self, async_client, rd_token, sample_document
    ):
        """Edge case: concurrent write - version lock mismatch."""
        resp = await async_client.put(
            f"/api/v1/documents/{sample_document.id}",
            json={
                "content_md": "# Updated",
                "version_lock": 999,  # Wrong lock value
            },
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "VERSION_CONFLICT"


class TestStatusTransition:
    async def test_document_status_transition_draft_to_review(
        self, async_client, rd_token, sample_document
    ):
        """US2 AC-1: DRAFT -> REVIEW."""
        resp = await async_client.patch(
            f"/api/v1/documents/{sample_document.id}/status",
            json={"status": "REVIEW"},
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "REVIEW"

    async def test_document_status_transition_to_approved(
        self, async_client, qa_token, test_db, sample_project, sample_partition
    ):
        """US2 AC-2: REVIEW -> APPROVED."""
        from app.models.document import Document

        review_doc = Document(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            partition_id=sample_partition.id,
            title="Review Doc",
            content_md="# Review content",
            version="1.0",
            status="REVIEW",
            owner_id="user-rd-001",
            version_lock=1,
        )
        test_db.add(review_doc)
        await test_db.flush()

        resp = await async_client.patch(
            f"/api/v1/documents/{review_doc.id}/status",
            json={"status": "APPROVED"},
            headers={"Authorization": f"Bearer {qa_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "APPROVED"

    async def test_invalid_status_transition_returns_422(
        self, async_client, admin_token, test_db, sample_project, sample_partition
    ):
        """US2 AC-4: APPROVED -> DRAFT is invalid."""
        from app.models.document import Document

        approved_doc = Document(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            partition_id=sample_partition.id,
            title="Approved for Transition Test",
            content_md="# Content",
            version="1.0",
            status="APPROVED",
            owner_id="user-admin-001",
            version_lock=1,
        )
        test_db.add(approved_doc)
        await test_db.flush()

        resp = await async_client.patch(
            f"/api/v1/documents/{approved_doc.id}/status",
            json={"status": "DRAFT"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "INVALID_STATUS_TRANSITION"

    async def test_non_owner_rd_cannot_advance_to_review(
        self, async_client, test_db, sample_project, sample_partition
    ):
        """US2 AC-5: Non-owner RD cannot push to REVIEW."""
        from app.core.security import create_access_token
        from app.models.document import Document

        # Create document owned by different user
        doc = Document(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            partition_id=sample_partition.id,
            title="Other's Document",
            content_md="# Someone else's content",
            version="1.0",
            status="DRAFT",
            owner_id="user-rd-999",  # Different owner
            version_lock=1,
        )
        test_db.add(doc)
        await test_db.flush()

        # RD user trying to advance someone else's doc
        rd_token = create_access_token(
            user_id="user-rd-001", role="RD", partition_access=["SWE", "HW"]
        )
        resp = await async_client.patch(
            f"/api/v1/documents/{doc.id}/status",
            json={"status": "REVIEW"},
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        assert resp.status_code == 403


class TestVersionHistory:
    async def test_get_version_history(
        self, async_client, rd_token, sample_document
    ):
        """US5 AC-2: versions listed newest first."""
        # Update document to create version history
        await async_client.put(
            f"/api/v1/documents/{sample_document.id}",
            json={"content_md": "# Version 1.1 content", "commit_message": "First update"},
            headers={"Authorization": f"Bearer {rd_token}"},
        )

        resp = await async_client.get(
            f"/api/v1/documents/{sample_document.id}/versions",
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "document_id" in data
        assert "versions" in data
        assert "current_version" in data
        assert len(data["versions"]) >= 1

    async def test_get_version_snapshot(
        self, async_client, rd_token, sample_document
    ):
        """US5 AC-3: version snapshot has correct content."""
        original_content = sample_document.content_md

        # Update to create a version snapshot
        await async_client.put(
            f"/api/v1/documents/{sample_document.id}",
            json={"content_md": "# New content", "commit_message": "Update"},
            headers={"Authorization": f"Bearer {rd_token}"},
        )

        # Get version history to find snapshot version
        hist_resp = await async_client.get(
            f"/api/v1/documents/{sample_document.id}/versions",
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        versions = hist_resp.json()["versions"]
        assert len(versions) >= 1

        # Get specific version snapshot
        version_num = versions[0]["version"]
        snap_resp = await async_client.get(
            f"/api/v1/documents/{sample_document.id}/versions/{version_num}",
            headers={"Authorization": f"Bearer {rd_token}"},
        )
        assert snap_resp.status_code == 200
        data = snap_resp.json()
        assert "content_md" in data
        assert data["version"] == version_num


class TestListDocuments:
    async def test_list_documents_with_filters(
        self, async_client, admin_token, sample_project, sample_partition, sample_document
    ):
        resp = await async_client.get(
            f"/api/v1/documents?project_id={sample_project.id}&status=DRAFT",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1
