# Tasks: DocERP Core Workflow and Traceability

**Input**: Design documents from `/specs/002-doce-erp-dms/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/rest-api.yaml`, `quickstart.md`

**Tests**: Include contract, integration, and unit tests because the plan and quickstart explicitly require API contract validation and incremental slice testing.

**Organization**: Tasks are grouped by user story to keep each story independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Every task includes an explicit file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the baseline API/schema/test structure needed by all stories.

- [X] T001 Create API package scaffold in `backend/app/api/__init__.py`
- [X] T002 Create versioned API router composition in `backend/app/api/router.py`
- [X] T003 [P] Create routes package scaffold in `backend/app/api/routes/__init__.py`
- [X] T004 [P] Create schema package scaffold in `backend/app/schemas/__init__.py`
- [X] T005 [P] Create contract test package scaffold in `backend/tests/contract/__init__.py`
- [X] T006 [P] Add shared async DB and UUID fixture setup in `backend/tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared cross-cutting building blocks that block all user stories.

**Critical**: Complete this phase before any user story implementation.

- [X] T007 Create authorization and partition-scope dependencies in `backend/app/api/dependencies/authz.py`
- [X] T008 [P] Create domain error classes in `backend/app/core/errors.py`
- [X] T009 [P] Create API error schemas in `backend/app/schemas/error.py`
- [X] T010 [P] Add global domain error handler wiring in `backend/app/main.py`
- [X] T011 [P] Create immutable audit event model in `backend/app/models/audit_event.py`
- [X] T012 [P] Create notification model for workflow alerts in `backend/app/models/notification.py`
- [X] T013 Create audit and notification service scaffolds in `backend/app/services/audit_service.py`
- [X] T014 Add foundational migration for audit and notification tables in `backend/migrations/versions/0002_audit_and_notifications.py`

**Checkpoint**: Foundation complete; user stories can now proceed.

---

## Phase 3: User Story 1 - Structured Document Lifecycle (Priority: P1) 🎯 MVP

**Goal**: Deliver controlled document lifecycle, revision immutability, and dynamic attribute validation.

**Independent Test**: Create a document, provide required metadata and attributes, transition DRAFT -> REVIEW -> APPROVED, and verify approved revision immutability.

### Tests for User Story 1

- [x] T015 [P] [US1] Add OpenAPI contract tests for document create/get/update/transition endpoints in `backend/tests/contract/test_documents_contract.py`
- [x] T016 [P] [US1] Add lifecycle transition integration tests in `backend/tests/integration/test_document_lifecycle.py`
- [x] T017 [P] [US1] Add dynamic attribute validation unit tests in `backend/tests/unit/test_attribute_validation.py`

### Implementation for User Story 1

- [x] T018 [P] [US1] Extend document fields (`standards_scope`, `last_transition_at`) in `backend/app/models/document.py`
- [x] T019 [P] [US1] Create document revision and transition models in `backend/app/models/document_revision.py`
- [x] T020 [P] [US1] Create standards and requirement models in `backend/app/models/standard.py`
- [x] T021 [P] [US1] Create attribute definition/value models in `backend/app/models/attribute_definition.py`
- [x] T022 [US1] Register US1 ORM exports in `backend/app/models/__init__.py`
- [x] T023 [US1] Add lifecycle and EAV migration script in `backend/migrations/versions/0003_document_lifecycle_and_eav.py`
- [x] T024 [US1] Implement required attribute validation service in `backend/app/services/attribute_validation_service.py`
- [x] T025 [US1] Implement lifecycle transition orchestration service in `backend/app/services/document_lifecycle_service.py`
- [x] T026 [US1] Implement document API schemas in `backend/app/schemas/documents.py`
- [x] T027 [US1] Implement document API endpoints in `backend/app/api/routes/documents.py`
- [x] T028 [US1] Mount document routes under API router in `backend/app/api/router.py`

**Checkpoint**: User Story 1 is independently functional and demo-ready.

---

## Phase 4: User Story 2 - Dependency Impact and Suspect Management (Priority: P2)

**Goal**: Deliver bi-directional traceability, SUSPECT propagation, and resolution evidence capture.

**Independent Test**: Create traceability links, publish upstream approved revision, verify downstream links become SUSPECT, then resolve with auditable evidence.

### Tests for User Story 2

- [x] T029 [P] [US2] Add OpenAPI contract tests for traceability endpoints in `backend/tests/contract/test_traceability_contract.py`
- [x] T030 [P] [US2] Add integration tests for suspect propagation and impact listing in `backend/tests/integration/test_traceability_impacts.py`
- [x] T031 [P] [US2] Add unit tests for circular link prevention and resolution validation in `backend/tests/unit/test_traceability_rules.py`

### Implementation for User Story 2

- [x] T032 [P] [US2] Extend dependency link health fields and enums in `backend/app/models/spec_item.py`
- [x] T033 [P] [US2] Create suspect resolution model in `backend/app/models/suspect_resolution.py`
- [x] T034 [US2] Register US2 ORM exports in `backend/app/models/__init__.py`
- [x] T035 [US2] Add traceability suspect management migration in `backend/migrations/versions/0004_traceability_suspect_management.py`
- [x] T036 [US2] Implement traceability graph and cycle-guard service in `backend/app/services/traceability_service.py`
- [x] T037 [US2] Implement suspect propagation and resolution service in `backend/app/services/suspect_service.py`
- [x] T038 [US2] Implement traceability API schemas in `backend/app/schemas/traceability.py`
- [x] T039 [US2] Implement traceability endpoints in `backend/app/api/routes/traceability.py`
- [x] T040 [US2] Emit SUSPECT owner notifications in `backend/app/services/notification_service.py`

**Checkpoint**: User Story 2 can be tested independently from US3/US4.

---

## Phase 5: User Story 3 - AI-Assisted Compliance Review (Priority: P3)

**Goal**: Deliver durable AI review jobs, clause-linked findings, and auditable suggestion decisions.

**Independent Test**: Submit AI review request for a revision, observe async job states/findings, record accept/reject decisions with rationale rules and retained audit evidence.

### Tests for User Story 3

- [x] T041 [P] [US3] Add OpenAPI contract tests for AI review endpoints in `backend/tests/contract/test_ai_review_contract.py`
- [x] T042 [P] [US3] Add integration tests for queued/partial/retryable AI workflows in `backend/tests/integration/test_ai_review_workflow.py`
- [x] T043 [P] [US3] Add unit tests for suggestion decision rules in `backend/tests/unit/test_ai_review_decisions.py`

### Implementation for User Story 3

- [x] T044 [P] [US3] Create compliance record model in `backend/app/models/compliance.py`
- [x] T045 [P] [US3] Create AI review job/finding/decision models in `backend/app/models/ai_review.py`
- [x] T046 [US3] Register US3 ORM exports in `backend/app/models/__init__.py`
- [x] T047 [US3] Add AI review and compliance migration in `backend/migrations/versions/0005_ai_review_and_compliance.py`
- [x] T048 [US3] Implement AI review job state service in `backend/app/services/ai_review_service.py`
- [x] T049 [US3] Implement AI suggestion decision service in `backend/app/services/ai_decision_service.py`
- [x] T050 [US3] Implement AI review API schemas in `backend/app/schemas/ai_review.py`
- [x] T051 [US3] Implement AI review endpoints in `backend/app/api/routes/ai_reviews.py`

**Checkpoint**: User Story 3 independently covers advisory AI review with human decision control.

---

## Phase 6: User Story 4 - Audit Export to External Governance Platform (Priority: P4)

**Goal**: Deliver structured export job workflow, validation reporting, and export readiness dashboard outputs.

**Independent Test**: Submit export for project, verify artifact manifest + validation issues output, and confirm export status and readiness counters are queryable.

### Tests for User Story 4

- [x] T052 [P] [US4] Add OpenAPI contract tests for export and dashboard endpoints in `backend/tests/contract/test_export_contract.py`
- [x] T053 [P] [US4] Add integration tests for export package generation and validation reporting in `backend/tests/integration/test_export_workflow.py`
- [x] T054 [P] [US4] Add unit tests for export mapping completeness rules in `backend/tests/unit/test_export_validation.py`

### Implementation for User Story 4

- [x] T055 [P] [US4] Create export job/artifact/issue models in `backend/app/models/export_job.py`
- [x] T056 [US4] Register US4 ORM exports in `backend/app/models/__init__.py`
- [x] T057 [US4] Add export jobs migration in `backend/migrations/versions/0006_export_jobs_and_artifacts.py`
- [x] T058 [US4] Implement export package assembly service in `backend/app/services/export_service.py`
- [x] T059 [US4] Implement export completeness validation service in `backend/app/services/export_validation_service.py`
- [x] T060 [US4] Implement export API schemas in `backend/app/schemas/export.py`
- [x] T061 [US4] Implement export endpoints in `backend/app/api/routes/exports.py`
- [x] T062 [US4] Implement dashboard summary aggregation service in `backend/app/services/dashboard_service.py`
- [x] T063 [US4] Implement dashboard summary endpoint in `backend/app/api/routes/dashboard.py`

**Checkpoint**: User Story 4 is independently testable and produces audit-ready export outputs.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, regression coverage, and documentation sync across all stories.

- [x] T064 [P] Finalize route registration for all feature endpoints in `backend/app/api/router.py`
- [x] T065 [P] Reconcile OpenAPI contract with implementation payloads in `specs/002-doce-erp-dms/contracts/rest-api.yaml`
- [x] T066 [P] Add full migration smoke test for new revisions in `backend/tests/integration/test_full_migration_smoke.py`
- [x] T067 [P] Add workflow regression checklist updates in `specs/002-doce-erp-dms/checklists/requirements.md`
- [x] T068 Add performance hotspot index migration in `backend/migrations/versions/0007_performance_hotspot_indexes.py`
- [x] T069 Add localized workflow status/error message catalog in `backend/app/schemas/messages.py`
- [x] T070 Update end-to-end validation runbook in `specs/002-doce-erp-dms/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 (US1)**: Starts after Phase 2.
- **Phase 4 (US2)**: Starts after Phase 3 because SUSPECT propagation depends on document revision/lifecycle behavior.
- **Phase 5 (US3)**: Starts after Phase 3 because AI review requires stable document/revision APIs.
- **Phase 6 (US4)**: Starts after Phases 4 and 5 to export traceability and compliance outcomes together.
- **Phase 7 (Polish)**: Starts after all user-story phases are complete.

