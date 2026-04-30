# Data Model: DocERP — Spec-Driven Document Management System

**Phase**: 1 — Design  
**Date**: 2026-04-29  
**Related**: [plan.md](./plan.md) | [research.md](./research.md) | [spec.md](./spec.md)

---

## Core Design Principles

- All primary keys are **UUID v4** (constitution: UUID PKs).
- EAV hybrid model: universal typed columns + JSONB `extra_attributes` + `attribute_definitions` registry (R-001).
- Document lifecycle is a **strictly unidirectional state machine**: `DRAFT → REVIEW → APPROVED → OBSOLETE`. Backward transitions are never permitted (FR-013b, Constitution §Data Model). When QRA requests revision, `revision_requested = TRUE` is set on the current version; the owner creates a new version in `DRAFT` state.
- Lock semantics are **embedded in the lifecycle**: cascade locks may only apply to `REVIEW` or `APPROVED` documents; transitioning to `APPROVED` automatically clears any active lock.
- All timestamps are `TIMESTAMP WITH TIME ZONE` (UTC stored, displayed per user locale).

---

## Entity Definitions

### 1. `organisation_nodes`

Represents one node in the 5-level org hierarchy (FR-001).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `parent_id` | UUID | FK → organisation_nodes(id), nullable | null = Company root |
| `level` | SMALLINT | NOT NULL, CHECK (1–5) | 1=Company, 2=BU, 3=Process, 4=Department, 5=Sub-dept |
| `name` | VARCHAR(200) | NOT NULL | |
| `bu_scope` | UUID | FK → organisation_nodes(id), nullable | The BU ancestor; used for BU-scoped cascade lock (FR-041) |
| `applicable_standards` | JSONB | NOT NULL, DEFAULT '[]' | Array of {standard, level/asil/cal} |
| `template_configuration` | JSONB | NOT NULL, DEFAULT '{}' | BU-specific document template overrides |
| `created_at` | TIMESTAMPTZ | NOT NULL |  |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

**Indexes**: `parent_id`, `bu_scope`, `level`

---

### 2. `projects`

A project scoped to a BU, carrying compliance standards and role assignments (FR-003, FR-004).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `bu_node_id` | UUID | FK → organisation_nodes(id), NOT NULL | Must be level=2 (BU) |
| `name` | VARCHAR(300) | NOT NULL | |
| `aspice_level` | SMALLINT | nullable | 1–5 |
| `iso26262_asil` | VARCHAR(10) | nullable | NULL / A / B / C / D |
| `iso21434_cal` | VARCHAR(10) | nullable | NULL / CAL1–CAL4 |
| `git_backend_type` | VARCHAR(20) | NOT NULL, CHECK ('gerrit','github','gitlab') | |
| `git_backend_config` | JSONB | NOT NULL, DEFAULT '{}' | URL, credentials ref (never secrets in DB) |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'active' | active / archived |
| `created_by` | UUID | FK → users(id) | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

---

### 3. `users`

Siliconmotion user accounts — LDAP sourced or local admin (FR-038).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `ldap_dn` | VARCHAR(500) | UNIQUE, nullable | null = local account |
| `username` | VARCHAR(100) | NOT NULL, UNIQUE | |
| `email` | VARCHAR(300) | NOT NULL, UNIQUE | |
| `display_name` | VARCHAR(200) | NOT NULL | |
| `locale` | VARCHAR(10) | NOT NULL, DEFAULT 'zh-TW' | zh-TW or en (FR-040) |
| `is_local_admin` | BOOLEAN | NOT NULL, DEFAULT FALSE | Local fallback account flag |
| `password_hash` | VARCHAR(128) | nullable | bcrypt; only set for local admin |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `last_login_at` | TIMESTAMPTZ | nullable | |
| `auth_method_last` | VARCHAR(10) | nullable | 'ldap' or 'local' |

---

### 4. `roles` & `project_role_assignments`

RBAC model mapping users to roles within a project scope (FR-004).

**`roles`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `name` | VARCHAR(50) | NOT NULL, UNIQUE — e.g., 'PM', 'RD_FW', 'RD_HW', 'ARCHITECT', 'AUDITOR_QRA', 'ADMIN' |
| `permissions` | JSONB | Structured permission set |

**`project_role_assignments`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `project_id` | UUID | FK → projects(id) |
| `user_id` | UUID | FK → users(id) |
| `role_id` | UUID | FK → roles(id) |
| `org_node_id` | UUID | FK → organisation_nodes(id), nullable — scope restriction |
| `assigned_at` | TIMESTAMPTZ | |

