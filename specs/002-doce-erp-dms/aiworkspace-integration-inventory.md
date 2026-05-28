# AiWorkSpace Integration Inventory

## Purpose

Assess which assets from `SM2514_ISO26262/SM2514_Auto/AiWorkSpace` should be integrated into DocERP, how they should be integrated, and what product capabilities they would enable.

## Executive Summary

`AiWorkSpace` is not primarily a backend application. It is a mixed workspace composed of:
- structured ISO 26262 process documents,
- markdown-based authoring conventions,
- traceability ID and folder configuration,
- GUI/tooling for document navigation and editing,
- helper scripts for document restructuring and link maintenance,
- code and design artifact folders that can act as downstream evidence.

For DocERP, the recommended integration target is **capability extraction**, not full repository embedding. The main reusable assets are:
- document templates,
- folder/process taxonomy,
- traceability naming and parsing rules,
- migration/import tooling,
- impact-analysis and reviewer workflow support,
- code-to-document trace sources.

## Evidence Summary

### 1. Process taxonomy and ID system

Source evidence:
- `AiWorkSpace/Narwhal_md_path_config.json`

Observed value:
- Defines process keys such as `SWE1`, `SWE2`, `HWE1`, `HWE2`, `SWE4`, `SYS2`, `SYS3`.
- Defines work-product folders, ID prefixes, block types, and metadata field expectations.
- Encodes parsing assumptions such as `pattern_prefix`, `source_block_type`, and advanced filter fields.

Implication for DocERP:
- This can become the canonical import/config source for process-specific document classes.
- It maps cleanly to DocERP concepts like `document_type`, dynamic attributes, standards scope, and validation profiles.

### 2. Workflow and authoring guidance

Source evidence:
- `AiWorkSpace/workflow/WorkflowHwe1.md`
- `AiWorkSpace/workflow/WorkflowHwe2.md`
- multiple workflow/template files under `AiWorkSpace/workflow/`

Observed value:
- Documents contain process-specific authoring rules, checklist logic, mandatory traceability directions, and ID lifecycle handling.
- These are effectively domain rules and reviewer guidance, not implementation code.

Implication for DocERP:
- These should be treated as policy/template assets.
- They can drive document skeleton generation, reviewer checklist generation, and AI review prompt context.

### 3. Shared tooling environment

Source evidence:
- `AiWorkSpace/tool_package/README_TOOL_PACKAGE.md`
- `AiWorkSpace/tool_package/requirements-sw-tools.txt`

Observed value:
- Provides a shared environment for `AutomotiveMdEditor` and `Migratorybird`.
- Tooling is Windows/Python oriented and focused on GUI navigation, markdown rendering, Excel I/O, and process-aware document handling.

Implication for DocERP:
- The useful part is not the venv itself.
- The useful part is the capability model: markdown navigation, trace parsing, Excel transformation, and document-oriented workflows.

### 4. Structure-maintenance scripts

Source evidence:
- `AiWorkSpace/_scripts/hwe2_link_refresh.py`
- `_scripts/hwe1_hwe2_resplit.py`
- `_scripts/rename_spine_aligned_folders.ps1`

Observed value:
- Scripts repair markdown links, maintain folder alignment, and normalize document layout after restructuring.

Implication for DocERP:
- These are strong candidates to become backend jobs or import/maintenance commands.
- They can evolve into post-import normalization, cross-file link repair, and content refactoring automation.

### 5. GUI editor and document navigation model

Source evidence:
- `AiWorkSpace/README_HWE_文件閱讀指南.md`
- `AiWorkSpace/SwTool/AutomotiveMdEditor/...`

Observed value:
- The workspace is designed around a markdown spine/tree model with outline navigation, trace hover, and process-aware folder browsing.
- It supports reviewing linked markdown rather than only storing static documents.

Implication for DocERP:
- This strongly suggests a future frontend feature set for structured document browsing.
- It should not be copied verbatim at first; instead, its interaction model should inform DocERP UI requirements.

### 6. Existing artifact repositories as trace/evidence sources

Source evidence:
- `AiWorkSpace/HWE1_ReqDoc/`
- `AiWorkSpace/HWE2_Arch/`
- `AiWorkSpace/ReqDoc/`
- `AiWorkSpace/SYS2_ReqDoc/`
- `AiWorkSpace/TestSpec/`
- `AiWorkSpace/ServiceLayer/`

Observed value:
- These folders contain upstream requirements, hardware architecture, software/service-layer implementation artifacts, and test specs.
- They can provide real traceability seeds between requirements, architecture, implementation, and tests.

Implication for DocERP:
- These folders can be imported as source systems.
- They can enrich US2 traceability and US4 export completeness.

## Recommended Integration Strategy

### Track A: Template and document-class integration

What to integrate:
- workflow templates under `AiWorkSpace/workflow/`
- process-folder mappings from `Narwhal_md_path_config.json`
- process-specific metadata fields from `advanced_filter.fields`

How to integrate:
- Add a process template registry in DocERP.
- Map `HWE1/HWE2/SWE1/SWE2/SWE4/SYS2/SYS3` to DocERP document types.
- Use existing EAV support to materialize process-specific metadata requirements.

Resulting DocERP capability:
- users can create ISO 26262 work products with correct section skeletons and metadata expectations.

Priority:
- Highest

### Track B: Bulk import of markdown work products

What to integrate:
- markdown trees under `HWE1_ReqDoc`, `HWE2_Arch`, `ReqDoc`, `SYS2_ReqDoc`, `TestSpec`

