# Async Event / Task Contract: DocERP

**Phase**: 1 — Design  
**Date**: 2026-04-29  
**Related**: [rest-api.md](./rest-api.md) | [data-model.md](../data-model.md) | [research.md](../research.md)

Async tasks are implemented with **Celery 5.x** using **Redis 7** as broker and result backend.  
Task names follow the convention `docerp.tasks.<module>.<task_name>`.

---

## Task: `docerp.tasks.cascade_lock.propagate_cascade_lock`

**Trigger**: `PUT /documents/{document_id}/content` — when upstream Spec saved by Architect.  
**Queue**: `cascade_lock`  
**Priority**: HIGH  
**Idempotent**: Yes (INSERT … ON CONFLICT DO NOTHING for lock records).

**Payload**
```json
{
  "upstream_document_id": "uuid",
  "upstream_version": 5,
  "triggered_by_user_id": "uuid",
  "bu_node_id": "uuid",
  "diff_content": "string"
}
```

**Execution steps**:
1. Acquire `pg_advisory_lock(hash(bu_node_id))`.
2. Query all documents directly linked to `upstream_document_id` via BLOCKING/BLOCKED_BY dependency links, within the same BU scope (`bu_node_id`).
3. For each dependent document with `lifecycle_state IN ('REVIEW', 'APPROVED')` and `lock_state = 'UNLOCKED'`:
   a. If Architect is mid-save race (FR-015c): defer lock until the document's `current_version` changes (schedule a `check_deferred_lock` subtask, delay 10 s, max 5 retries).  
   b. Otherwise: set `lock_state = 'LOCKED'`.
   c. Write a `lock_events` record with `diff_snapshot`.
   d. Dispatch in-app notification + email alert to document owner (FR-021).
4. Release advisory lock.

**Failure handling**: Celery retry with exponential back-off (max 3 retries, 60 s base). Dead-letter queue: `cascade_lock_dlq`. DLQ entries alert system admin.

---

## Task: `docerp.tasks.cascade_lock.check_deferred_lock`

**Trigger**: Spawned by `propagate_cascade_lock` when a deferred lock is needed (FR-015c).  
**Queue**: `cascade_lock`

**Payload**
```json
{
  "target_document_id": "uuid",
  "wait_for_version_gt": 5,
  "lock_event_payload": {}
}
```

**Execution**: Poll `documents.current_version > wait_for_version_gt`. If true, apply lock. If not, retry up to 5 times (10 s intervals). After 5 retries, apply lock immediately regardless.

---

## Task: `docerp.tasks.cycle_detection.detect_cycles_for_document`

**Trigger**: `POST /items/{item_id}/dependencies` — after any DependencyLink mutation (FR-015d).  
**Queue**: `dependency`  
**Priority**: NORMAL

**Payload**
```json
{ "document_id": "uuid", "changed_link_id": "uuid" }
```

**Execution steps**:
1. Load adjacency list for BLOCKING/BLOCKED_BY graph for the project; use Redis cache key `dep_graph:{project_id}` (TTL 60 s, invalidated on every link change).
2. Run DFS from `document_id` to detect cycles (Johnson's algorithm for all simple cycles, or standard DFS for first cycle detection).
3. If cycle found:
   a. Set `cycle_warning = TRUE` on the completing `dependency_links` row.
   b. Set `cycle_warning = TRUE` on all `spec_items` in the cycle.
   c. Dispatch in-app + email notifications to all document owners in the cycle (FR-015d).
4. Invalidate Redis cache.

---

## Task: `docerp.tasks.obsolete_scan.scan_downstream_on_obsolete`

**Trigger**: `POST /documents/{document_id}/lifecycle` with `target_state = OBSOLETE` (FR-039).  
**Queue**: `dependency`  
**Priority**: NORMAL

**Payload**
```json
{ "obsoleted_document_id": "uuid" }
```

**Execution steps**:
1. Find all `spec_items` belonging to `obsoleted_document_id`.
2. Find all `dependency_links` where `source_item_id IN (above items)` — all relationship types.
3. For each downstream `spec_item` found:
   a. Set `upstream_obsolete_warning = TRUE`.
   b. Dispatch in-app + email notification to downstream item owner.
   c. Write to `audit_trail`.

---

## Task: `docerp.tasks.export.generate_audit_package`

**Trigger**: `POST /projects/{project_id}/audit/export` (FR-024, FR-045).  
**Queue**: `export`  
**Priority**: NORMAL

**Payload**
```json
{
  "project_id": "uuid",
  "audit_package_id": "uuid",
  "standards_scope": ["ASPICE", "ISO-26262", "ISO-21434"],
  "triggered_by_user_id": "uuid"
}
```

**Execution steps**:
1. Run compliance check (same logic as `POST /audit/check`).
2. Fetch all Spec Items with their EAV attributes, ordered by document and position.
3. Load active `CodeBeamerSchemaDefinition`.
4. Generate `.xlsx` using `openpyxl` per the RD-03-010-09 column structure.
5. Run post-generation validation against schema — produce `validation_report` JSON.
6. Write files to `AUDIT_PACKAGE_STORAGE_PATH/{archive_name}/`.
7. Update `AuditPackage` DB record with `storage_path`, `compliance_check_result`, `validation_report`, `validation_passed`.
8. Dispatch completion notification to triggering user.

---

## Task: `docerp.tasks.wizard.expire_old_wizard_sessions`

**Trigger**: Celery beat — daily at 02:00 server time (FR-043: 90-day expiry).  
**Queue**: `maintenance`

**Execution**: Delete all `wizard_sessions` where `expires_at < NOW()` and `completed = FALSE`. Send email notification to affected users before deletion (1-day advance warning, scheduled at 01:00).

---

## Task: `docerp.tasks.maintenance.compute_storage_quota`

**Trigger**: Celery beat — daily at 03:00 server time (FR-045: storage quota monitoring).  
**Queue**: `maintenance`

**Execution**: Sum filesystem sizes of all Audit Package directories. Compare against `AUDIT_PACKAGE_VOLUME_GB * 0.80` threshold. If exceeded, create/update a `system_alerts` record and dispatch dashboard warning to all admin users.

---

## Redis Key Conventions

| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `dep_graph:{project_id}` | Cached adjacency list for cycle detection | 60 s |
| `wizard:{session_id}` | Wizard session hot-cache | 1 h |
| `lock_state:{document_id}` | Fast lock state read for export/commit gate check | 30 s |
| `ai_fallback_mode` | Global flag: LLM API reachability (FR-033b) | 30 s |