---

### 5. `documents`

Core versioned document entity with embedded lifecycle state machine (FR-010–017, FR-039).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK | |
| `project_id` | UUID | FK → projects(id), NOT NULL | |
| `org_node_id` | UUID | FK → organisation_nodes(id), NOT NULL | Owning department/sub-dept |
| `document_type` | VARCHAR(20) | NOT NULL | 'MANUAL' / 'PROCEDURE' / 'SPEC' / 'FORM' / 'FMEDA' |
| `title` | VARCHAR(500) | NOT NULL | |
| `owner_id` | UUID | FK → users(id), NOT NULL | Responsible owner |
| `partition_agent` | VARCHAR(50) | nullable | 'SYS' / 'HW' / 'SWE' / 'SAFETY' / 'SECURITY' |
| `lifecycle_state` | VARCHAR(20) | NOT NULL, DEFAULT 'DRAFT' | 'DRAFT' / 'REVIEW' / 'APPROVED' / 'OBSOLETE' |
| `lock_state` | VARCHAR(30) | NOT NULL, DEFAULT 'UNLOCKED' | 'UNLOCKED' / 'LOCKED' / 'PENDING_QRA' |
| `current_version` | INTEGER | NOT NULL, DEFAULT 1 | Optimistic locking counter (R-003) |
| `is_safety_critical` | BOOLEAN | NOT NULL, DEFAULT FALSE | True if ASIL-B+ or high CAL (FR-014) |
| `revision_requested` | BOOLEAN | NOT NULL, DEFAULT FALSE | Set TRUE when QRA requests revision without backward lifecycle transition (FR-013b) |
| `bu_node_id` | UUID | FK → organisation_nodes(id), NOT NULL | BU ancestor for cascade lock scoping (FR-041) |
| `schema_version` | INTEGER | NOT NULL, DEFAULT 1 | EAV schema version (FR-035, R-001) |
| `git_commit_sha` | VARCHAR(64) | nullable | Last committed SHA |
| `git_path` | VARCHAR(1000) | nullable | Path in the Git repository |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

**State Machine Transitions**:
```
DRAFT → REVIEW      (owner submits for review)
REVIEW → APPROVED   (reviewer approves; clears any LOCKED state)
REVIEW → DRAFT      (reviewer rejects)
APPROVED → REVIEW   (change initiated; triggers cascade lock evaluation)
APPROVED → OBSOLETE (deprecated; triggers FR-039 downstream warning scan)
```

**Lock Transitions** (only applies when lifecycle_state = REVIEW or APPROVED):
```
UNLOCKED → LOCKED             (cascade lock triggered by upstream Spec save)
LOCKED → PENDING_QRA          (safety-critical: owner marks "Reviewed & Updated")
LOCKED → UNLOCKED             (standard: owner marks "Reviewed & Updated" → transitions to APPROVED)
PENDING_QRA → UNLOCKED/APPROVED (QRA approves or Emergency Override — FR-014b)
```

**Indexes**: `project_id`, `org_node_id`, `owner_id`, `lifecycle_state`, `lock_state`, `bu_node_id`

---

### 6. `document_versions`

Full version history for rollback and diff (FR-011, FR-017).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `document_id` | UUID | FK → documents(id) |
| `version_number` | INTEGER | NOT NULL |
| `content_markdown` | TEXT | NOT NULL — full Markdown content snapshot |
| `changed_by` | UUID | FK → users(id) |
| `change_summary` | TEXT | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Index**: `(document_id, version_number)` UNIQUE

---

### 7. `attribute_definitions`

EAV schema registry — one row per attribute type per document type (FR-034, FR-035, R-001).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `document_type` | VARCHAR(20) | NOT NULL — matches documents.document_type |
| `attribute_key` | VARCHAR(100) | NOT NULL |
| `display_name_en` | VARCHAR(200) | NOT NULL |
| `display_name_zh` | VARCHAR(200) | NOT NULL |
| `value_type` | VARCHAR(20) | NOT NULL — 'text' / 'int' / 'float' / 'bool' / 'uuid_ref' / 'json' |
| `is_required` | BOOLEAN | NOT NULL, DEFAULT FALSE |
| `validation_rule` | JSONB | nullable — regex, min/max, allowed_values |
| `standard_clause_ref` | VARCHAR(200) | nullable — e.g., 'ISO-26262:6:7.4.2' |
| `schema_version` | INTEGER | NOT NULL, DEFAULT 1 |
| `created_at` | TIMESTAMPTZ | |

