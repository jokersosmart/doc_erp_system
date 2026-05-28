from __future__ import annotations

from app.models.export_job import ExportArtifactType
from app.services.export_validation_service import ExportValidationService


def test_validate_mapping_requires_profile() -> None:
    service = ExportValidationService()

    issues = service.validate_mapping_completeness(
        mapping_profile="",
        artifact_types={ExportArtifactType.MANIFEST},
    )

    assert any(issue.issue_code == "MAPPING_PROFILE_MISSING" for issue in issues)


def test_validate_mapping_requires_manifest_artifact() -> None:
    service = ExportValidationService()

    issues = service.validate_mapping_completeness(
        mapping_profile="default",
        artifact_types={ExportArtifactType.DOCUMENT_BUNDLE},
    )

    assert any(issue.issue_code == "MANIFEST_MISSING" for issue in issues)


def test_strict_profile_warns_for_missing_traceability_and_compliance() -> None:
    service = ExportValidationService()

    issues = service.validate_mapping_completeness(
        mapping_profile="strict",
        artifact_types={ExportArtifactType.MANIFEST},
    )

    codes = {issue.issue_code for issue in issues}
    assert "TRACEABILITY_ARTIFACT_MISSING" in codes
    assert "COMPLIANCE_ARTIFACT_MISSING" in codes
