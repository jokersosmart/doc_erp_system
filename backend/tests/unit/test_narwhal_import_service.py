from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.spec_item import DependencyRelationshipType
from app.models.document import LifecycleState
from app.schemas.imports import (
    NarwhalRelationshipStrategy,
    NarwhalTraceLinkMode,
    NarwhalTraceLinkStatus,
)
from app.services.narwhal_import_service import NarwhalImportService


class _FakeScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


class _FakeExecuteResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._values)


def test_scan_workspace_collects_enabled_process_candidates(tmp_path: Path) -> None:
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
                    "advanced_filter": {
                        "source_block_type": "Requirement",
                        "fields": {"verification_method": [False, "Test"], "status": ""},
                    },
                },
                "SWE5": {
                    "folder": "TestSpec/integration_test_spec",
                    "description": "Disabled process",
                    "enabled": False,
                    "pattern_prefix": "SWIT_",
                },
            }
        ),
        encoding="utf-8",
    )

    service = NarwhalImportService()
    response = service.scan_workspace(config_path=str(config_path))

    assert response.workspace_root == str(tmp_path)
    assert response.total_candidates == 1
    assert response.processes[0].process_key == "HWE1"
    assert response.processes[0].metadata_fields == ["status", "verification_method"]
    assert response.candidates[0].document_type == "hardware_requirement"
    assert response.candidates[0].title == "Requirement A"


def test_scan_workspace_can_include_disabled_processes(tmp_path: Path) -> None:
    config_path = tmp_path / "Narwhal_md_path_config.json"
    test_dir = tmp_path / "TestSpec" / "integration_test_spec"
    test_dir.mkdir(parents=True)
    (test_dir / "case.md").write_text("No heading", encoding="utf-8")

    config_path.write_text(
        json.dumps(
            {
                "SWE5": {
                    "folder": "TestSpec/integration_test_spec",
                    "description": "Integration Test Specifications",
                    "enabled": False,
                    "pattern_prefix": "SWIT_",
                }
            }
        ),
        encoding="utf-8",
    )

    service = NarwhalImportService()
    response = service.scan_workspace(
        config_path=str(config_path),
        include_disabled=True,
        process_keys=["SWE5"],
    )

    assert response.total_candidates == 1
    assert response.candidates[0].document_type == "software_integration_test"
    assert response.candidates[0].title == "case"


def test_scan_workspace_raises_for_missing_config() -> None:
    service = NarwhalImportService()

    with pytest.raises(NotFoundError):
        service.scan_workspace(config_path="Z:/missing/Narwhal_md_path_config.json")


def test_scan_workspace_rejects_non_narwhal_file_name(tmp_path: Path) -> None:
    wrong_file = tmp_path / "config.json"
    wrong_file.write_text("{}", encoding="utf-8")

    service = NarwhalImportService()

    with pytest.raises(ValidationError):
        service.scan_workspace(config_path=str(wrong_file))


@pytest.mark.asyncio
async def test_import_document_creates_document_from_markdown_candidate(tmp_path: Path) -> None:
    config_path = tmp_path / "Narwhal_md_path_config.json"
    req_dir = tmp_path / "HWE1_ReqDoc"
    req_dir.mkdir()
    markdown_file = req_dir / "req_a.md"
    markdown_file.write_text("# Imported Requirement\nBody", encoding="utf-8")
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

    created_document = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        bu_node_id=uuid.uuid4(),
        title="Imported Requirement",
        document_type="hardware_requirement",
        content_markdown="# Imported Requirement\nBody",
        lifecycle_state=LifecycleState.DRAFT,
        current_version=1,
        updated_at=None,
    )
    lifecycle_service = AsyncMock()
    lifecycle_service.create_document.return_value = created_document

    service = NarwhalImportService()
    session = AsyncMock()
    session.add = MagicMock()
    response = await service.import_document(
        session=session,
        config_path=str(config_path),
        process_key="HWE1",
        relative_path="HWE1_ReqDoc/req_a.md",
        project_id=created_document.project_id,
        owner_id=created_document.owner_id,
        partition_id=created_document.bu_node_id,
        standards_scope=["ISO26262-8"],
        lifecycle_service=lifecycle_service,
    )

    lifecycle_service.create_document.assert_awaited_once()
    assert response.process_key == "HWE1"
    assert response.relative_path == "HWE1_ReqDoc/req_a.md"
    assert response.document.document_type == "hardware_requirement"
    assert response.document.title == "Imported Requirement"
    assert response.source_item_identifier.startswith("HWE1_")
    assert response.trace_links == []