**Unique constraint**: `(document_type, attribute_key, schema_version)`

---

### 8. `spec_items`

Atomic requirement/design/test/evidence entries within a document (FR-034).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `document_id` | UUID | FK → documents(id) |
| `item_type` | VARCHAR(20) | 'REQUIREMENT' / 'DESIGN' / 'TEST_CASE' / 'EVIDENCE' |
| `item_id_display` | VARCHAR(100) | Human-readable ID (e.g., SM-001, HW-REQ-042) |
| `title` | VARCHAR(500) | NOT NULL |
| `content_markdown` | TEXT | nullable |
| `clause_reference` | VARCHAR(300) | Standard clause this item satisfies (FR-034a) |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'DRAFT' |
| `safety_related` | BOOLEAN | NOT NULL, DEFAULT FALSE |
| `asil_level` | VARCHAR(5) | nullable |
| `owner_id` | UUID | FK → users(id) |
| `position_order` | INTEGER | NOT NULL, DEFAULT 0 — display ordering within document |
| `extra_attributes` | JSONB | NOT NULL, DEFAULT '{}' — EAV payload (FDTI, FRTI, FHTI, DC, etc.) |
| `upstream_obsolete_warning` | BOOLEAN | NOT NULL, DEFAULT FALSE — FR-039 |
| `cycle_warning` | BOOLEAN | NOT NULL, DEFAULT FALSE — FR-015d |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Indexes**: `document_id`, `owner_id`, `item_type`, `upstream_obsolete_warning`, `cycle_warning`

---

### 9. `dependency_links`

Typed relationships between Spec Items — the dependency graph edges (FR-018, FR-019).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `source_item_id` | UUID | FK → spec_items(id) |
| `target_item_id` | UUID | FK → spec_items(id) |
| `relationship_type` | VARCHAR(20) | NOT NULL — 'BLOCKING' / 'BLOCKED_BY' / 'RELATED' |
| `traceability_state` | VARCHAR(10) | NOT NULL, DEFAULT 'VALID' — 'VALID' / 'SUSPECT' (FR-019b, Constitution §II) |
| `cycle_warning` | BOOLEAN | NOT NULL, DEFAULT FALSE — FR-015d |
| `created_by` | UUID | FK → users(id) |
| `created_at` | TIMESTAMPTZ | |

**Unique constraint**: `(source_item_id, target_item_id, relationship_type)`  
**Indexes**: `source_item_id`, `target_item_id`, `relationship_type`, `cycle_warning`, `traceability_state`

**SUSPECT Transition Rule** (FR-019b): On every document save, a background task scans all `dependency_links` where `source_item_id` belongs to a Spec Item in the saved document and `relationship_type IN ('BLOCKING', 'BLOCKED_BY')`, and sets `traceability_state = 'SUSPECT'`. Reset to `'VALID'` occurs when the downstream document owner completes "Reviewed & Updated" (FR-013/FR-014).

---

### 10. `lock_events`

Audit log of every cascade lock trigger (FR-015, FR-014b).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `upstream_document_id` | UUID | FK → documents(id) — the Spec that changed |
| `upstream_version` | INTEGER | Version at time of lock trigger |
| `locked_document_id` | UUID | FK → documents(id) — the downstream document locked |
| `lock_type` | VARCHAR(20) | 'CASCADE' / 'EMERGENCY_OVERRIDE' |
| `triggered_by` | UUID | FK → users(id) |
| `triggered_at` | TIMESTAMPTZ | NOT NULL |
| `unlocked_by` | UUID | FK → users(id), nullable |
| `unlocked_at` | TIMESTAMPTZ | nullable |
| `unlock_type` | VARCHAR(30) | nullable — 'SELF_APPROVED' / 'QRA_APPROVED' / 'EMERGENCY_OVERRIDE' |
| `override_reason` | TEXT | nullable — required when lock_type = EMERGENCY_OVERRIDE (FR-014b) |
| `diff_snapshot` | TEXT | nullable — diff content shown to owner (FR-017) |

---

### 11. `ai_suggestions`

