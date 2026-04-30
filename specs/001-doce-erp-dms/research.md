# Research: DocERP — Spec-Driven Document Management System

**Phase**: 0 — Research  
**Date**: 2026-04-29  
**Related**: [plan.md](./plan.md) | [spec.md](./spec.md)

---

## R-001: EAV Architecture in PostgreSQL for Incremental Schema Evolution

**Decision**: Use a hybrid EAV model — fixed columns for universal first-class attributes (id, document_id, name, value_text, value_int, value_float, value_json, created_at) with a separate `attribute_definitions` table per document type and a `schema_version` integer column per document.

**Rationale**: Pure EAV (all attributes as rows) is query-inefficient for complex reporting and traceability matrix generation. JSONB columns for the EAV payload combined with a typed `attribute_definitions` registry gives the flexibility of EAV (FR-035: incremental schema evolution) while allowing PostgreSQL index-accelerated queries on known fields. The `schema_version` enables migration without altering existing rows — new attributes are nullable with defaults, old records simply lack optional new keys.

**Alternatives considered**:
- Pure relational fixed schema: Rejected. Cannot accommodate A-008 (FW/SW/Architect attribute sets TBD) without table migrations that risk breaking existing records.
- JSONB-only (schemaless): Rejected. Loss of type validation for safety-critical attributes (FDTI, FRTI, FHTI, Diagnostic Coverage) — constitution Principle IV requires typed validation by partition Agents.
- TimescaleDB / MongoDB: Rejected. Constitution mandates PostgreSQL for ACID + integrity. No justification for adding a second datastore.

---

## R-002: Cascade Lock Atomicity Under Concurrent Load (FR-015, FR-041)

**Decision**: Implement cascade lock propagation as a Celery task with PostgreSQL advisory locks per BU scope. When the Architect's Spec is saved, the HTTP handler enqueues a `cascade_lock_bu_{bu_id}` Celery task. The Celery worker acquires a `pg_try_advisory_lock(bu_id)` before writing lock records, ensuring BU-scoped atomicity without cross-BU contention.

**Rationale**: FR-015 prohibits partial lock states. FR-041 mandates BU-scoped independence. PostgreSQL advisory locks are lightweight (no row contention), scoped by integer key (BU UUID → int hash), and automatically released on transaction commit. Celery provides at-least-once delivery with Redis as broker; idempotent lock writes (INSERT … ON CONFLICT DO NOTHING) prevent double-lock issues.

**Alternatives considered**:
- Synchronous in-request lock propagation: Rejected. Under load with many dependent documents, this would exceed HTTP timeout thresholds and violate SC-003 (< 3 s) due to cascading DB writes.
- Distributed lock via Redis (Redlock): Rejected. Adds a second lock coordination system alongside Celery; Redlock has known failure modes under Redis partition. PostgreSQL advisory locks are already in the transaction stack.
- Row-level SELECT FOR UPDATE on all dependent documents: Rejected. Would serialise all document saves across the entire system, not just within a BU — violates FR-041 independence guarantee.

---

## R-003: Optimistic Locking with Three-Way Merge (FR-015b)

**Decision**: Use a `document_version` integer counter (incremented on every save). On save, the client passes the `version` it read. The backend performs `UPDATE ... WHERE id = ? AND version = ?`; if 0 rows updated, a 409 Conflict is returned with the current server version and a three-way diff payload (base → my changes, base → their changes). The frontend renders this as a merge editor.

**Rationale**: Optimistic locking avoids pessimistic lock overhead for the common case (no conflict). The three-way diff approach (GNU diff3 algorithm applied to Markdown sections) is standard in document collaboration tools (analogous to Git merge). Human-only merge enforcement (FR-015b: "system MUST NOT auto-merge") requires the server to return both change-sets and the client to enforce the merge decision.

**Alternatives considered**:
- Last-Write-Wins: Rejected. Silently destroys concurrent changes — catastrophic for safety-critical compliance documents.
- Operational Transformation (OT) / CRDT: Rejected. Engineering complexity is disproportionate for a document whose sections are safety-critical and must never be auto-merged (FR-015b constraint).

---

## R-004: Async Circular Dependency Detection (FR-015d)

**Decision**: After any `DependencyLink` create/update, enqueue a Celery task `detect_cycles_for_document(doc_id)`. The worker runs a DFS over the Blocking/Blocked-By subgraph starting from the affected document using an adjacency list cached in Redis (TTL 60 s, invalidated on any link change). On cycle detection, the completing link is flagged `cycle_warning=True` and in-app + email notifications are dispatched to all cycle participants.

**Rationale**: Synchronous cycle detection (rejected per clarification Q7/FR-015d) would block the user's save action. Redis-cached adjacency list limits DB round-trips to invalidation events only. DFS on a bounded document graph (100s, not millions of nodes) completes in < 100 ms. The `cycle_warning` flag on the link persists until a human resolves it, satisfying the "Circular Dependency Warning in dependency graph" requirement.