@pytest.mark.asyncio
async def test_import_document_rejects_file_outside_process_folder(tmp_path: Path) -> None:
    config_path = tmp_path / "Narwhal_md_path_config.json"
    req_dir = tmp_path / "HWE1_ReqDoc"
    req_dir.mkdir()
    outside_dir = tmp_path / "Other"
    outside_dir.mkdir()
    (outside_dir / "req_a.md").write_text("# Outside", encoding="utf-8")
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

    service = NarwhalImportService()

    with pytest.raises(ValidationError):
        await service.import_document(
            session=AsyncMock(),
            config_path=str(config_path),
            process_key="HWE1",
            relative_path="Other/req_a.md",
            project_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            partition_id=uuid.uuid4(),
            standards_scope=[],
            lifecycle_service=AsyncMock(),
        )


@pytest.mark.asyncio
async def test_import_documents_batches_selected_candidates(tmp_path: Path) -> None:
    config_path = tmp_path / "Narwhal_md_path_config.json"
    req_dir = tmp_path / "HWE1_ReqDoc"
    req_dir.mkdir()
    (req_dir / "req_a.md").write_text("# Requirement A\nBody", encoding="utf-8")
    (req_dir / "req_b.md").write_text("# Requirement B\nBody", encoding="utf-8")
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

    created_documents = [
        SimpleNamespace(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            bu_node_id=uuid.uuid4(),
            title="Requirement A",
            document_type="hardware_requirement",
            content_markdown="# Requirement A\nBody",
            lifecycle_state=LifecycleState.DRAFT,
            current_version=1,
            updated_at=None,
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            bu_node_id=uuid.uuid4(),
            title="Requirement B",
            document_type="hardware_requirement",
            content_markdown="# Requirement B\nBody",
            lifecycle_state=LifecycleState.DRAFT,
            current_version=1,
            updated_at=None,
        ),
    ]
    lifecycle_service = AsyncMock()
    lifecycle_service.create_document.side_effect = created_documents

    service = NarwhalImportService()
    session = AsyncMock()
    session.add = MagicMock()
    response = await service.import_documents(
        session=session,
        config_path=str(config_path),
        project_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        partition_id=uuid.uuid4(),
        standards_scope=["ISO26262-8"],
        relative_paths=["HWE1_ReqDoc/req_a.md", "HWE1_ReqDoc/req_b.md"],
        include_disabled=False,
        lifecycle_service=lifecycle_service,
    )

    assert lifecycle_service.create_document.await_count == 2
    assert response.imported_count == 2
    assert response.imported[0].relative_path == "HWE1_ReqDoc/req_a.md"
    assert response.imported[1].relative_path == "HWE1_ReqDoc/req_b.md"