AI-generated content suggestions with Accept/Reject tracking (FR-007, FR-008).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `spec_item_id` | UUID | FK → spec_items(id) |
| `document_id` | UUID | FK → documents(id) |
| `suggested_content` | TEXT | NOT NULL |
| `clause_reference` | VARCHAR(300) | Standard clause referenced (FR-009) |
| `gap_type` | VARCHAR(50) | e.g., 'MISSING_SECTION' / 'INCOMPLETE_CLAUSE' / 'INVALID_VALUE' |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'PENDING' — 'PENDING' / 'ACCEPTED' / 'REJECTED' |
| `reviewed_by` | UUID | FK → users(id), nullable |
| `reviewed_at` | TIMESTAMPTZ | nullable |
| `fallback_mode` | BOOLEAN | NOT NULL, DEFAULT FALSE — True if generated from local rule set (FR-033b) |
| `created_at` | TIMESTAMPTZ | |

---

### 12. `fmeda_worksheets`

ISO-26262 FMEDA analysis artifact (FR-027–FR-030, FR-042).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `document_id` | UUID | FK → documents(id) |
| `component_name` | VARCHAR(300) | NOT NULL |
| `asil_target` | VARCHAR(5) | NOT NULL |
| `library_version_used` | INTEGER | FK → failure_mode_library_versions(id) — FR-042e |
| `spfm` | NUMERIC(6,4) | computed |
| `lfm` | NUMERIC(6,4) | computed |
| `pmhf` | NUMERIC(10,4) | computed (FIT units) |
| `spfm_threshold_pass` | BOOLEAN | nullable |
| `lfm_threshold_pass` | BOOLEAN | nullable |
| `pmhf_threshold_pass` | BOOLEAN | nullable |
| `worksheet_data` | JSONB | NOT NULL — per-failure-mode rows with λ, DC, FDTI, FRTI, FHTI values |
| `calculated_at` | TIMESTAMPTZ | |

---

### 13. `failure_mode_library_entries` & `failure_mode_library_versions`

Versioned FMEDA failure mode library (FR-042).

**`failure_mode_library_versions`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL | PK (integer for lightweight FK references) |
| `version_label` | VARCHAR(50) | e.g., '1.0.0', '1.1.0-custom' |
| `is_baseline` | BOOLEAN | True = shipped with DocERP installation |
| `created_by` | UUID | FK → users(id) |
| `created_at` | TIMESTAMPTZ | |

**`failure_mode_library_entries`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `library_version_id` | INTEGER | FK → failure_mode_library_versions(id) |
| `component_type` | VARCHAR(200) | NOT NULL — e.g., 'MOSFET', 'SRAM', 'OSCILLATOR' |
| `failure_mode` | VARCHAR(300) | NOT NULL |
| `failure_rate_lambda` | NUMERIC(12,6) | NOT NULL — in FIT (failures per 10^9 hours) |
| `failure_mode_distribution` | JSONB | NOT NULL — {mode_fraction: float} |
| `diagnostic_coverage_default` | NUMERIC(5,4) | nullable |
| `is_custom` | BOOLEAN | NOT NULL, DEFAULT FALSE |
| `created_by` | UUID | FK → users(id) |
| `created_at` | TIMESTAMPTZ | |

---

### 14. `audit_packages`

Point-in-time export artifacts (FR-045).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `project_id` | UUID | FK → projects(id) |
| `archive_name` | VARCHAR(500) | NOT NULL — follows FR-045 naming convention |
| `storage_path` | VARCHAR(1000) | NOT NULL — absolute on-premise filesystem path |
| `standards_scope` | JSONB | NOT NULL — e.g., ['ASPICE', 'ISO-26262', 'ISO-21434'] |
| `triggered_by` | UUID | FK → users(id) |
| `triggered_at` | TIMESTAMPTZ | NOT NULL |
| `compliance_check_result` | JSONB | NOT NULL — gap summary |
| `validation_report` | JSONB | nullable — CodeBeamer schema issues (FR-044) |
| `validation_passed` | BOOLEAN | NOT NULL |

---

### 15. `codebeamer_schema_definitions`

Admin-managed CodeBeamer column schema for export validation (FR-026, FR-044).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `schema_version_label` | VARCHAR(50) | NOT NULL — e.g., 'CB-2024.1' |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT FALSE — one active at a time |
| `column_definitions` | JSONB | NOT NULL — ordered array of {column_name, expected_type, required, order_index} |
| `updated_by` | UUID | FK → users(id) |
| `updated_at` | TIMESTAMPTZ | |

---

### 16. `wizard_sessions`

AI onboarding wizard step-level auto-save (FR-043).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `user_id` | UUID | FK → users(id), NOT NULL |
| `project_id` | UUID | FK → projects(id), nullable — null until wizard completes |
| `current_step` | SMALLINT | NOT NULL, DEFAULT 1 |
| `answers` | JSONB | NOT NULL, DEFAULT '{}' — step → answer map |
| `started_at` | TIMESTAMPTZ | NOT NULL |
| `last_updated_at` | TIMESTAMPTZ | NOT NULL |
| `expires_at` | TIMESTAMPTZ | NOT NULL — started_at + 90 days (FR-043) |
| `completed` | BOOLEAN | NOT NULL, DEFAULT FALSE |

