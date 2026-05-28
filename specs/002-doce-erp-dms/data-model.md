# Data Model: DocERP Core Workflow and Traceability

## 1. Modeling Scope

This feature extends the current PostgreSQL schema to support:
- controlled document lifecycle and immutable revision history,
- dynamic attributes (EAV) scoped by standards and partitions,
- dependency health propagation and suspect resolution evidence,
- AI compliance review jobs and per-suggestion decisions,
- structured export jobs with validation outputs,
- append-only audit and user notification records.

All entities use UUID primary keys to satisfy constitution requirements.

## 2. Entity Definitions

## 2.1 Existing Entities Reused

### Project
- Purpose: compliance delivery scope.
- Key fields: id, name, bu_node_id, git_backend_type, created_at.
- Relationships: 1:N with Document.

### OrganisationNode (Partition)
- Purpose: hierarchical ownership and access boundary.
- Key fields: id, parent_id, name, level, bu_scope.
- Relationships: parent-child hierarchy; referenced by Project, Document, and events.

### User
- Purpose: actor identity and locale.
- Key fields: id, username, locale, is_local_admin.

### Document (extended)
- Purpose: active head record for a controlled artifact.
- Existing fields retained: id, project_id, bu_node_id, owner_id, title, content_markdown, lifecycle_state, current_version.
- New fields:
  - standards_scope: JSON or join-table driven reference list (implementation choice in migration task).
  - last_transition_at: timestamp for workflow reporting.
- Relationships:
  - 1:N with SpecItem.
  - 1:N with DocumentRevision (new).
  - 1:N with DocumentTransitionEvent (new).
  - 1:N with DocumentAttributeValue (new).

### SpecItem
- Purpose: decomposed requirement/design/test unit for traceability.
- Key fields: id, document_id, item_identifier, title, content_markdown.

### DependencyLink (extended)
- Purpose: typed relationship between source and target spec items.
- Existing fields retained: id, source_item_id, target_item_id, relationship_type.
- New fields:
  - health_status: enum VALID | SUSPECT.
  - last_upstream_revision: integer, nullable.
  - suspect_since: timestamp, nullable.
  - last_resolution_id: UUID, nullable.

### LockEvent
- Purpose: lock cascade history when upstream changes impact downstream.
- Reused for event lineage and dashboard aggregation.

## 2.2 New Entities

### DocumentRevision
- Purpose: immutable snapshot of document content and metadata per version.
- Fields:
  - id (UUID)
  - document_id (UUID FK -> Document)
  - version_number (int)
  - content_markdown (text)
  - lifecycle_state_at_snapshot (enum)
  - created_by_user_id (UUID FK -> User)
  - created_at (timestamp)
- Constraints:
  - UNIQUE(document_id, version_number)
  - version_number > 0

### DocumentTransitionEvent
- Purpose: auditable lifecycle transition history.
- Fields:
  - id
  - document_id
  - from_state (enum)
  - to_state (enum)
  - actor_user_id
  - rationale (text, nullable)
  - validation_result (json, nullable)
  - created_at

### Standard
- Purpose: catalog of compliance frameworks (ASPICE, ISO-26262, ISO-21434).
- Fields: id, code, name, version, is_active, created_at.
- Constraints: UNIQUE(code, version).

### StandardRequirement
- Purpose: individual clause/control belonging to a standard.
- Fields: id, standard_id, clause_key, title, description, is_mandatory.
- Constraints: UNIQUE(standard_id, clause_key).

### AttributeDefinition
- Purpose: dynamic metadata definition scoped by standard and partition.
- Fields:
  - id
  - key
  - label
  - data_type (enum STRING | INTEGER | BOOLEAN | ENUM | DATE)
  - is_required (bool)
  - standard_id (nullable FK)
  - partition_node_id (nullable FK -> OrganisationNode)
  - allowed_values_json (nullable)
  - validation_rule_json (nullable)
  - created_at
- Constraints:
  - UNIQUE(key, standard_id, partition_node_id)

### DocumentAttributeValue
- Purpose: value instance for a document revision and attribute definition.
- Fields:
  - id
  - document_id
  - revision_id (FK -> DocumentRevision)
  - attribute_definition_id
  - value_string (nullable)
  - value_integer (nullable)
  - value_boolean (nullable)
  - value_date (nullable)
  - created_at
- Constraints:
  - UNIQUE(revision_id, attribute_definition_id)
  - exactly one value column must be populated according to data_type.

### ComplianceRecord
- Purpose: requirement-level compliance status linked to evidence document revision.
- Fields:
  - id
  - document_id
  - revision_id
  - standard_requirement_id
  - status (enum PENDING | COMPLIANT | GAP | WAIVED)
  - evidence_note (nullable)
  - updated_by_user_id
  - updated_at
- Constraints:
  - UNIQUE(revision_id, standard_requirement_id)

### SuspectResolution
- Purpose: explicit closure record for SUSPECT dependencies.
- Fields:
  - id
  - dependency_link_id
  - resolution_type (enum UPDATED | NOT_IMPACTED | PENDING)
  - rationale (text)
  - resolved_by_user_id
  - resolved_at
  - upstream_revision_number
- Constraints:
  - rationale required when resolution_type = NOT_IMPACTED.