@pytest.mark.asyncio
async def test_import_document_trace_mode_suggest_returns_resolved_and_unresolved(tmp_path: Path) -> None:
    config_path = tmp_path / "Narwhal_md_path_config.json"
    req_dir = tmp_path / "HWE1_ReqDoc"
    req_dir.mkdir()
    markdown_file = req_dir / "req_trace.md"
    markdown_file.write_text(
        "# HWR_001\nDepends on SWR_001 and SWR_999.",
        encoding="utf-8",
    )
    config_path.write_text(
        json.dumps(
            {
                "HWE1": {
                    "folder": "HWE1_ReqDoc",
                    "description": "Hardware Requirements",
                    "enabled": True,
                    "pattern_prefix": "HWR_",
                },
                "SWE1": {
                    "folder": "ReqDoc",
                    "description": "Software Requirements",
                    "enabled": True,
                    "pattern_prefix": "SWR_",
                },
            }
        ),
        encoding="utf-8",
    )

    project_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    partition_id = uuid.uuid4()
    created_document = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=project_id,
        owner_id=owner_id,
        bu_node_id=partition_id,
        title="HWR_001",
        document_type="hardware_requirement",
        content_markdown="# HWR_001\nDepends on SWR_001 and SWR_999.",
        lifecycle_state=LifecycleState.DRAFT,
        current_version=1,
        updated_at=None,
    )
    target_item = SimpleNamespace(
        id=uuid.uuid4(),
        item_identifier="SWR_001",
        document_id=uuid.uuid4(),
    )

    lifecycle_service = AsyncMock()
    lifecycle_service.create_document.return_value = created_document
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.return_value = _FakeExecuteResult([target_item])

    service = NarwhalImportService()
    response = await service.import_document(
        session=session,
        config_path=str(config_path),
        process_key="HWE1",
        relative_path="HWE1_ReqDoc/req_trace.md",
        project_id=project_id,
        owner_id=owner_id,
        partition_id=partition_id,
        standards_scope=["ISO26262-8"],
        trace_link_mode=NarwhalTraceLinkMode.SUGGEST,
        relationship_strategy=NarwhalRelationshipStrategy.FIXED,
        relationship_type=DependencyRelationshipType.BLOCKING,
        lifecycle_service=lifecycle_service,
    )

    assert response.source_item_identifier == "HWR_001"
    assert len(response.trace_links) == 2
    assert response.trace_links[0].status == NarwhalTraceLinkStatus.SUGGESTED
    assert response.trace_links[0].target_identifier == "SWR_001"
    assert response.trace_links[1].status == NarwhalTraceLinkStatus.UNRESOLVED
    assert response.trace_links[1].target_identifier == "SWR_999"


@pytest.mark.asyncio
async def test_import_document_trace_mode_auto_create_marks_created(tmp_path: Path) -> None:
    config_path = tmp_path / "Narwhal_md_path_config.json"
    req_dir = tmp_path / "HWE1_ReqDoc"
    req_dir.mkdir()
    markdown_file = req_dir / "req_trace.md"
    markdown_file.write_text("# HWR_001\nDepends on SWR_001.", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "HWE1": {
                    "folder": "HWE1_ReqDoc",
                    "description": "Hardware Requirements",
                    "enabled": True,
                    "pattern_prefix": "HWR_",
                },
                "SWE1": {
                    "folder": "ReqDoc",
                    "description": "Software Requirements",
                    "enabled": True,
                    "pattern_prefix": "SWR_",
                },
            }
        ),
        encoding="utf-8",
    )

    project_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    partition_id = uuid.uuid4()
    created_document = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=project_id,
        owner_id=owner_id,
        bu_node_id=partition_id,
        title="HWR_001",
        document_type="hardware_requirement",
        content_markdown="# HWR_001\nDepends on SWR_001.",
        lifecycle_state=LifecycleState.DRAFT,
        current_version=1,
        updated_at=None,
    )
    target_item = SimpleNamespace(
        id=uuid.uuid4(),
        item_identifier="SWR_001",
        document_id=uuid.uuid4(),
    )

    lifecycle_service = AsyncMock()
    lifecycle_service.create_document.return_value = created_document
    traceability_service = AsyncMock()
    traceability_service.create_link.return_value = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.return_value = _FakeExecuteResult([target_item])

    service = NarwhalImportService()
    response = await service.import_document(
        session=session,
        config_path=str(config_path),
        process_key="HWE1",
        relative_path="HWE1_ReqDoc/req_trace.md",
        project_id=project_id,
        owner_id=owner_id,
        partition_id=partition_id,
        standards_scope=["ISO26262-8"],
        trace_link_mode=NarwhalTraceLinkMode.AUTO_CREATE,
        relationship_strategy=NarwhalRelationshipStrategy.FIXED,
        relationship_type=DependencyRelationshipType.BLOCKING,
        lifecycle_service=lifecycle_service,
        traceability_service=traceability_service,
    )

    assert len(response.trace_links) == 1
    assert response.trace_links[0].status == NarwhalTraceLinkStatus.CREATED