---

### 17. `notifications`

In-app notification store (FR-021, FR-014, FR-015d, FR-039).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `recipient_id` | UUID | FK → users(id) |
| `notification_type` | VARCHAR(50) | 'CASCADE_LOCK' / 'QRA_PENDING' / 'CYCLE_WARNING' / 'OBSOLETE_WARNING' / 'EMERGENCY_OVERRIDE' / etc. |
| `title` | TEXT | NOT NULL |
| `body` | TEXT | NOT NULL |
| `reference_id` | UUID | nullable — related document/item/event ID |
| `is_read` | BOOLEAN | NOT NULL, DEFAULT FALSE |
| `created_at` | TIMESTAMPTZ | NOT NULL |

---

### 18. `audit_trail`

Comprehensive system-wide audit log (FR-008, FR-014b, FR-038, FR-042d).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `actor_id` | UUID | FK → users(id) |
| `action_type` | VARCHAR(80) | NOT NULL — e.g., 'AI_SUGGESTION_ACCEPTED', 'EMERGENCY_OVERRIDE', 'LOCAL_AUTH_LOGIN', 'FMEDA_LIBRARY_MODIFIED' |
| `entity_type` | VARCHAR(50) | e.g., 'DOCUMENT', 'SPEC_ITEM', 'AI_SUGGESTION' |
| `entity_id` | UUID | nullable |
| `before_state` | JSONB | nullable |
| `after_state` | JSONB | nullable |
| `metadata` | JSONB | nullable — additional context (reason, override notes, etc.) |
| `occurred_at` | TIMESTAMPTZ | NOT NULL |

**Partition**: Consider monthly range partitioning on `occurred_at` for long-term performance.

---

## Entity Relationship Summary

```
organisation_nodes (5-level tree)
  └── projects (scoped to BU node)
        ├── project_role_assignments → users → roles
        └── documents (owned by org node, lifecycle state machine)
              ├── document_versions (full history snapshots)
              ├── spec_items (atomic items within a doc)
              │     ├── attribute_definitions (EAV schema registry per doc type)
              │     ├── dependency_links (typed edges: BLOCKING / BLOCKED_BY / RELATED)
              │     └── ai_suggestions (Accept/Reject with audit trail)
              └── fmeda_worksheets (ISO-26262 FMEDA, linked to failure_mode_library)

lock_events (cascade lock audit, linked to upstream + downstream documents)
audit_packages (point-in-time compliance exports per project)
codebeamer_schema_definitions (admin-managed xlsx column schema)
wizard_sessions (per-user AI wizard auto-save)
notifications (in-app notification delivery)
audit_trail (immutable system-wide event log)
failure_mode_library_versions + failure_mode_library_entries (FMEDA baseline + custom)
```

---

## State Transition Validation Rules

### Document Lifecycle (`lifecycle_state`)

| From | To | Allowed Actors | Side Effects |
|------|----|----------------|--------------|
| `DRAFT` | `REVIEW` | Owner | — |
| `REVIEW` | `APPROVED` | Reviewer / QRA (safety-critical) | Auto-clears LOCKED or PENDING_QRA lock state |
| `REVIEW` | `DRAFT` | Reviewer | — |
| `APPROVED` | `REVIEW` | Owner | Eligible for cascade lock (FR-015) |
| `APPROVED` | `OBSOLETE` | Owner / PM | Triggers FR-039 downstream warning scan |

### Lock State (`lock_state`)

| From | To | Trigger | Constraint |
|------|----|---------|------------|
| `UNLOCKED` | `LOCKED` | Cascade lock Celery task (R-002) | lifecycle must be REVIEW or APPROVED |
| `LOCKED` | `UNLOCKED` | Owner "Reviewed & Updated" (standard doc) → auto → APPROVED | is_safety_critical = FALSE |
| `LOCKED` | `PENDING_QRA` | Owner "Reviewed & Updated" (safety-critical doc) | is_safety_critical = TRUE |
| `PENDING_QRA` | `UNLOCKED` | QRA approval → auto → APPROVED | QRA role required |
| `PENDING_QRA` | `UNLOCKED` | Emergency Override (PM / Dept Manager) | Logged in audit_trail + LockEvent (FR-014b) |