**Alternatives considered**:
- Real-time rejection on link creation: Rejected by user in clarification Q2 (FR-015d requires async with warning, not rejection).
- Full-graph recompute on every link change: Rejected. With 100+ concurrent users, this creates contention; incremental DFS from the affected node is sufficient and far cheaper.

---

## R-005: RAG Pipeline for AI Compliance Consultant (FR-007, FR-009, FR-033b)

**Decision**: Use LangChain with a local vector store (pgvector extension on existing PostgreSQL) to embed ASPICE 3.1, ISO-26262, and ISO-21434 reference texts (licensed). Each AI query extracts the relevant Spec Item context (section text, existing attributes, doc type) — a context extraction layer caps extraction at 2,000 tokens max per query (FR-033: minimal context only). Suggestions are returned as structured JSON (clause_ref, suggestion_text, gap_type) for the frontend to render as individual Accept/Reject cards.

**Offline fallback (FR-033b)**: A `ComplianceRuleSet` YAML file ships with DocERP — pre-defined per standard (ASPICE Level 2/3, ISO-26262 Part 6, ISO-21434) listing required section types and mandatory fields. When the LLM API is unreachable (HTTP timeout or 5xx), the AI service falls back to rule-set matching and returns partial suggestions with a `fallback_mode: true` flag; the frontend shows the offline banner.

**Rationale**: pgvector avoids introducing a separate vector database (Pinecone, Weaviate) — keeping all data on-premise. LangChain provides a standard RAG abstraction that is model-provider-agnostic (compatible with OpenAI, Azure OpenAI, Anthropic, or a self-hosted model). The 2,000-token cap enforces FR-033 at the service layer regardless of LLM provider.

**Alternatives considered**:
- Separate vector DB (Chroma, Weaviate): Rejected. Adds a third storage system; constitution Principle IV warns against unjustified complexity.
- Fine-tuned local model only: Rejected. Licensing and training cost are outside project scope (A-004); RAG over licensed texts achieves the clause-citation requirement without fine-tuning.

---

## R-006: Git Abstraction Layer (FR-031, A-009)

**Decision**: Implement a `GitBackend` abstract base class with three concrete adapters: `GerritAdapter` (SSH/HTTP REST API), `GitHubAdapter` (PyGitHub), `GitLabAdapter` (python-gitlab). Each adapter exposes `commit(doc_content, message, branch)` and `get_history(doc_id)` methods. The active backend is configured per project via a `git_backend_type` enum column on the `Project` model. GitPython is used only for local repository operations (clone, diff); remote push is delegated to each adapter's API.

**Rationale**: Engineers must never directly interact with Git (FR-031). A backend-agnostic interface with project-level configuration satisfies A-009 (Gerrit as Phase 1 primary) while keeping GitLab/GitHub as drop-in alternatives. GitPython provides the diff computation for the inline Cascade Lock diff view (FR-017).

**Alternatives considered**:
- Single Gerrit-only client: Rejected. FR-031 explicitly requires GitHub/GitLab configurability.
- libgit2 / pygit2: Viable alternative to GitPython but lower-level; GitPython's higher-level API reduces implementation surface for the diff and history features needed.

---

## R-007: LDAP / AD Integration with Local Fallback (FR-038)

**Decision**: Use `python-ldap` for LDAP bind and group membership queries. On login, the system attempts LDAP bind first; if the LDAP server is unreachable (socket timeout < 3 s), it falls back to local bcrypt-hashed account lookup. JWTs are issued for both paths with a `auth_method: ldap | local` claim. Every `local` auth event writes to the `security_audit_log` table and dispatches an admin alert notification.

**Rationale**: `python-ldap` is the most mature Python LDAP library with full AD compatibility. 3-second LDAP timeout prevents the local fallback from being blocked for too long during LDAP outage. JWT-based session avoids per-request LDAP queries, keeping latency stable under load.

**Alternatives considered**:
- `ldap3` library: Viable; pure Python (no C extension). Selected `python-ldap` for broader enterprise AD compatibility, but `ldap3` is an equivalent fallback if C extension compilation is constrained on the on-premise server.
- Session cookies only (no JWT): Rejected. JWT allows stateless validation across horizontally scaled backend instances, which is required for the 99.5% uptime / horizontal scaling target (A-001).

---

## R-008: CodeBeamer Excel Export & Validation (FR-024, FR-026, FR-044, SC-008)

**Decision**: Use `openpyxl` to generate `.xlsx` files following Siliconmotion's RD-03-010-09 column structure. A `CodeBeamerSchemaDefinition` table in PostgreSQL stores the target column definitions (name, expected type, ordering, required flag) as a versioned record; administrators update this via the admin UI when CodeBeamer is upgraded (FR-044). Post-generation validation compares each cell against the schema definition and produces a separate Potential Import Issues report if any mismatch is detected.

