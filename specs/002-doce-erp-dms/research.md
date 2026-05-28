# Research: DocERP Core Workflow and Traceability

## Scope

This research resolves planning decisions needed to implement the feature in the current repository while staying aligned with the constitution and existing backend architecture.

## Decision 1: Deliver backend-first vertical slices on the existing async stack

Decision: Implement lifecycle, traceability, AI review, and export as backend-first vertical slices using the current FastAPI + SQLAlchemy asyncio stack.

Rationale: The repository already has FastAPI entrypoint, async DB session wiring, migration baseline, and service-layer patterns. Backend-first delivery reduces integration risk and enables immediate contract testing.

Alternatives considered:
- Frontend-first implementation: rejected because frontend runtime stack is not initialized yet.
- Replatform to a new backend framework: rejected due unnecessary migration cost and delayed value delivery.

## Decision 2: Use explicit revision entities for immutable approved history

Decision: Add a DocumentRevision table and persist immutable snapshots for each approved revision; block direct edits on approved revisions and require new draft revision creation.

Rationale: FR-005 requires controlled revision behavior. Storing snapshots separately provides reliable auditability and supports downstream impact detection by revision number.

Alternatives considered:
- Version only on Document row: rejected because history reconstruction becomes fragile.
- Git-only history without DB revision records: rejected because API-level traceability and reporting require queryable structured revisions.

## Decision 3: Keep EAV as the extension mechanism for standards and partitions

Decision: Add AttributeDefinition and DocumentAttributeValue entities scoped by standard and partition, with required-flag validation at transition time.

Rationale: Constitution Principle IV requires dynamic extensibility without hardcoded standard-specific columns.

Alternatives considered:
- Add fixed columns per standard: rejected by constitution and poor scalability.
- Store all attributes in a single JSON column: rejected because validation, filtering, and export mapping become less reliable.

## Decision 4: Persist dependency health state and resolution evidence

Decision: Extend traceability with explicit health state (VALID/SUSPECT) and resolution events tied to actor, timestamp, rationale, and upstream revision context.

Rationale: FR-011 to FR-014 require deterministic suspect propagation, owner action tracking, and auditable resolution decisions.

Alternatives considered:
- Compute SUSPECT purely at query time: rejected because historical evidence and notifications would be inconsistent.
- Store resolution notes only in free text logs: rejected because machine-readable status and reporting are required.

## Decision 5: Implement durable async workflow for AI review and export jobs

Decision: Persist AIReviewJob and ExportJob tables with queue/status timestamps and retry metadata; expose polling APIs for job status.

Rationale: FR-020 and FR-023 require recoverable delayed/partial processing. Durable DB-backed jobs survive service restarts.

Alternatives considered:
- In-memory background task state only: rejected because state is lost on restart.
- Immediate synchronous processing: rejected due NFR latency targets and external dependency variability.

## Decision 6: Use append-only audit events with operation-level granularity

Decision: Introduce an AuditEvent table capturing actor, partition scope, object reference, before/after metadata, and event type for lifecycle, dependency, AI decision, and export actions.

Rationale: FR-015 and NFR-004 require immutable and queryable audit evidence across sensitive operations.

Alternatives considered:
- Rely on generic application logs only: rejected because logs are not sufficient as immutable domain evidence.
- Single coarse audit record per request: rejected because domain-level traceability requires finer event granularity.

## Decision 7: Standardize external interface on REST + OpenAPI contract

Decision: Define feature APIs in OpenAPI 3.1 under contracts/rest-api.yaml, including error models, async job states, and authorization requirements.

Rationale: Contract-first design enables parallel backend and frontend work and provides deterministic inputs for Phase 2 task generation.

Alternatives considered:
- Implicit contracts documented only in prose: rejected because ambiguity increases task breakdown risk.
- GraphQL adoption in this feature: rejected to keep scope consistent with current REST conventions.

## Decision 8: Export package format must be structured and validation-first

Decision: Export jobs generate a package manifest plus artifact files and validation issue report before handoff; synchronization to external governance platform remains one-way.

Rationale: Constitution Principle V and FR-022 to FR-024 require structured, auditable, and correction-friendly handoff.

Alternatives considered:
- Direct push without local validation output: rejected because users lose actionable correction guidance.
- Bidirectional synchronization: rejected because it exceeds current system boundary assumptions.
