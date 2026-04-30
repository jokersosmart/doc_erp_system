# Tasks: DocERP — Spec-Driven Document Management System

**Input**: Design documents from `specs/001-doce-erp-dms/`
**Branch**: `002-doce-erp-dms`
**Date**: 2026-04-29
**Prerequisites**: [plan.md](./plan.md) ✅ | [spec.md](./spec.md) ✅ | [research.md](./research.md) ✅ | [data-model.md](./data-model.md) ✅ | [contracts/](./contracts/) ✅

---

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, independent from in-progress tasks)
- **[US1–US6]**: User Story this task belongs to
- All paths relative to workspace root (`d:\joker.kang\Desktop\Folder\Doc_erp_system\`)

---

## Phase 1: Setup

**Purpose**: Repository structure, tooling, and Docker dev environment initialization.

- [x] T001 Create full project directory structure per `plan.md` Project Structure section (backend/, frontend/, docker-compose.yml)
- [x] T002 Initialize Python 3.11 backend project with `pyproject.toml` in `backend/` — dependencies: fastapi, sqlalchemy[asyncio], celery, redis, langchain, openpyxl, gitpython, python-ldap, alembic, httpx, pytest, pytest-asyncio
- [x] T003 [P] Initialize React 18 + TypeScript 5.x frontend project with `package.json` in `frontend/` — dependencies: react, react-router-dom, tanstack-query, zustand, @tanstack/react-table, react-i18next, vitest, playwright
- [x] T004 [P] Create `docker-compose.yml` at repo root — services: postgres:16, redis:7, backend, frontend; bind-mount volumes for on-premise data persistence (FR-032)
- [x] T005 [P] Configure backend linting/formatting in `backend/pyproject.toml` — ruff, mypy strict mode, pre-commit hooks
- [x] T006 [P] Configure frontend linting/formatting in `frontend/` — eslint, prettier, TypeScript strict mode

**Checkpoint**: `docker-compose up` brings up empty Postgres + Redis — proceed to Foundational.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on. Must be complete before any US work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T007 Implement `backend/app/core/config.py` — pydantic-settings: DATABASE_URL, REDIS_URL, LDAP_URL, LDAP_BIND_DN, LLM_API_URL, LLM_API_KEY, SECRET_KEY, GIT_BACKEND_TYPE
- [x] T008 Implement `backend/app/core/database.py` — SQLAlchemy 2.x async engine, session factory, `get_db` dependency
- [x] T009 Create Alembic migration environment in `backend/migrations/` — `alembic.ini`, `env.py` using async engine
- [x] T010 [P] Implement `organisation_nodes` model + migration in `backend/app/models/org.py` — all columns per data-model.md §1; indexes on parent_id, bu_scope, level
- [x] T011 [P] Implement `projects` model + migration in `backend/app/models/org.py` — all columns per data-model.md §2
- [x] T012 [P] Implement `users` model + migration in `backend/app/models/org.py` — LDAP DN, locale (zh-TW/en), is_local_admin, password_hash (bcrypt, local admin only) per data-model.md §3
- [x] T013 [P] Implement `roles` + `project_role_assignments` models + migration in `backend/app/models/org.py` — RBAC permission JSONB per data-model.md §4
- [x] T014 Implement `documents` model + migration in `backend/app/models/document.py` — lifecycle_state enum (DRAFT/REVIEW/APPROVED/OBSOLETE), lock_state enum (UNLOCKED/LOCKED/PENDING_QRA), is_safety_critical, bu_node_id, current_version (optimistic lock counter), schema_version per data-model.md §5
- [x] T015 [P] Implement `document_versions` model + migration in `backend/app/models/document.py` — full content_markdown snapshot per data-model.md §6
- [x] T016 [P] Implement `attribute_definitions` model + migration in `backend/app/models/spec_item.py` — EAV registry with schema_version per data-model.md §7 (FR-035)
- [x] T017 Implement `spec_items` + `dependency_links` models + migration in `backend/app/models/spec_item.py` — item_type enum, Blocking/Blocked By/Related relationship_type enum per data-model.md §8–9
- [x] T018 [P] Implement `audit_trail_entries` + `notification_records` models + migration in `backend/app/models/audit_package.py` per data-model.md
- [x] T019 Implement `backend/app/core/security.py` — LDAP bind via python-ldap (primary), bcrypt local-admin verification (fallback FR-038), JWT access token generation/validation; emergency local-login audit log write + security alert emit
- [x] T020 Implement `backend/app/api/v1/auth.py` — POST `/api/v1/auth/login` (LDAP first, local fallback), POST `/api/v1/auth/logout`, GET `/api/v1/auth/me`; enforce FR-038 LDAP-first behaviour
- [x] T021 Implement `backend/app/api/deps.py` — `get_current_user`, `require_role`, `get_project`, RBAC permission check helpers (FR-004)
- [x] T022 Implement FastAPI app entry point `backend/app/main.py` — middleware: CORS (internal network only), request ID, error handler; mount all v1 routers; lifespan: Celery worker healthcheck
- [x] T023 Implement Celery app + Redis broker in `backend/app/tasks/__init__.py` — celery app config, task autodiscovery; `docker-compose.yml` celery worker service
- [x] T024 [P] Implement `backend/app/services/notification.py` — in-app notification write to `notification_records`; email dispatch attempt via SMTP (silently log failure to system log per FR-046, no retry, no in-app fallback)
- [x] T025 [P] Implement `frontend/src/services/api.ts` — axios/fetch base client with JWT header injection, 401 redirect to login, request ID propagation
- [x] T026 [P] Implement `frontend/src/i18n/` — react-i18next setup, `zh-TW.json` + `en.json` locale files with all base UI keys; ISO/ASPICE terms kept in English in both locales (FR-040)
- [x] T027 Implement `frontend/src/pages/LoginPage.tsx` — LDAP credential form, submit to POST `/api/v1/auth/login`, JWT store in memory (not localStorage), redirect to dashboard on success

**Checkpoint**: Auth flow works end-to-end (login → JWT → protected route). DB migrations run clean. Celery worker starts. Proceed to US1.

---

## Phase 3: User Story 1 — AI-Guided Project Onboarding (Priority: P0) 🎯 MVP

**Goal**: A PM can create a new project through an AI wizard (6–8 questions), and a fully pre-populated document framework is generated for the selected BU & compliance standards.

**Independent Test**: A PM logs in, completes the wizard, and sees a document skeleton with correct partitions — before any other feature is implemented.

- [x] T028 [US1] Implement `backend/app/api/v1/projects.py` — GET `/api/v1/org/nodes` (org hierarchy tree), POST `/api/v1/projects` (create project), GET `/api/v1/projects/{id}` per contracts/rest-api.md
- [x] T029 [US1] Implement `wizard_sessions` model + migration in `backend/app/models/org.py` — step_index, answers_json, project_context_json, expires_at (90-day TTL per FR-043), user_id FK
- [x] T030 [US1] Implement `backend/app/api/v1/projects.py` — POST `/api/v1/wizard/sessions` (create wizard session), PATCH `/api/v1/wizard/sessions/{id}/step` (step auto-save per FR-043), GET `/api/v1/wizard/sessions/active` (resume detection), DELETE `/api/v1/wizard/sessions/{id}` (start-over clears session); 90-day expiry via Celery periodic task
- [x] T031 [US1] Implement `backend/app/services/ai_consultant.py` stub — `generate_wizard_questions(bu, standards)` returns the 6–8 structured questions (project name, BU, ASPICE level, ASIL/CAL, participating departments, document types); at this stage: config-driven static questions, not LLM (LLM RAG added in US2)
- [x] T032 [US1] Implement `backend/app/services/ai_consultant.py` — `generate_document_framework(wizard_session)`: creates `documents` + `spec_items` scaffold rows for every required partition (SYS/HW/SWE/SAFETY/SECURITY) based on BU template config and selected standards; pre-populates section titles and clause reference placeholders per BU template
- [x] T033 [US1] Seed BU template configurations in `backend/migrations/` Alembic data migration — SSD Controller BU templates (HARA, Safety Goals, System Spec, FW Spec, HW Spec, SW Spec, VCT Plan) + eMMC BU templates (distinct from SSD per FR-002); seed `attribute_definitions` rows for base HW template fields from RD-03-010-09
- [x] T034 [P] [US1] Implement `frontend/src/components/wizard/WizardContainer.tsx` — multi-step form (6–8 steps), step auto-save via PATCH on each answer (FR-043), resume prompt on re-entry ("Continue" / "Start Over"), progress bar, responsive layout
- [x] T035 [P] [US1] Implement `frontend/src/components/wizard/WizardStep.tsx` — renders question + answer options per step type (select, multiselect, text input); locale-aware labels (FR-040)
- [x] T036 [US1] Implement `frontend/src/pages/ProjectDashboardPage.tsx` — role-specific dashboard shell: PM view shows document skeleton list with lifecycle badges + lock state badges (FR-012); empty state for new project; data from GET `/api/v1/projects/{id}/documents`
- [x] T037 [US1] Add GET `/api/v1/projects/{id}/documents` endpoint in `backend/app/api/v1/documents.py` — returns document list with lifecycle_state + lock_state + owner per project, RBAC enforced

**Checkpoint**: PM completes wizard → document skeleton visible on dashboard. Wizard resume works after browser close. Two BUs produce different frameworks.

---

## Phase 4: User Story 2 — In-Editor AI Compliance Consulting (Priority: P0)

**Goal**: An RD can open a Spec, invoke the AI consultant, receive gap suggestions with clause references, and Accept/Reject each — with audit trail logging.

**Independent Test**: An RD opens any existing Spec, invokes AI consultant, receives ≥1 actionable suggestion, accepts it, and sees it in both the document and the audit trail.

- [x] T038 [US2] Implement `ai_suggestions` model + migration in `backend/app/models/document.py` — spec_item_id FK, suggested_content, clause_reference, status (PENDING/ACCEPTED/REJECTED), accepted_by FK users, accepted_at, created_at per data-model.md
- [x] T039 [US2] Implement POST `/api/v1/ai/consult` in `backend/app/api/v1/ai.py` — accepts document_id + optional spec_item_id; calls `ai_consultant.py` gap analysis; returns list of AISuggestion objects (suggested_content, clause_ref, position_hint); enforces FR-007 suggestion-only mode (no writes without Accept)
- [x] T040 [US2] Implement LangChain RAG pipeline in `backend/app/services/ai_consultant.py` — vector store over ASPICE 3.1 / ISO-26262 / ISO-21434 reference chunks (ChromaDB or pgvector), retriever + LLM chain; context extraction layer sends only minimal spec section text to cloud LLM API (FR-033); fallback to local static rule checklist when LLM API unavailable (FR-033b); AI_OFFLINE_MODE banner flag in response
- [x] T041 [US2] Implement POST `/api/v1/ai/suggestions/{id}/accept` in `backend/app/api/v1/ai.py` — inserts accepted content into correct spec_item position; writes `audit_trail_entries` row: "Suggested by AI, accepted by [user] on [datetime]" (FR-008); returns updated spec_item
- [x] T042 [US2] Implement POST `/api/v1/ai/suggestions/{id}/reject` in `backend/app/api/v1/ai.py` — sets suggestion status=REJECTED; no document modification; no audit entry for rejects (FR-007)
- [x] T043 [US2] Implement `backend/app/api/v1/documents.py` — GET `/api/v1/documents/{id}` (full document content + spec_items + attribute values), PATCH `/api/v1/documents/{id}` (optimistic lock: send current_version, 409 if mismatch → return three-way diff payload per FR-015b), POST `/api/v1/documents/{id}/versions` (save new version snapshot)
- [x] T044 [US2] Implement unified FW/HW standard deviation check in `backend/app/services/ai_consultant.py` — `check_template_compliance(document)`: compares document sections against `attribute_definitions` registry; flags missing required sections as gaps in AI suggestion response (FR-036, FR-037)
- [x] T045 [P] [US2] Implement `frontend/src/components/editor/SpecEditor.tsx` — Markdown editor with section rendering; AI consultant trigger button always visible; connects to POST `/api/v1/ai/consult` on click; shows AI_OFFLINE banner when offline mode flagged (FR-033b)
- [x] T046 [P] [US2] Implement `frontend/src/components/editor/AISidePanel.tsx` — list of AISuggestion cards, each showing: gap description, suggested content, clause reference (e.g., "ISO-26262 Part 6 Clause 7.4.2"), Accept button, Reject button; no auto-insertion (FR-007); accepted suggestions appear in editor at correct position
- [x] T047 [US2] Implement `frontend/src/components/editor/ConflictMergeModal.tsx` — three-way diff UI shown on 409 conflict (my changes / base / their changes); human must manually resolve (FR-015b); no auto-merge; submit resolved content via PATCH with resolved version

**Checkpoint**: RD invokes AI consultant → suggestion appears in side panel → Accept inserts into doc → audit trail entry created. Offline fallback shows banner + static rules.

---

## Phase 5: User Story 3 — Cascade Lock & Dependency Notification (Priority: P0)

**Goal**: Architect saves top-level Spec → all dependent sub-team Specs atomically locked (BU-scoped per FR-041) → owners notified with diff view → standard Specs self-unlock after review → safety-critical Specs require QRA approval.

**Independent Test**: Two-account demo: Architect saves System Spec → dependent Spec owner sees LOCKED banner + diff view.

- [ ] T048 [US3] Implement `lock_events` model + migration in `backend/app/models/lock_event.py` — upstream_document_id, triggered_by_user_id, bu_node_id (BU scope), locked_document_ids (UUID array), triggered_at, resolved_at per data-model.md
- [ ] T049 [US3] Implement `backend/app/services/dependency_engine.py` — `build_dependency_graph(project_id)`: loads all DependencyLinks for project into an in-memory directed graph; `get_directly_dependent_specs(document_id)`: returns all documents with Blocked By links pointing to the given document; `get_bu_scope(document_id)`: returns bu_node_id for BU-scoped lock filtering (FR-041)
- [ ] T050 [US3] Implement Celery task `backend/app/tasks/cascade_lock.py` — `apply_cascade_lock(document_id, triggered_by_user_id)`: BU-scoped (FR-041): only locks dependent documents within same BU; deferred lock semantics (FR-015c): for each target document, if currently being edited (optimistic lock check on current_version vs DB), record pending lock; apply lock (UNLOCKED → LOCKED) atomically via DB transaction with SELECT FOR UPDATE; write LockEvent record; dispatch in-app + email notifications to each owner with diff payload; task must be idempotent
- [ ] T051 [US3] Implement PATCH `/api/v1/documents/{id}/lifecycle` in `backend/app/api/v1/documents.py` — handles state transitions: DRAFT→REVIEW, REVIEW→APPROVED, REVIEW→DRAFT, APPROVED→REVIEW, APPROVED→OBSOLETE; APPROVED transition automatically sets lock_state=UNLOCKED (FR-013/014); APPROVED→OBSOLETE triggers `obsolete_scan` Celery task; APPROVED→REVIEW triggers `apply_cascade_lock` Celery task for dependent docs
- [ ] T052 [US3] Implement PATCH `/api/v1/documents/{id}/lock` in `backend/app/api/v1/documents.py` — `mark_reviewed`: for standard doc (is_safety_critical=False): LOCKED→UNLOCKED; for safety-critical (is_safety_critical=True): LOCKED→PENDING_QRA (FR-013/014); `qra_approve`: PENDING_QRA→UNLOCKED (QRA role only) writes to audit trail; `emergency_override`: PENDING_QRA→UNLOCKED (PM/Manager role), writes full audit log entry (FR-014b) + sends security alert to QRA; validate lock is only applicable in REVIEW/APPROVED lifecycle states
- [ ] T053 [US3] Implement Celery task `backend/app/tasks/obsolete_scan.py` — `scan_obsolete_downstream(document_id)`: scans all DependencyLinks whose upstream is any SpecItem in the obsolete document; marks affected SpecItems with `upstream_obsolete_warning=True`; sends in-app + email to each downstream owner; writes audit_trail_entries (FR-039)
- [ ] T054 [US3] Implement GET `/api/v1/documents/{id}/diff` in `backend/app/api/v1/documents.py` — returns diff between current version and the version at lock trigger time (LockEvent.triggered_at); used by LOCKED document owner to see what changed upstream (FR-017)
- [ ] T055 [US3] Implement `backend/app/api/v1/spec_items.py` — POST `/api/v1/documents/{id}/spec-items/{item_id}/dependencies` (create Blocking/Blocked By/Related link); Celery task enqueue for async cycle detection (FR-015d); DELETE dependency link
- [ ] T056 [US3] Implement Celery task `backend/app/tasks/cycle_detection.py` — `detect_cycles(project_id)`: DFS over Blocking/Blocked By graph; if cycle found: flag the completing DependencyLink as `has_cycle_warning=True`; send in-app + email to all cycle-participant document owners listing full circular path (FR-015d); MUST NOT remove or alter any user-defined link
- [ ] T057 [P] [US3] Implement `frontend/src/components/lock/LockBanner.tsx` — renders LOCKED (red), PENDING_QRA (yellow), APPROVED/UNLOCKED (green) banners on document header; shows responsible-next-action person name; "Mark as Reviewed & Updated" button (FR-012)
- [ ] T058 [P] [US3] Implement `frontend/src/components/lock/DiffView.tsx` — inline diff panel shown when document is LOCKED; fetches GET `/api/v1/documents/{id}/diff`; highlights changed sections from upstream Spec (FR-017)
- [ ] T059 [P] [US3] Implement `frontend/src/components/lock/QRAApprovalFlow.tsx` — QRA auditor review panel: shows upstream diff + owner's changes; Approve / Request Revision buttons; revision request posts QRA comments to owner (FR-014)
- [ ] T060 [US3] Implement WebSocket notification endpoint in `backend/app/api/v1/` + `frontend/src/services/notificationSocket.ts` — real-time in-app notifications for lock events, QRA actions, cycle warnings; fallback: poll GET `/api/v1/notifications` every 30 s
- [ ] T061 [US3] Implement `frontend/src/components/dependency/DependencyGraph.tsx` — interactive DAG visualisation (react-flow or d3-force); nodes = documents/spec_items; edges = Blocking (solid red) / Blocked By (solid orange) / Related (dashed blue); cycle warning badge on flagged edges; BU scope filter; "Upstream Obsolete Warning" indicator on flagged nodes

**Checkpoint**: Architect saves → dependents locked → owners see LOCKED banner + diff. Safety-critical triggers PENDING_QRA. QRA approves → green banner. Cycle detection fires async.

---

## Phase 6: User Story 4 — Traceability Matrix & One-Click Audit Package Export (Priority: P1)

**Goal**: Auditor runs one-click compliance check → sees gap report → downloads CodeBeamer-compatible Excel → all historical packages retained.

**Independent Test**: Auditor triggers compliance check + Excel download on any project with ≥1 document — even if not perfectly formatted.

- [ ] T062 [US4] Implement `compliance_check_results` + `audit_packages` models + migration in `backend/app/models/audit_package.py` — audit_package: project_id, filename (convention: `<project-id>_audit_<YYYY-MM-DD>_<HHmm>_<username>.xlsx`), triggered_by, standards_scope, storage_path, created_at; compliance_check_result: gap list JSONB, standards checked per data-model.md
- [ ] T063 [US4] Implement `backend/app/services/export_service.py` — `generate_compliance_check(project_id)`: iterates all Spec Items + DependencyLinks; for each FR-034 attribute (Clause Reference, Blocking, Blocked By, Related): flags items missing required attributes against ASPICE / ISO-26262 / ISO-21434 rule set (static rules + RAG-enhanced if AI online); returns structured gap list with severity and recommended action
- [ ] T064 [US4] Implement POST `/api/v1/audit/check` in `backend/app/api/v1/audit.py` — triggers compliance check, stores result in `compliance_check_results`, returns gap report (FR-023)
- [ ] T065 [US4] Implement `backend/app/services/export_service.py` — `generate_codebeamer_xlsx(project_id)`: uses openpyxl to build `.xlsx` with columns per FR-024 (Status, Safety Related, Source HSR, Source HSI, SM ID, SM Type, Reaction/Diagnostics, FDTI, FRTI, FHTI, Diagnostic Coverage, Ref., Verification, Dependency, CC-ID, CC Type, Source HCR-ID, Reaction/Response); maps SpecItem EAV attribute values to corresponding columns; safety-critical attributes (FDTI, FRTI, FHTI, Diagnostic Coverage) enforced as typed values with validation rules
- [ ] T066 [US4] Implement post-generation validation in `backend/app/services/export_service.py` — `validate_xlsx_against_schema(xlsx_path, codebeamer_schema_version)`: checks column names, ordering, and value types against the configured CodeBeamer schema version; returns list of discrepancies (column, row, expected format, recommended fix); if issues found: xlsx is still made available but "Potential Import Issues" report is generated as PDF (FR-044)
- [ ] T067 [US4] Implement POST `/api/v1/audit/export` in `backend/app/api/v1/audit.py` — generates xlsx + validation report; saves AuditPackage record with filename per FR-045 convention; stores immutably on server; returns download links for xlsx + optional issues PDF; GET `/api/v1/audit/packages` returns all historical packages for project (FR-045)
- [ ] T068 [US4] Implement traceability matrix query in `backend/app/api/v1/audit.py` — GET `/api/v1/projects/{id}/traceability` — returns requirement→design→test→evidence mapping by traversing DependencyLinks; surfaces broken links (missing downstream linkage) (FR-022)
- [ ] T069 [P] [US4] Implement `frontend/src/pages/AuditPage.tsx` — one-click "Audit Check" button → gap report table with severity badges; one-click "Export" → xlsx download with validation status indicator (green "Validation Passed" or yellow issues count badge) + separate issues PDF download (FR-044)
- [ ] T070 [P] [US4] Implement `frontend/src/pages/AuditPackageHistoryPage.tsx` — reverse-chronological list of all historical audit packages: export timestamp, triggering user, standards scope, re-download button (FR-045); storage quota warning banner when threshold exceeded (admin role)
- [ ] T071 [US4] Implement traceability matrix UI in `frontend/src/components/dashboard/TraceabilityMatrix.tsx` — requirement → design element → test case → evidence table; broken link indicator (FR-022); PM dashboard integration

**Checkpoint**: Auditor runs compliance check → gap report displayed. Excel downloaded with correct RD-03-010-09 columns. Historical packages listed and re-downloadable.

---

## Phase 7: User Story 5 — FMEDA Automation (Priority: P1)

**Goal**: Safety engineer inputs component data → system computes SPFM, LFM, PMHF automatically → flags threshold failures → exports CodeBeamer-compatible Excel.

**Independent Test**: Engineer inputs minimal component data → SPFM/LFM/PMHF values computed and displayed.

- [ ] T072 [US5] Implement `fmeda_worksheets` + `failure_mode_library` + `failure_mode_library_audit` models + migration in `backend/app/models/fmeda.py` — failure_mode_library: component_type, lambda_value, failure_mode_distribution JSONB, diagnostic_coverage_default, library_version (per FR-042); fmeda_worksheet: project_id, document_id, component_rows JSONB, spfm, lfm, pmhf, asil_target, threshold_failures JSONB, library_version_used, calculation_version
- [ ] T073 [US5] Implement `backend/app/services/fmeda_calculator.py` — `calculate_fmeda(worksheet_id)`: load component rows + resolve failure mode library entries (by library_version_used — pinned at calculation time per FR-042); compute SPFM = 1 - DC_covered/λ_total, LFM = latent metric, PMHF = Σ(λ_SP × (1-DC_SP)); flag results not meeting configured ASIL-B thresholds (SPFM ≥ 99%, LFM ≥ 90%, PMHF ≤ 10⁻⁸/h); store result as new calculation_version without overwriting historical (FR-042e)
- [ ] T074 [US5] Implement `backend/app/api/v1/fmeda.py` — POST `/api/v1/fmeda/worksheets` (create); PATCH `/api/v1/fmeda/worksheets/{id}/components` (update component rows); POST `/api/v1/fmeda/worksheets/{id}/calculate` (trigger SPFM/LFM/PMHF calculation); GET `/api/v1/fmeda/worksheets/{id}/results`; POST `/api/v1/fmeda/worksheets/{id}/export` (CodeBeamer xlsx per FR-030) per contracts/rest-api.md
- [ ] T075 [US5] Implement Failure Mode Library Management API in `backend/app/api/v1/fmeda.py` — GET `/api/v1/fmeda/library` (list entries, filter by component_type); POST `/api/v1/fmeda/library` (add custom entry — admin role only); PATCH `/api/v1/fmeda/library/{id}` (edit); DELETE `/api/v1/fmeda/library/{id}` (soft delete); POST `/api/v1/fmeda/library/import` (bulk import via Excel template); all mutations write versioned `failure_mode_library_audit` records (FR-042d)
- [ ] T076 [US5] Seed baseline Failure Mode Library in `backend/migrations/` Alembic data migration — common IC design component types (flip-flop, SRAM, Flash, PLLs, ADC/DAC, power regulators) with ICd-standard λ values and default failure mode distributions (FR-042a)
- [ ] T077 [P] [US5] Implement `frontend/src/components/fmeda/FMEDAWorksheet.tsx` — spreadsheet-like component input grid (component name, type, λ, failure mode distribution, diagnostic coverage); library lookup picker; "Calculate" button; results section showing SPFM/LFM/PMHF with threshold pass/fail badges (FR-029)
- [ ] T078 [P] [US5] Implement `frontend/src/components/fmeda/FailureModeLibraryManager.tsx` — admin UI: searchable library table, add/edit/delete row (admin only), bulk import button, version history view per entry (FR-042b/c/d)

**Checkpoint**: Safety engineer inputs components → SPFM/LFM/PMHF computed → failures flagged → Excel exported.

---

## Phase 8: User Story 6 — Git Commit via DocERP (Priority: P1)

**Goal**: RD commits a document via DocERP UI without knowing Git — backend pushes to Gerrit/GitHub/GitLab; dependency + audit routines triggered on success.

**Independent Test**: Engineer clicks Commit in DocERP UI → corresponding commit appears in configured Git backend.

- [ ] T079 [US6] Implement `backend/app/services/git_abstraction.py` — `GitBackendAdapter` abstract class; `GerritAdapter`, `GitHubAdapter`, `GitLabAdapter` concrete implementations using GitPython; `commit_document(project, document, message, user)`: serialises document Markdown to `git_path`, creates commit, pushes to backend; backend type selected from `projects.git_backend_type`; credential lookup from environment secrets (never from DB per FR-032)
- [ ] T080 [US6] Implement POST `/api/v1/documents/{id}/commit` in `backend/app/api/v1/documents.py` — validates lock_state=UNLOCKED (LOCKED → 423 with lock reason, FR-016); validates lifecycle_state=APPROVED; calls `git_abstraction.commit_document`; on success: updates `documents.git_commit_sha`; asynchronously triggers dependency + audit update routines via Celery; returns commit SHA and Git backend URL
- [ ] T081 [US6] Implement post-commit dependency + audit update Celery task in `backend/app/tasks/` — `post_commit_update(document_id, commit_sha)`: re-evaluates traceability links, refreshes audit_trail_entries with commit reference, notifies PM dashboard of successful commit event
- [ ] T082 [P] [US6] Implement `frontend/src/components/editor/CommitPanel.tsx` — "Commit" button visible on unlocked APPROVED documents; commit message input; backend selector indicator (Gerrit/GitHub/GitLab) read-only from project config; disabled with lock-reason tooltip on LOCKED documents (FR-016); success shows commit SHA + Git URL

**Checkpoint**: Engineer commits via UI → commit SHA visible in DocERP + in Git backend → LOCKED doc blocks commit with message.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: i18n completeness, admin panel, storage quota, system log viewer, E2E tests, performance validation.

- [ ] T083 Complete `frontend/src/i18n/zh-TW.json` + `en.json` — all UI strings, error messages, notification text, system messages fully localised in both languages; ISO/ASPICE terms (ASIL, CAL, SPFM, LFM, PMHF, etc.) kept in English in both locales (FR-040); language preference persisted per user account via PATCH `/api/v1/auth/me/preferences`
- [ ] T084 [P] Implement admin panel pages in `frontend/src/pages/AdminPage.tsx` — system log viewer (delivery failure log per FR-046), CodeBeamer schema version update UI (FR-044), storage quota dashboard for Audit Package volume with configurable threshold warning (FR-045), LDAP connection status indicator
- [ ] T085 [P] Implement CodeBeamer schema version management API in `backend/app/api/v1/audit.py` — GET/PUT `/api/v1/admin/codebeamer-schema-version`; schema definition stored in DB (not hardcoded); admins can update column definitions to track CodeBeamer version updates (FR-044)
- [ ] T086 [P] Implement Audit Package storage quota monitoring Celery periodic task in `backend/app/tasks/` — checks total size of stored Audit Package files against configured threshold (default 80%); writes storage_warning to system dashboard if exceeded (FR-045)
- [ ] T087 Implement Playwright E2E test suite in `frontend/tests/e2e/` — cover: wizard create project → document skeleton visible; AI consultant accept suggestion → audit trail entry; Architect save → sub-team LOCKED; QRA approve → UNLOCKED; commit blocked on LOCKED; Git commit → SHA visible; FMEDA calculate → thresholds flagged
- [ ] T088 [P] Implement backend integration tests in `backend/tests/integration/` — cover: cascade lock atomicity (no partial states); BU-scoped cascade lock (only same-BU docs locked per FR-041); optimistic lock 409 returns three-way diff; OBSOLETE scan notifies downstream owners; cycle detection flags circular path
- [ ] T089 [P] Performance validation — load test dependency graph update latency with `backend/tests/` locust script: 100 concurrent users, simulate document save → confirm cascade lock Celery task completes < 3 s (SC-003); document list page load < 2 s; Git commit round-trip < 5 s
- [ ] T090 Compile `quickstart.md` final developer instructions update — verify all docker-compose steps, DB migration sequence, LDAP test stub config, LLM API env var setup, add known troubleshooting entries for Windows/Linux on-premise differences

---

## Dependencies (Story Completion Order)

```
Phase 1 (Setup)
    └─→ Phase 2 (Foundational) — auth, DB, models, Celery
            ├─→ Phase 3 (US1: Wizard + Project Creation) ──┐
            │       └─→ Phase 4 (US2: AI Consultant)        │
            │               └─→ Phase 5 (US3: Cascade Lock) │
            │                       └─→ Phase 6 (US4: Audit Export)
            ├─→ Phase 7 (US5: FMEDA) [independent of US2/3/4, depends only on Foundational + US1 for project context]
            └─→ Phase 8 (US6: Git Commit) [independent of US2–5, depends only on Foundational + US1 for document model]
                        └─→ Phase 9 (Polish)
```

**Story independence notes**:
- US5 (FMEDA) depends on US1 only for project/document models — can develop in parallel with US2/US3.
- US6 (Git) depends on US1 document model only — can develop in parallel with US2–US5.
- US4 (Audit Export) depends on US1 (documents exist), US3 (lock enforcement on export), US2 (compliance gap logic).

---

## Parallel Execution Examples Per Story

### Phase 3 (US1): Parallel after T031
| Stream A | Stream B |
|----------|----------|
| T032 (framework generation service) | T034 (WizardContainer UI) |
| T033 (seed BU templates) | T035 (WizardStep UI) |
| T037 (project documents API) | T036 (ProjectDashboardPage) |

### Phase 4 (US2): Parallel after T039
| Stream A | Stream B |
|----------|----------|
| T040 (RAG pipeline) | T045 (SpecEditor UI) |
| T041/T042 (accept/reject API) | T046 (AISidePanel UI) |
| T044 (template deviation check) | T047 (ConflictMergeModal) |

### Phase 5 (US3): Parallel after T050
| Stream A | Stream B | Stream C |
|----------|----------|----------|
| T051 (lifecycle transitions) | T057 (LockBanner UI) | T060 (WebSocket) |
| T052 (lock PATCH API) | T058 (DiffView UI) | T061 (DependencyGraph UI) |
| T053 (obsolete scan task) | T059 (QRAApprovalFlow UI) | |

### Phase 7 (US5): Parallel after T074
| Stream A | Stream B |
|----------|----------|
| T075 (library management API) | T077 (FMEDAWorksheet UI) |
| T076 (seed baseline library) | T078 (LibraryManager UI) |

---

## Implementation Strategy

### MVP Scope (Phase 1 + Phase 2 + Phase 3 only)

Deliver Phase 1–3 first to prove the core Spec-driven skeleton:
1. PM logs in (auth working)
2. PM completes AI wizard → project + document skeleton created
3. Role-based dashboard visible with document list

This MVP is independently demonstrable without AI RAG, cascade lock, or export features.

### Incremental Delivery Order

| Increment | Phases | Demonstrates |
|-----------|--------|-------------|
| MVP | 1 + 2 + 3 | Auth + wizard + BU-specific document skeleton |
| Sprint 2 | + 4 | AI compliance consulting with audit trail |
| Sprint 3 | + 5 | Cascade lock + QRA flow + dependency graph |
| Sprint 4 | + 6 | Audit export + CodeBeamer xlsx + traceability |
| Sprint 5 | + 7 + 8 | FMEDA automation + Git commit abstraction |
| Sprint 6 | + 9 | i18n, admin panel, E2E tests, performance |

---

## Format Validation

All tasks follow: `- [ ] T### [P?] [US?] Description with file path`

| Check | Result |
|-------|--------|
| All tasks have checkbox `- [ ]` | ✅ |
| All tasks have sequential T### ID | ✅ T001–T090 |
| User story phase tasks have [US] label | ✅ T028–T082 |
| Setup/Foundational/Polish tasks have NO [US] label | ✅ |
| [P] applied only to truly parallel tasks (different files, no incomplete deps) | ✅ |
| All tasks include explicit file paths | ✅ |
| Total tasks | **90** |