**Rationale**: `openpyxl` is the standard Python library for xlsx generation without requiring Microsoft Office. Administrator-managed schema versioning decouples DocERP releases from CodeBeamer version updates (A-003). Keeping the schema as a DB record (not hardcoded) satisfies FR-035's requirement for admin-managed schema evolution.

**Alternatives considered**:
- xlsxwriter: Faster but write-only (cannot read existing files); openpyxl supports both read and write which may be needed for template-based generation.
- Direct CodeBeamer REST API: Rejected per A-003 (no direct API connection required; file-based only).

---

## R-009: FMEDA Safety Metric Calculation (FR-027–FR-030, FR-042)

**Decision**: Implement SPFM, LFM, and PMHF calculations as pure Python functions in `fmeda_calculator.py`, operating on `FMEDAWorksheet` and `FailureModeLibraryEntry` model data. Formulas follow IEC 62380 / SN 29500 failure rate conventions as referenced in ISO-26262 Part 10. Calculations are triggered synchronously (not async) since they are CPU-bound and complete in < 1 s for typical component counts. Results are stored versioned alongside the library version used (FR-042e).

**SPFM** = 1 - (Σ λ_SPF) / (Σ λ_total)  
**LFM** = 1 - (Σ λ_RF · (1 - DC_RF)) / (Σ λ_total - Σ λ_SPF)  
**PMHF** = Σ (λ_SPF + λ_RF · (1 - DC_RF)) per component

**Rationale**: Pure Python functions (no external solver dependency) keep the FMEDA module self-contained and auditable. Storing the library version at calculation time (FR-042e) ensures historical recalculation reproducibility — a hard requirement for ISO-26262 safety case documentation.

**Alternatives considered**:
- Using a spreadsheet calculation engine (e.g., formulas-js, pycel): Rejected. Adds dependency complexity; the formulas are known and fixed — custom validated Python functions are more auditable.
- MATLAB / Simulink integration: Out of scope for Phase 1; no MATLAB licensing assumed.

---

## R-010: Audit Package Retention & Storage (FR-045)

**Decision**: Audit Packages are stored on the on-premise file system under a configurable `AUDIT_PACKAGE_STORAGE_PATH`. Each package is a directory named per the FR-045 convention (`<project-id>_audit_<YYYY-MM-DD>_<HHmm>_<username>/`) containing the `.xlsx` export, the compliance check result JSON, and metadata. A `AuditPackage` DB record tracks the directory path, creation time, triggering user, and standards scope. Storage usage is computed by a scheduled Celery beat task (daily) and compared against the admin-configured threshold (default 80% of `AUDIT_PACKAGE_VOLUME_GB`).

**Rationale**: File system storage avoids PostgreSQL blob bloat for potentially large xlsx files. The DB record provides the query interface for the Audit Package History page without requiring filesystem traversal. Celery beat for storage monitoring avoids per-request overhead.

**Alternatives considered**:
- S3-compatible object storage (MinIO on-premise): Viable for future scaling; deferred to Phase 2 to keep Phase 1 infrastructure simple and fully on-premise without additional services.
- Store xlsx in PostgreSQL bytea: Rejected. Degrades DB performance for large files; backup/restore of binary blobs is more complex than filesystem archiving.

---

## Summary of All Decisions

| ID | Topic | Decision |
|----|-------|----------|
| R-001 | EAV Schema | Hybrid EAV: typed columns + JSONB payload + attribute_definitions registry + schema_version |
| R-002 | Cascade Lock Atomicity | Celery task + PostgreSQL advisory locks per BU ID |
| R-003 | Optimistic Locking / Merge | Version counter + 409 Conflict + 3-way diff in response |
| R-004 | Cycle Detection | Async Celery DFS + Redis adjacency cache + cycle_warning flag |
| R-005 | RAG / AI Fallback | LangChain + pgvector + 2,000-token cap + YAML fallback rule set |
| R-006 | Git Abstraction | Abstract GitBackend + GerritAdapter / GitHubAdapter / GitLabAdapter |
| R-007 | LDAP + Local Auth | python-ldap + JWT + 3 s timeout + local bcrypt fallback |
| R-008 | Excel Export | openpyxl + versioned CodeBeamerSchemaDefinition + post-gen validation |
| R-009 | FMEDA Calculation | Pure Python SPFM/LFM/PMHF functions + versioned result storage |
| R-010 | Audit Package Storage | Filesystem directories + AuditPackage DB record + Celery beat quota monitoring |

**All NEEDS CLARIFICATION items from Technical Context: RESOLVED**  
**Constitution Check post-research: ALL PASS — proceed to Phase 1 design.**
