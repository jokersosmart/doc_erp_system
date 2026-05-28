from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.models.document import Document, LifecycleState
from app.schemas.documents import DocumentResponse
from app.schemas.imports import NarwhalImportDocumentResponse


def test_imports_contract_path_and_method_present() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert "/api/v1/imports/narwhal/scan" in paths
    assert "post" in paths["/api/v1/imports/narwhal/scan"]
    assert "/api/v1/imports/narwhal/documents" in paths
    assert "post" in paths["/api/v1/imports/narwhal/documents"]
    assert "/api/v1/imports/narwhal/documents/batch" in paths
    assert "post" in paths["/api/v1/imports/narwhal/documents/batch"]


def test_imports_contract_request_and_error_responses_declared() -> None:
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/imports/narwhal/scan"]["post"]
    import_operation = schema["paths"]["/api/v1/imports/narwhal/documents"]["post"]
    batch_operation = schema["paths"]["/api/v1/imports/narwhal/documents/batch"]["post"]

    assert "requestBody" in operation
    assert "422" in operation["responses"]
    assert "404" in operation["responses"]
    assert "requestBody" in import_operation
    assert "201" in import_operation["responses"]
    assert "422" in import_operation["responses"]
    assert "404" in import_operation["responses"]
    assert "requestBody" in batch_operation
    assert "201" in batch_operation["responses"]
    assert "422" in batch_operation["responses"]
    assert "404" in batch_operation["responses"]


def test_imports_scan_endpoint_returns_candidates_from_narwhal_workspace(tmp_path: Path) -> None:
    config_path = tmp_path / "Narwhal_md_path_config.json"
    req_dir = tmp_path / "HWE1_ReqDoc"
    req_dir.mkdir()
    (req_dir / "req_a.md").write_text("# Requirement A\nBody", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "HWE1": {
                    "folder": "HWE1_ReqDoc",
                    "description": "Hardware Requirements",
                    "enabled": True,
                    "pattern_prefix": "HWR_",
                }
            }
        ),
        encoding="utf-8",
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/imports/narwhal/scan",
        json={"config_path": str(config_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_candidates"] == 1
    assert payload["candidates"][0]["process_key"] == "HWE1"
    assert payload["candidates"][0]["title"] == "Requirement A"


def test_imports_document_endpoint_returns_imported_document_payload(monkeypatch) -> None:
    async def override_db():
        yield AsyncMock()

    async def fake_import_document(self, **kwargs):
        document = Document(
            id=uuid.uuid4(),
            project_id=kwargs["project_id"],
            owner_id=kwargs["owner_id"],
            bu_node_id=kwargs["partition_id"],
            title="Imported Requirement",
            document_type="hardware_requirement",
            content_markdown="# Imported Requirement",
            lifecycle_state=LifecycleState.DRAFT,
            current_version=1,
        )
        return NarwhalImportDocumentResponse(
            process_key=kwargs["process_key"],
            source_path="D:/AiWorkSpace/HWE1_ReqDoc/req_a.md",
            relative_path=kwargs["relative_path"],
            document=DocumentResponse.from_document(document=document),
            source_item_id=uuid.uuid4(),
            source_item_identifier="HWR_001",
            trace_links=[],
        )

    from app.api.routes import imports as imports_route_module

    monkeypatch.setattr(imports_route_module.NarwhalImportService, "import_document", fake_import_document)
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    response = client.post(
        "/api/v1/imports/narwhal/documents",
        json={
            "config_path": "D:/AiWorkSpace/Narwhal_md_path_config.json",
            "process_key": "HWE1",
            "relative_path": "HWE1_ReqDoc/req_a.md",
            "project_id": str(uuid.uuid4()),
            "owner_id": str(uuid.uuid4()),
            "partition_id": str(uuid.uuid4()),
            "standards_scope": ["ISO26262-8"],
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["process_key"] == "HWE1"
    assert payload["document"]["document_type"] == "hardware_requirement"
    assert payload["document"]["title"] == "Imported Requirement"
    assert payload["source_item_identifier"] == "HWR_001"


def test_imports_batch_document_endpoint_returns_import_summary(monkeypatch) -> None:
    async def override_db():
        yield AsyncMock()

    async def fake_import_documents(self, **kwargs):
        document = Document(
            id=uuid.uuid4(),
            project_id=kwargs["project_id"],
            owner_id=kwargs["owner_id"],
            bu_node_id=kwargs["partition_id"],
            title="Imported Requirement",
            document_type="hardware_requirement",
            content_markdown="# Imported Requirement",
            lifecycle_state=LifecycleState.DRAFT,
            current_version=1,
        )
        return {
            "workspace_root": "D:/AiWorkSpace",
            "imported": [
                {
                    "process_key": "HWE1",
                    "source_path": "D:/AiWorkSpace/HWE1_ReqDoc/req_a.md",
                    "relative_path": "HWE1_ReqDoc/req_a.md",
                    "document": DocumentResponse.from_document(document=document),
                    "source_item_id": uuid.uuid4(),
                    "source_item_identifier": "HWR_001",
                    "trace_links": [],
                }
            ],
            "imported_count": 1,
        }

    from app.api.routes import imports as imports_route_module

    monkeypatch.setattr(imports_route_module.NarwhalImportService, "import_documents", fake_import_documents)
    app.dependency_overrides[get_db] = override_db

    client = TestClient(app)
    response = client.post(
        "/api/v1/imports/narwhal/documents/batch",
        json={
            "config_path": "D:/AiWorkSpace/Narwhal_md_path_config.json",
            "project_id": str(uuid.uuid4()),
            "owner_id": str(uuid.uuid4()),
            "partition_id": str(uuid.uuid4()),
            "standards_scope": ["ISO26262-8"],
            "process_keys": ["HWE1"],
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["workspace_root"] == "D:/AiWorkSpace"
    assert payload["imported_count"] == 1
    assert payload["imported"][0]["document"]["title"] == "Imported Requirement"
