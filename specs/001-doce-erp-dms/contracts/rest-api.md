# REST API Contract: DocERP

**Phase**: 1 — Design  
**Date**: 2026-04-29  
**Related**: [data-model.md](../data-model.md) | [research.md](../research.md)

Base URL: `/api/v1`  
Auth: Bearer JWT (FR-038). All endpoints require authentication unless noted.  
Content-Type: `application/json`  
Errors follow RFC 7807 Problem Details: `{ type, title, status, detail, instance }`.

---

## Authentication

### `POST /auth/login`

Attempt LDAP bind; fall back to local account if LDAP unreachable (FR-038).

**Request**
```json
{ "username": "string", "password": "string" }
```
**Response 200**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600,
  "auth_method": "ldap | local",
  "user": { "id": "uuid", "username": "string", "display_name": "string", "locale": "zh-TW | en" }
}
```
**Response 401**: Invalid credentials.  
**Side effect**: If `auth_method = local`, writes `audit_trail` entry + dispatches admin security alert.

---

## Organisation & Projects

### `GET /orgs`
Returns the full org hierarchy tree as a nested JSON structure.

### `POST /projects`
Create a new project within a BU node.

**Request**
```json
{
  "bu_node_id": "uuid",
  "name": "string",
  "aspice_level": 2,
  "iso26262_asil": "B",
  "iso21434_cal": null,
  "git_backend_type": "gerrit | github | gitlab",
  "git_backend_config": {}
}
```
**Response 201**: Created project object.

### `GET /projects/{project_id}`
### `PATCH /projects/{project_id}`

---

## Documents

### `POST /projects/{project_id}/documents`
Create a new document within a project.

**Request**
```json
{
  "org_node_id": "uuid",
  "document_type": "SPEC | MANUAL | PROCEDURE | FORM | FMEDA",
  "title": "string",
  "owner_id": "uuid",
  "partition_agent": "SYS | HW | SWE | SAFETY | SECURITY | null",
  "is_safety_critical": false
}
```
**Response 201**: Document object including `lifecycle_state: DRAFT`, `lock_state: UNLOCKED`.

### `GET /projects/{project_id}/documents`
Query params: `lifecycle_state`, `lock_state`, `document_type`, `owner_id`, `page`, `per_page`.

### `GET /documents/{document_id}`
Returns document metadata + current version content.

### `PUT /documents/{document_id}/content`
Save document content. Implements optimistic locking (R-003).

**Request**
```json
{
  "version": 5,
  "content_markdown": "string",
  "change_summary": "string"
}
```
**Response 200**: Updated document with new `current_version`.  
**Response 409 Conflict**: Version mismatch — concurrent edit detected.
```json
{
  "type": "/errors/version-conflict",
  "title": "Version Conflict",
  "status": 409,
  "detail": "Document was modified by another user.",
  "current_version": 6,
  "base_content": "string",
  "their_changes": "string",
  "your_changes": "string"
}
```

### `POST /documents/{document_id}/lifecycle`
Transition lifecycle state.

**Request**
```json
{ "target_state": "REVIEW | APPROVED | DRAFT | OBSOLETE", "comment": "string" }
```
**Response 200**: Updated document.  
**Response 422**: Invalid transition.  
**Side effects**:
- `→ APPROVED`: clears any active lock, writes `lock_event` if applicable.
- `→ OBSOLETE`: enqueues `obsolete_scan` Celery task (FR-039).

### `POST /documents/{document_id}/lock/review`
Owner marks document as "Reviewed & Updated" (FR-013, FR-014).

**Response 200**:
- Standard doc → `lock_state: UNLOCKED`, `lifecycle_state: APPROVED`.
- Safety-critical → `lock_state: PENDING_QRA`, notification dispatched to QRA.

### `POST /documents/{document_id}/lock/qra-approve`
QRA auditor approves unlock (FR-014).

**Request**: `{ "comment": "string" }`  
**Response 200**: `lock_state: UNLOCKED`, `lifecycle_state: APPROVED`.

### `POST /documents/{document_id}/lock/emergency-override`
PM / Dept Manager force-unlock (FR-014b).

**Request**: `{ "reason": "string" }` (reason is mandatory)  
**Response 200**: Lock cleared. Writes full `lock_events` + `audit_trail` record. Admin notified.

### `GET /documents/{document_id}/versions`
List all versions in reverse-chronological order.

### `GET /documents/{document_id}/versions/{version_number}`
Returns the content snapshot + metadata for a specific version.

### `GET /documents/{document_id}/diff/{from_version}/{to_version}`
Returns a unified diff between two versions (used for Cascade Lock diff view, FR-017).

---

## Spec Items & Dependencies

### `POST /documents/{document_id}/items`
Create a Spec Item.

**Request**
```json
{
  "item_type": "REQUIREMENT | DESIGN | TEST_CASE | EVIDENCE",
  "item_id_display": "SM-001",
  "title": "string",
  "content_markdown": "string",
  "clause_reference": "ISO-26262:6:7.4.2",
  "safety_related": true,
  "asil_level": "B",
  "extra_attributes": {}
}
```
**Response 201**: Created SpecItem.

### `GET /documents/{document_id}/items`
### `PUT /items/{item_id}`
### `DELETE /items/{item_id}`

### `POST /items/{item_id}/dependencies`
Add a dependency link (FR-018, FR-015d — async cycle check after save).

**Request**
```json
{
  "target_item_id": "uuid",
  "relationship_type": "BLOCKING | BLOCKED_BY | RELATED"
}
```
**Response 201**: Created `DependencyLink`.  
**Side effect**: Enqueues `detect_cycles_for_document` Celery task.

### `DELETE /dependencies/{link_id}`

### `GET /projects/{project_id}/dependency-graph`
Returns the full dependency graph as adjacency list.

```json
{
  "nodes": [{ "id": "uuid", "label": "string", "doc_id": "uuid", "cycle_warning": false }],
  "edges": [{ "source": "uuid", "target": "uuid", "type": "BLOCKING | BLOCKED_BY | RELATED", "cycle_warning": false }]
}
```

---

## Traceability Matrix

### `GET /projects/{project_id}/traceability-matrix`
Returns requirement → design → test → evidence mapping (FR-022).

Query params: `standard` (ASPICE | ISO-26262 | ISO-21434), `format` (json | xlsx).

---

## AI Consultant & Wizard

### `POST /documents/{document_id}/ai/consult`
Invoke AI consultant for a document (FR-007, FR-009, FR-033b).

**Request**
```json
{ "target_item_ids": ["uuid"] }
```
**Response 200**
```json
{
  "suggestions": [
    {
      "id": "uuid",
      "spec_item_id": "uuid",
      "suggested_content": "string",
      "clause_reference": "ISO-26262:6:7.4.2",
      "gap_type": "MISSING_SECTION",
      "fallback_mode": false
    }
  ],
  "fallback_mode": false
}
```

### `POST /ai/suggestions/{suggestion_id}/accept`
Accept a suggestion — inserts content into Spec Item + writes audit trail (FR-008).

### `POST /ai/suggestions/{suggestion_id}/reject`
Reject a suggestion — no document change.

### `POST /wizard/sessions`
Start or resume a wizard session (FR-043).

**Request**: `{ "project_id": "uuid | null" }`  
**Response 200**: `{ "session_id": "uuid", "current_step": int, "answers": {}, "expires_at": "datetime" }`

### `PUT /wizard/sessions/{session_id}/steps/{step_number}`
Save a wizard step answer (auto-save).

**Request**: `{ "answer": {} }`  
**Response 200**: Updated session.

### `POST /wizard/sessions/{session_id}/complete`
Complete the wizard and generate the document framework.

**Response 201**: Created project + initial document set.

### `DELETE /wizard/sessions/{session_id}`
"Start Over" — deletes the session (FR-043).

---

## Audit & Compliance Export

### `POST /projects/{project_id}/audit/check`
Run compliance check (FR-023).

**Response 200**
```json
{
  "gaps": [
    { "document_id": "uuid", "item_id": "uuid", "standard": "ISO-26262", "clause": "6.7.4.2", "gap_description": "string" }
  ],
  "summary": { "total_gaps": 12, "critical": 3, "warnings": 9 }
}
```

### `POST /projects/{project_id}/audit/export`
Generate audit package + xlsx export (FR-024, FR-045).

**Request**: `{ "standards_scope": ["ASPICE", "ISO-26262", "ISO-21434"] }`  
**Response 202**: `{ "audit_package_id": "uuid", "status": "generating" }`  
Poll `GET /audit-packages/{id}` for completion.

### `GET /audit-packages/{audit_package_id}`
Returns package status + download URL when ready.

### `GET /audit-packages/{audit_package_id}/download`
Stream the `.xlsx` file.

### `GET /audit-packages/{audit_package_id}/validation-report`
Returns the Potential Import Issues report (FR-044).

### `GET /projects/{project_id}/audit-packages`
List all historical audit packages for the project (FR-045).

---

## FMEDA

### `POST /documents/{document_id}/fmeda`
Create or update a FMEDA worksheet (FR-027).

**Request**
```json
{
  "component_name": "string",
  "asil_target": "B",
  "failure_mode_rows": [
    { "library_entry_id": "uuid", "failure_mode": "string", "lambda_override": null, "dc_override": null }
  ]
}
```

### `POST /fmeda/{worksheet_id}/calculate`
Trigger SPFM / LFM / PMHF calculation (FR-028).

**Response 200**
```json
{
  "spfm": 0.9823,
  "lfm": 0.9501,
  "pmhf": 12.4,
  "spfm_threshold_pass": true,
  "lfm_threshold_pass": true,
  "pmhf_threshold_pass": false,
  "library_version_used": 2
}
```

### `GET /fmeda/{worksheet_id}/export`
Download CodeBeamer-compatible FMEDA xlsx (FR-030).

### `GET /fmeda/library`
List failure mode library entries.

### `POST /fmeda/library`
Add custom library entry (admin only, FR-042b).

### `PUT /fmeda/library/{entry_id}`
### `DELETE /fmeda/library/{entry_id}`

### `POST /fmeda/library/import`
Bulk import via Excel template (FR-042c). `multipart/form-data`.

---

## Git Commit Abstraction

### `POST /documents/{document_id}/git/commit`
Commit document via DocERP Git abstraction (FR-031).

**Request**: `{ "commit_message": "string" }`  
**Response 200**: `{ "sha": "string", "backend": "gerrit | github | gitlab" }`  
**Response 423 Locked**: Document is in LOCKED or PENDING_QRA state (FR-016).

---

## Notifications

### `GET /notifications`
List in-app notifications for the current user.

Query params: `unread_only=true`, `page`, `per_page`.

### `POST /notifications/{notification_id}/read`
Mark as read.

### WebSocket: `WS /ws/notifications`
Real-time notification stream for the authenticated user. Sends JSON events:
```json
{ "type": "CASCADE_LOCK | QRA_PENDING | CYCLE_WARNING | OBSOLETE_WARNING", "payload": {} }
```