How to integrate:
- Build an import job that reads process folder, title, markdown content, and inferred document type.
- Create DocERP `Document`, `DocumentRevision`, and optionally `SpecItem` records from imported files.
- Preserve source path for round-trip traceability.

Resulting DocERP capability:
- existing ISO26262 markdown documentation can be onboarded without manual re-entry.

Priority:
- Highest

### Track C: Traceability rule and ID parsing integration

What to integrate:
- `pattern_prefix`, `swe_type`, and link direction rules from `Narwhal_md_path_config.json`
- workflow markdown guidance that states upstream/downstream rules

How to integrate:
- Add a parser that extracts IDs such as `HWR_*`, `HWA_*`, `SWR_*`, `SYSA_*`, `SWUT_*`.
- Auto-create or suggest `DependencyLink` records from embedded traceability blocks.
- Validate link direction against process rules.

Resulting DocERP capability:
- semi-automatic creation of trace links from legacy markdown and stronger SUSPECT propagation coverage.

Priority:
- Highest

### Track D: Script-to-job conversion

What to integrate:
- `_scripts/hwe2_link_refresh.py`
- related resplit/rename maintenance scripts

How to integrate:
- Convert these into backend maintenance jobs or admin commands.
- Run them after import or document tree refactoring.

Resulting DocERP capability:
- automated link repair, normalized folder/content structure, and lower maintenance cost after migration.

Priority:
- Medium

### Track E: GUI interaction model reuse

What to integrate:
- Automotive MD Editor interaction patterns

How to integrate:
- Do not embed PyQt GUI directly.
- Recreate key behaviors in DocERP frontend later:
  - spine/tree navigation,
  - outline panel,
  - trace hover preview,
  - double-click jump to linked content.

Resulting DocERP capability:
- structured engineering-document navigation instead of plain file storage.

Priority:
- Medium

### Track F: Code and evidence correlation

What to integrate:
- `ServiceLayer/`, `SwTool/`, and other implementation directories

How to integrate:
- Add a scanner that maps code modules and filenames to requirement/architecture references.
- Use this as an optional downstream evidence source, not as the first migration target.

Resulting DocERP capability:
- traceability between requirement, architecture, implementation, and tests.

Priority:
- Medium

## What Should Not Be Imported Directly

### 1. Full Python virtual environment or tool runtime

Do not import:
- `tool_package/venv`
- Windows-specific bootstrap scripts as runtime dependencies

Reason:
- environment-specific, large, and not part of DocERP domain data.

### 2. Full PyQt GUI application as-is

Do not import:
- Automotive MD Editor source as a direct submodule of backend

Reason:
- wrong runtime model for a web application.
- should be translated into web interaction requirements instead.

### 3. Arbitrary generated outputs

Do not import directly:
- ad hoc Excel outputs such as `traceability_scan_*.xlsx`

Reason:
- useful as input sources, but not canonical application logic.
- should be handled via importers and evidence attachments.

## Concrete Feature Gains If Integrated

### 1. ISO 26262 template-driven document creation

Users can create HWE/SWE/SYS work products with the correct chapter structure and expected metadata from the start.

### 2. Legacy markdown migration into DocERP

Existing markdown repositories become first-class DocERP documents and revisions instead of external unmanaged files.

### 3. Process-aware traceability extraction

Trace IDs and embedded link rules can be parsed into DocERP traceability relations automatically.

### 4. Better SUSPECT impact coverage

When imported trace rules and legacy paths are available, downstream impact analysis becomes broader and more accurate.

### 5. Evidence-aware AI review

Workflow docs and templates can be fed into AI review prompts so that findings become process-specific rather than generic.

### 6. Stronger audit export packages

Export can include richer process metadata, imported traceability, and source-path evidence from migrated assets.

### 7. Maintenance automation for markdown ecosystems

Existing workspace scripts can become admin jobs for link refresh, content normalization, and tree maintenance.

## Recommended Implementation Order

### Phase 1

- Import `Narwhal_md_path_config.json` concepts into DocERP config.
- Add process template registry.
- Add markdown import job for `HWE1/HWE2/SYS2/SWE1/SWE2/SWE4` folders.

### Phase 2

- Parse traceability IDs and auto-suggest links.
- Import traceability scan Excel as optional evidence/input.
- Add validation against process-specific upstream/downstream rules.

### Phase 3

- Convert maintenance scripts into backend jobs.
- Add source-path based impact-analysis support.
- Extend export package with imported evidence references.

### Phase 4

- Recreate Automotive MD Editor navigation patterns in DocERP frontend.
- Add code/artifact correlation from implementation directories.

## Mapping to Current DocERP Modules

| AiWorkSpace asset | DocERP target |
|---|---|
| `Narwhal_md_path_config.json` | backend config + import profile model |
| `workflow/*.md` templates | document template registry + AI review context |
| `HWE1_ReqDoc`, `HWE2_Arch`, `ReqDoc`, `SYS2_ReqDoc`, `TestSpec` | document import pipeline |
| traceability scan Excel files | import/evidence attachment pipeline |
| `_scripts/*.py` | backend maintenance jobs / admin tools |
| `ServiceLayer/`, implementation folders | optional code-evidence scanner |
| AutomotiveMdEditor interaction model | future frontend structured document viewer |

## Final Recommendation

Integrate `AiWorkSpace` as a **source of templates, process taxonomy, traceability rules, and migration tooling**, not as a monolithic code drop.

The first DocERP milestone should be:
- process template registry,
- markdown import pipeline,
- trace ID parser,
- rule-aware traceability generation.

That path delivers the highest value with the lowest architectural risk.
