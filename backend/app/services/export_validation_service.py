"""Export validation rules service."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.export_job import ExportArtifactType, ExportIssueSeverity


@dataclass(slots=True)
class ValidationIssue:
    issue_code: str
    severity: ExportIssueSeverity
    message: str
    entity_ref: str | None = None


class ExportValidationService:
    def validate_mapping_completeness(
        self,
        *,
        mapping_profile: str,
        artifact_types: set[ExportArtifactType],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if not mapping_profile.strip():
            issues.append(
                ValidationIssue(
                    issue_code="MAPPING_PROFILE_MISSING",
                    severity=ExportIssueSeverity.ERROR,
                    message="Mapping profile is required.",
                )
            )

        if ExportArtifactType.MANIFEST not in artifact_types:
            issues.append(
                ValidationIssue(
                    issue_code="MANIFEST_MISSING",
                    severity=ExportIssueSeverity.ERROR,
                    message="Manifest artifact is required.",
                )
            )

        if mapping_profile.lower() == "strict":
            if ExportArtifactType.TRACEABILITY not in artifact_types:
                issues.append(
                    ValidationIssue(
                        issue_code="TRACEABILITY_ARTIFACT_MISSING",
                        severity=ExportIssueSeverity.WARNING,
                        message="Traceability artifact is missing for strict mapping profile.",
                    )
                )
            if ExportArtifactType.COMPLIANCE not in artifact_types:
                issues.append(
                    ValidationIssue(
                        issue_code="COMPLIANCE_ARTIFACT_MISSING",
                        severity=ExportIssueSeverity.WARNING,
                        message="Compliance artifact is missing for strict mapping profile.",
                    )
                )

        return issues
