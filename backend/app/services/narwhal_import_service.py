"""Narwhal/AiWorkSpace config loading and markdown import scanning."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.document import Document
from app.models.spec_item import DependencyRelationshipType, SpecItem
from app.schemas.documents import DocumentResponse
from app.schemas.imports import (
    NarwhalBatchImportResponse,
    NarwhalImportDocumentResponse,
    NarwhalImportCandidate,
    NarwhalProcessSummary,
    NarwhalRelationshipStrategy,
    NarwhalScanResponse,
    NarwhalTraceLinkMode,
    NarwhalTraceLinkResult,
    NarwhalTraceLinkStatus,
)
from app.services.document_lifecycle_service import DocumentLifecycleService
from app.services.traceability_service import TraceabilityService


class NarwhalImportService:
    def scan_workspace(
        self,
        *,
        config_path: str,
        process_keys: list[str] | None = None,
        include_disabled: bool = False,
    ) -> NarwhalScanResponse:
        workspace_root, config_data = self._load_config(config_path=config_path)
        process_filter = set(process_keys or [])

        process_summaries: list[NarwhalProcessSummary] = []
        candidates: list[NarwhalImportCandidate] = []

        for process_key, process_config in config_data.items():
            if not isinstance(process_config, dict):
                continue
            folder = process_config.get("folder")
            pattern_prefix = process_config.get("pattern_prefix")
            if not folder or not pattern_prefix:
                continue
            if process_filter and process_key not in process_filter:
                continue

            enabled = bool(process_config.get("enabled", False))
            if not enabled and not include_disabled:
                continue

            advanced_filter = process_config.get("advanced_filter", {})
            fields = advanced_filter.get("fields", {}) if isinstance(advanced_filter, dict) else {}

            summary = NarwhalProcessSummary(
                process_key=process_key,
                folder=folder,
                description=str(process_config.get("description", "")),
                enabled=enabled,
                pattern_prefix=str(pattern_prefix),
                source_block_type=advanced_filter.get("source_block_type") if isinstance(advanced_filter, dict) else None,
                metadata_fields=sorted(fields.keys()),
            )
            process_summaries.append(summary)

            folder_path = workspace_root / folder
            if not folder_path.exists():
                continue

            for markdown_file in sorted(folder_path.rglob("*.md")):
                candidates.append(
                    NarwhalImportCandidate(
                        process_key=process_key,
                        document_type=self._infer_document_type(process_key=process_key),
                        source_path=str(markdown_file),
                        relative_path=str(markdown_file.relative_to(workspace_root)).replace("\\", "/"),
                        file_name=markdown_file.name,
                        title=self._infer_title(markdown_file=markdown_file),
                        pattern_prefix=str(pattern_prefix),
                    )
                )

        return NarwhalScanResponse(
            workspace_root=str(workspace_root),
            processes=process_summaries,
            candidates=candidates,
            total_candidates=len(candidates),
        )

    async def import_document(
        self,
        *,
        session: AsyncSession,
        config_path: str,
        process_key: str,
        relative_path: str,
        project_id,
        owner_id,
        partition_id,
        standards_scope: list[str],
        trace_link_mode: NarwhalTraceLinkMode = NarwhalTraceLinkMode.NONE,
        relationship_strategy: NarwhalRelationshipStrategy = NarwhalRelationshipStrategy.FIXED,
        relationship_type: DependencyRelationshipType = DependencyRelationshipType.BLOCKING,
        lifecycle_service: DocumentLifecycleService | None = None,
        traceability_service: TraceabilityService | None = None,
    ) -> NarwhalImportDocumentResponse:
        workspace_root, config_data = self._load_config(config_path=config_path)
        process_config = self._get_process_config(config_data=config_data, process_key=process_key)
        markdown_file = self._resolve_markdown_file(
            workspace_root=workspace_root,
            process_config=process_config,
            relative_path=relative_path,
        )
        content_markdown = markdown_file.read_text(encoding="utf-8")

        service = lifecycle_service or DocumentLifecycleService(session=session)
        document = await service.create_document(
            project_id=project_id,
            owner_id=owner_id,
            partition_id=partition_id,
            title=self._infer_title(markdown_file=markdown_file),
            document_type=self._infer_document_type(process_key=process_key),
            content_markdown=content_markdown,
            standards_scope=standards_scope,
        )
        source_identifier = self._derive_source_identifier(
            process_key=process_key,
            pattern_prefix=str(process_config.get("pattern_prefix", "")),
            content_markdown=content_markdown,
            fallback_token=str(document.id).replace("-", "")[:8],
        )
        source_item = await self._create_primary_spec_item(
            session=session,
            document=document,
            item_identifier=source_identifier,
        )
        trace_links = await self._build_trace_links(
            session=session,
            project_id=project_id,
            source_item=source_item,
            source_document=document,
            content_markdown=content_markdown,
            config_data=config_data,
            source_process_key=process_key,
            trace_link_mode=trace_link_mode,
            relationship_strategy=relationship_strategy,
            relationship_type=relationship_type,
            traceability_service=traceability_service,
        )

        return NarwhalImportDocumentResponse(
            process_key=process_key,
            source_path=str(markdown_file),
            relative_path=str(markdown_file.relative_to(workspace_root)).replace("\\", "/"),
            document=DocumentResponse.from_document(document=document),
            source_item_id=source_item.id,
            source_item_identifier=source_item.item_identifier,
            trace_links=trace_links,
        )

    async def import_documents(
        self,
        *,
        session: AsyncSession,
        config_path: str,
        project_id,
        owner_id,
        partition_id,
        standards_scope: list[str],
        process_keys: list[str] | None = None,
        relative_paths: list[str] | None = None,
        include_disabled: bool = False,
        trace_link_mode: NarwhalTraceLinkMode = NarwhalTraceLinkMode.NONE,
        relationship_strategy: NarwhalRelationshipStrategy = NarwhalRelationshipStrategy.FIXED,
        relationship_type: DependencyRelationshipType = DependencyRelationshipType.BLOCKING,
        lifecycle_service: DocumentLifecycleService | None = None,
        traceability_service: TraceabilityService | None = None,
    ) -> NarwhalBatchImportResponse:
        scan_response = self.scan_workspace(
            config_path=config_path,
            process_keys=process_keys,
            include_disabled=include_disabled,
        )
        selected_paths = set(relative_paths or [])
        imported: list[NarwhalImportDocumentResponse] = []

        for candidate in scan_response.candidates:
            if selected_paths and candidate.relative_path not in selected_paths:
                continue
            imported.append(
                await self.import_document(
                    session=session,
                    config_path=config_path,
                    process_key=candidate.process_key,
                    relative_path=candidate.relative_path,
                    project_id=project_id,
                    owner_id=owner_id,
                    partition_id=partition_id,
                    standards_scope=standards_scope,
                    trace_link_mode=trace_link_mode,
                    relationship_strategy=relationship_strategy,
                    relationship_type=relationship_type,
                    lifecycle_service=lifecycle_service,
                    traceability_service=traceability_service,
                )
            )

        return NarwhalBatchImportResponse(
            workspace_root=scan_response.workspace_root,
            imported=imported,
            imported_count=len(imported),
        )

    def _load_config(self, *, config_path: str) -> tuple[Path, dict[str, Any]]:
        config_file = Path(config_path)
        if not config_file.exists():
            raise NotFoundError("Narwhal config file not found")
        if config_file.name != "Narwhal_md_path_config.json":
            raise ValidationError("Expected Narwhal_md_path_config.json")

        try:
            config_data = json.loads(config_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid Narwhal config JSON: {exc.msg}") from exc

        if not isinstance(config_data, dict):
            raise ValidationError("Narwhal config root must be an object")

        return config_file.parent, config_data

    def _get_process_config(self, *, config_data: dict[str, Any], process_key: str) -> dict[str, Any]:
        process_config = config_data.get(process_key)
        if not isinstance(process_config, dict):
            raise NotFoundError("Narwhal process configuration not found")
        return process_config

    def _resolve_markdown_file(
        self,
        *,
        workspace_root: Path,
        process_config: dict[str, Any],
        relative_path: str,
    ) -> Path:
        folder = process_config.get("folder")
        if not isinstance(folder, str) or not folder:
            raise ValidationError("Narwhal process folder is not configured")

        process_root = (workspace_root / folder).resolve()
        markdown_file = (workspace_root / relative_path).resolve()

        if markdown_file.suffix.lower() != ".md":
            raise ValidationError("Only markdown files can be imported")
        if not markdown_file.exists():
            raise NotFoundError("Narwhal markdown file not found")
        if process_root != markdown_file and process_root not in markdown_file.parents:
            raise ValidationError("Markdown file is outside the configured process folder")

        return markdown_file

    def _infer_document_type(self, *, process_key: str) -> str:
        mapping = {
            "HWE1": "hardware_requirement",
            "HWE2": "hardware_architecture",
            "SWE1": "software_requirement",
            "SWE2": "software_architecture",
            "SWE3": "software_detail_design",
            "SWE4": "software_unit_test",
            "SWE5": "software_integration_test",
            "SYS2": "system_requirement",
            "SYS3": "system_architecture",
        }
        return mapping.get(process_key, process_key.lower())

    def _infer_title(self, *, markdown_file: Path) -> str:
        try:
            first_line = markdown_file.read_text(encoding="utf-8").splitlines()[0].strip()
        except (UnicodeDecodeError, IndexError):
            return markdown_file.stem

        if first_line.startswith("#"):
            return first_line.lstrip("#").strip() or markdown_file.stem
        return markdown_file.stem

    async def _create_primary_spec_item(
        self,
        *,
        session: AsyncSession,
        document: Document,
        item_identifier: str,
    ) -> SpecItem:
        item = SpecItem(
            id=uuid.uuid4(),
            document_id=document.id,
            item_identifier=item_identifier,
            title=document.title,
            content_markdown=document.content_markdown,
        )
        session.add(item)
        await session.flush()
        return item

    async def _build_trace_links(
        self,
        *,
        session: AsyncSession,
        project_id,
        source_item: SpecItem,
        source_document: Document,
        content_markdown: str,
        config_data: dict[str, Any],
        source_process_key: str,
        trace_link_mode: NarwhalTraceLinkMode,
        relationship_strategy: NarwhalRelationshipStrategy,
        relationship_type: DependencyRelationshipType,
        traceability_service: TraceabilityService | None,
    ) -> list[NarwhalTraceLinkResult]:
        if trace_link_mode == NarwhalTraceLinkMode.NONE:
            return []

        prefixes = self._collect_pattern_prefixes(config_data=config_data)
        identifiers = self._extract_trace_identifiers(content_markdown=content_markdown, prefixes=prefixes)
        target_identifiers = [i for i in identifiers if i != source_item.item_identifier]
        if not target_identifiers:
            return []

        resolved_targets = await self._resolve_target_items(
            session=session,
            project_id=project_id,
            target_identifiers=target_identifiers,
            source_document_id=source_document.id,
        )
        trace_service = traceability_service or TraceabilityService(session=session)
        results: list[NarwhalTraceLinkResult] = []

        for target_identifier in target_identifiers:
            resolved_relationship_type = self._resolve_relationship_type(
                source_process_key=source_process_key,
                target_identifier=target_identifier,
                config_data=config_data,
                relationship_strategy=relationship_strategy,
                fallback_relationship_type=relationship_type,
            )
            target_item = resolved_targets.get(target_identifier)
            if target_item is None:
                results.append(
                    NarwhalTraceLinkResult(
                        source_item_id=source_item.id,
                        source_identifier=source_item.item_identifier,
                        target_identifier=target_identifier,
                        relationship_type=resolved_relationship_type,
                        status=NarwhalTraceLinkStatus.UNRESOLVED,
                        reason="No matching SpecItem identifier found in project",
                    )
                )
                continue

            if trace_link_mode == NarwhalTraceLinkMode.AUTO_CREATE:
                try:
                    await trace_service.create_link(
                        source_item_id=source_item.id,
                        target_item_id=target_item.id,
                        relationship_type=resolved_relationship_type,
                    )
                    results.append(
                        NarwhalTraceLinkResult(
                            source_item_id=source_item.id,
                            source_identifier=source_item.item_identifier,
                            target_identifier=target_identifier,
                            target_item_id=target_item.id,
                            relationship_type=resolved_relationship_type,
                            status=NarwhalTraceLinkStatus.CREATED,
                        )
                    )
                except ConflictError:
                    results.append(
                        NarwhalTraceLinkResult(
                            source_item_id=source_item.id,
                            source_identifier=source_item.item_identifier,
                            target_identifier=target_identifier,
                            target_item_id=target_item.id,
                            relationship_type=resolved_relationship_type,
                            status=NarwhalTraceLinkStatus.SKIPPED_CONFLICT,
                            reason="Dependency link already exists or creates a cycle",
                        )
                    )
                continue

            results.append(
                NarwhalTraceLinkResult(
                    source_item_id=source_item.id,
                    source_identifier=source_item.item_identifier,
                    target_identifier=target_identifier,
                    target_item_id=target_item.id,
                    relationship_type=resolved_relationship_type,
                    status=NarwhalTraceLinkStatus.SUGGESTED,
                )
            )

        return results

    async def _resolve_target_items(
        self,
        *,
        session: AsyncSession,
        project_id,
        target_identifiers: list[str],
        source_document_id,
    ) -> dict[str, SpecItem]:
        if not target_identifiers:
            return {}

        result = await session.execute(
            select(SpecItem)
            .join(Document, SpecItem.document_id == Document.id)
            .where(
                Document.project_id == project_id,
                SpecItem.item_identifier.in_(target_identifiers),
                SpecItem.document_id != source_document_id,
            )
        )
        items = result.scalars().all()

        mapping: dict[str, SpecItem] = {}
        for item in items:
            mapping.setdefault(item.item_identifier, item)
        return mapping

    def _collect_pattern_prefixes(self, *, config_data: dict[str, Any]) -> list[str]:
        prefixes: list[str] = []
        for process_config in config_data.values():
            if not isinstance(process_config, dict):
                continue
            prefix = process_config.get("pattern_prefix")
            if isinstance(prefix, str) and prefix:
                prefixes.append(prefix)
        return sorted(set(prefixes))

    def _extract_trace_identifiers(self, *, content_markdown: str, prefixes: list[str]) -> list[str]:
        if not prefixes:
            return []
        alternation = "|".join(re.escape(prefix) for prefix in prefixes)
        pattern = re.compile(rf"\b(?:{alternation})[A-Za-z0-9][A-Za-z0-9_.-]*\b")
        seen: set[str] = set()
        ordered: list[str] = []
        for identifier in pattern.findall(content_markdown):
            if identifier in seen:
                continue
            seen.add(identifier)
            ordered.append(identifier)
        return ordered

    def _derive_source_identifier(
        self,
        *,
        process_key: str,
        pattern_prefix: str,
        content_markdown: str,
        fallback_token: str,
    ) -> str:
        if pattern_prefix:
            identifiers = self._extract_trace_identifiers(
                content_markdown=content_markdown,
                prefixes=[pattern_prefix],
            )
            if identifiers:
                return identifiers[0]
        return f"{process_key}_{fallback_token}"

    def _resolve_relationship_type(
        self,
        *,
        source_process_key: str,
        target_identifier: str,
        config_data: dict[str, Any],
        relationship_strategy: NarwhalRelationshipStrategy,
        fallback_relationship_type: DependencyRelationshipType,
    ) -> DependencyRelationshipType:
        if relationship_strategy == NarwhalRelationshipStrategy.FIXED:
            return fallback_relationship_type

        target_process_key = self._infer_process_key_from_identifier(
            identifier=target_identifier,
            config_data=config_data,
        )
        if target_process_key is None:
            return fallback_relationship_type

        upstream_processes = {"SYS2", "SWE1", "HWE1"}
        downstream_processes = {"SYS3", "SWE2", "HWE2", "SWE4", "SWE5"}

        if source_process_key in upstream_processes and target_process_key in downstream_processes:
            return DependencyRelationshipType.BLOCKING
        if source_process_key in downstream_processes and target_process_key in upstream_processes:
            return DependencyRelationshipType.BLOCKED_BY
        if source_process_key == target_process_key:
            return DependencyRelationshipType.RELATED

        return fallback_relationship_type

    def _infer_process_key_from_identifier(
        self,
        *,
        identifier: str,
        config_data: dict[str, Any],
    ) -> str | None:
        for process_key, process_config in config_data.items():
            if not isinstance(process_config, dict):
                continue
            pattern_prefix = process_config.get("pattern_prefix")
            if isinstance(pattern_prefix, str) and pattern_prefix and identifier.startswith(pattern_prefix):
                return process_key
        return None