### User Story Dependencies

- **US1 (P1)**: Foundation for all downstream stories.
- **US2 (P2)**: Depends on US1 models and lifecycle transitions.
- **US3 (P3)**: Depends on US1 revision model and authorization scaffolding.
- **US4 (P4)**: Depends on US1 + US2 + US3 data completeness.

### Within Each User Story

- Tests first (contract/integration/unit) and expected to fail before implementation.
- Models and migration before service logic.
- Services before schemas and endpoints.
- Endpoint mounting after route implementation.

---

## Parallel Opportunities

### User Story 1

- Run in parallel: T015, T016, T017
- Run in parallel: T018, T019, T020, T021

### User Story 2

- Run in parallel: T029, T030, T031
- Run in parallel: T032, T033

### User Story 3

- Run in parallel: T041, T042, T043
- Run in parallel: T044, T045

### User Story 4

- Run in parallel: T052, T053, T054
- Run in parallel: T055 with T060

### Cross-Story After Foundational Phase

- US2 and US3 can run in parallel once US1 checkpoint is accepted and API contracts are stable.

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate US1 independently with T015-T017 and lifecycle acceptance scenarios.
4. Demo/deploy MVP before expanding scope.

### Incremental Delivery

1. Deliver US1 and validate.
2. Deliver US2 and validate suspect propagation.
3. Deliver US3 and validate AI advisory workflow.
4. Deliver US4 and validate export handoff.
5. Finish with Phase 7 hardening.

### Parallel Team Strategy

1. Team completes Phase 1 and Phase 2 together.
2. Developer A drives US2 while Developer B drives US3 after US1 checkpoint.
3. Developer C prepares US4 model/schema tracks in parallel where marked [P].
4. Integrate all tracks in Phase 7.