### AIReviewJob
- Purpose: durable async request for AI compliance review.
- Fields:
  - id
  - document_id
  - revision_id
  - requested_standards_json
  - status (enum QUEUED | RUNNING | PARTIAL | COMPLETED | FAILED | RETRYABLE)
  - requested_by_user_id
  - accepted_at
  - first_result_at (nullable)
  - completed_at (nullable)
  - error_code (nullable)
  - error_message (nullable)

### AIReviewFinding
- Purpose: clause-linked finding generated by AI review.
- Fields:
  - id
  - ai_review_job_id
  - standard_requirement_id (nullable when mapping failed)
  - severity (enum INFO | WARNING | MAJOR)
  - finding_text
  - evidence_gap_text (nullable)
  - created_at

### AISuggestionDecision
- Purpose: per-suggestion accept/reject audit record.
- Fields:
  - id
  - ai_review_finding_id
  - decision (enum ACCEPTED | REJECTED)
  - rationale (nullable for accepted, required for rejected)
  - decided_by_user_id
  - decided_at

### ExportJob
- Purpose: durable async audit export request.
- Fields:
  - id
  - project_id
  - mapping_profile
  - status (enum QUEUED | RUNNING | PARTIAL | COMPLETED | FAILED)
  - requested_by_user_id
  - requested_at
  - completed_at (nullable)
  - synced_at (nullable)

### ExportArtifact
- Purpose: generated package artifact metadata.
- Fields:
  - id
  - export_job_id
  - artifact_type (enum MANIFEST | DOCUMENT_BUNDLE | TRACEABILITY | COMPLIANCE | VALIDATION_REPORT)
  - storage_path
  - checksum_sha256
  - created_at

### ExportIssue
- Purpose: correction-oriented validation result.
- Fields:
  - id
  - export_job_id
  - issue_code
  - severity (enum ERROR | WARNING)
  - entity_ref
  - message
  - created_at

### AuditEvent
- Purpose: append-only immutable evidence for sensitive operations.
- Fields:
  - id
  - event_type
  - actor_user_id
  - partition_node_id (nullable)
  - entity_type
  - entity_id
  - payload_before_json (nullable)
  - payload_after_json (nullable)
  - occurred_at
- Constraints:
  - application and migration policy must block UPDATE/DELETE.

### Notification
- Purpose: owner-visible impact and workflow status messages.
- Fields:
  - id
  - recipient_user_id
  - channel (enum IN_APP | EMAIL)
  - category
  - title
  - body
  - related_entity_type
  - related_entity_id
  - is_read
  - created_at

## 3. Relationships

- Project 1:N Document.
- OrganisationNode 1:N Project and 1:N Document.
- Document 1:N DocumentRevision.
- Document 1:N SpecItem.
- SpecItem N:M SpecItem via DependencyLink.
- DependencyLink 1:N SuspectResolution.
- DocumentRevision 1:N DocumentAttributeValue.
- AttributeDefinition 1:N DocumentAttributeValue.
- Standard 1:N StandardRequirement.
- DocumentRevision N:M StandardRequirement via ComplianceRecord.
- AIReviewJob 1:N AIReviewFinding.
- AIReviewFinding 1:1 AISuggestionDecision (optional until decided).
- ExportJob 1:N ExportArtifact.
- ExportJob 1:N ExportIssue.

## 4. Validation Rules

- Document create requires project_id, owner_id, partition(bu_node_id), title, standards scope.
- Transition to REVIEW or APPROVED must pass required AttributeDefinition checks.
- APPROVED revisions are immutable; edits must create a new DRAFT revision.
- Dependency creation rejects self-link and circular chain.
- SUSPECT resolution must reference current upstream revision context.
- AI suggestion rejection requires rationale text.
- Export completion can be PARTIAL only if at least one artifact exists and ExportIssue records are present.
- Authorization checks apply to read/edit/review/export operations by role and partition scope.

## 5. State Transitions

## 5.1 Document Lifecycle

- DRAFT -> REVIEW: owner/editor action after validation success.
- REVIEW -> APPROVED: authorized reviewer action.
- REVIEW -> DRAFT: reviewer requests rework with rationale.
- APPROVED -> OBSOLETE: authorized action when superseded.
- APPROVED -> DRAFT: not a direct state change; system creates a new DocumentRevision with incremented version and DRAFT state.

## 5.2 Dependency Health

- VALID -> SUSPECT: triggered when upstream approved revision changes.
- SUSPECT -> VALID: resolved by UPDATED or NOT_IMPACTED decision.
- SUSPECT -> SUSPECT: remains pending when resolution_type = PENDING.

## 5.3 Async Jobs

### AIReviewJob
- QUEUED -> RUNNING -> COMPLETED
- QUEUED/RUNNING -> PARTIAL when external mapping is incomplete
- QUEUED/RUNNING -> RETRYABLE on temporary service outage
- RETRYABLE -> RUNNING on retry
- RUNNING -> FAILED on terminal error

### ExportJob
- QUEUED -> RUNNING -> COMPLETED
- RUNNING -> PARTIAL when package generated with validation issues
- RUNNING -> FAILED on terminal processing error

## 6. Indexing and Query Hotspots

- Document: indexes on project_id, lifecycle_state, bu_node_id, owner_id.
- DependencyLink: indexes on source_item_id, target_item_id, health_status.
- SuspectResolution: indexes on dependency_link_id, resolved_at.
- AIReviewJob: indexes on status, requested_at, document_id.
- ExportJob: indexes on status, requested_at, project_id.
- AuditEvent: composite index on entity_type + entity_id + occurred_at.