@pytest.mark.asyncio
async def test_import_document_trace_mode_auto_create_marks_conflict(tmp_path: Path) -> None:
    config_path = tmp_path / "Narwhal_md_path_config.json"
    req_dir = tmp_path / "HWE1_ReqDoc"
    req_dir.mkdir()
    markdown_file = req_dir / "req_trace.md"
    markdown_file.write_text("# HWR_001\nDepends on SWR_001.", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "HWE1": {
                    "folder": "HWE1_ReqDoc",
                    "description": "Hardware Requirements",
                    "enabled": True,
                    "pattern_prefix": "HWR_",
                },
                "SWE1": {
                    "folder": "ReqDoc",
                    "description": "Software Requirements",
                    "enabled": True,
                    "pattern_prefix": "SWR_",
                },
            }
        ),
        encoding="utf-8",
    )

    project_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    partition_id = uuid.uuid4()
    created_document = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=project_id,
        owner_id=owner_id,
        bu_node_id=partition_id,
        title="HWR_001",
        document_type="hardware_requirement",
        content_markdown="# HWR_001\nDepends on SWR_001.",
        lifecycle_state=LifecycleState.DRAFT,
        current_version=1,
        updated_at=None,
    )
    target_item = SimpleNamespace(
        id=uuid.uuid4(),
        item_identifier="SWR_001",
        document_id=uuid.uuid4(),
    )

    lifecycle_service = AsyncMock()
    lifecycle_service.create_document.return_value = created_document
    traceability_service = AsyncMock()
    traceability_service.create_link.side_effect = ConflictError("conflict")
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.return_value = _FakeExecuteResult([target_item])

    service = NarwhalImportService()
    response = await service.import_document(
        session=session,
        config_path=str(config_path),
        process_key="HWE1",
        relative_path="HWE1_ReqDoc/req_trace.md",
        project_id=project_id,
        owner_id=owner_id,
        partition_id=partition_id,
        standards_scope=["ISO26262-8"],
        trace_link_mode=NarwhalTraceLinkMode.AUTO_CREATE,
        relationship_strategy=NarwhalRelationshipStrategy.FIXED,
        relationship_type=DependencyRelationshipType.BLOCKING,
        lifecycle_service=lifecycle_service,
        traceability_service=traceability_service,
    )

    assert len(response.trace_links) == 1
    assert response.trace_links[0].status == NarwhalTraceLinkStatus.SKIPPED_CONFLICT


@pytest.mark.asyncio
async def test_import_document_trace_mode_suggest_uses_process_default_relationship(tmp_path: Path) -> None:
    config_path = tmp_path / "Narwhal_md_path_config.json"
    req_dir = tmp_path / "HWE1_ReqDoc"
    req_dir.mkdir()
    markdown_file = req_dir / "req_trace.md"
    markdown_file.write_text("# HWR_001\nDepends on SWA_001.", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "HWE1": {
                    "folder": "HWE1_ReqDoc",
                    "description": "Hardware Requirements",
                    "enabled": True,
                    "pattern_prefix": "HWR_",
                },
                "SWE2": {
                    "folder": "ReqDoc",
                    "description": "Software Architecture",
                    "enabled": True,
                    "pattern_prefix": "SWA_",
                },
            }
        ),
        encoding="utf-8",
    )

    project_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    partition_id = uuid.uuid4()
    created_document = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=project_id,
        owner_id=owner_id,
        bu_node_id=partition_id,
        title="HWR_001",
        document_type="hardware_requirement",
        content_markdown="# HWR_001\nDepends on SWR_001.",
        lifecycle_state=LifecycleState.DRAFT,
        current_version=1,
        updated_at=None,
    )
    target_item = SimpleNamespace(
        id=uuid.uuid4(),
        item_identifier="SWA_001",
        document_id=uuid.uuid4(),
    )

    lifecycle_service = AsyncMock()
    lifecycle_service.create_document.return_value = created_document
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.return_value = _FakeExecuteResult([target_item])

    service = NarwhalImportService()
    response = await service.import_document(
        session=session,
        config_path=str(config_path),
        process_key="HWE1",
        relative_path="HWE1_ReqDoc/req_trace.md",
        project_id=project_id,
        owner_id=owner_id,
        partition_id=partition_id,
        standards_scope=["ISO26262-8"],
        trace_link_mode=NarwhalTraceLinkMode.SUGGEST,
        relationship_strategy=NarwhalRelationshipStrategy.PROCESS_DEFAULT,
        relationship_type=DependencyRelationshipType.RELATED,
        lifecycle_service=lifecycle_service,
    )

    assert len(response.trace_links) == 1
    assert response.trace_links[0].relationship_type == DependencyRelationshipType.BLOCKING
