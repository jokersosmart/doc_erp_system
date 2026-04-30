# Feature Specification: DocERP — Spec-Driven Document Management System

**Feature Branch**: `002-doce-erp-dms`  
**Created**: 2026-04-29  
**Status**: Draft  
**Input**: PRD: DocERP — Spec-Driven Document Management System for Siliconmotion

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — AI-Guided Project Onboarding (Priority: P0)

A PM starts a new product project at Siliconmotion and needs the correct document skeleton generated for ASPICE Level 2 and ISO-26262 ASIL-B compliance, across the SSD Controller BU. Instead of manually configuring dozens of templates, the PM launches DocERP, is guided by an AI wizard through 6–8 structured questions (project name, BU, applicable standards, ASPICE level, ASIL/CAL targets, participating departments), and receives a fully pre-populated document framework — with all required sections, traceability placeholders, and role assignments — within minutes.

**Why this priority**: Without a correct initial framework, all subsequent editing, compliance checking, and traceability is built on a broken foundation. This is the entry gate for every project.

**Independent Test**: A PM can create a new project, complete the wizard, and receive a document skeleton that is immediately openable and editable — before any other feature is implemented.

**Acceptance Scenarios**:

1. **Given** a PM logs into DocERP for the first time with a new project, **When** they complete the AI onboarding wizard with all 6–8 questions answered, **Then** a fully pre-populated document framework is generated with the correct sections for the selected BU, standards, and departments.
2. **Given** an SSD Controller BU project is created with ASPICE Level 2 and ISO-26262 ASIL-B, **When** the framework is generated, **Then** it includes HARA, Safety Goals, and System Spec partitions with the correct ownership assignments.
3. **Given** an eMMC BU project is created with different standards, **When** the framework is generated, **Then** it is distinct from the SSD Controller BU framework with BU-specific templates applied.
4. **Given** a PM partially completes the wizard, **When** they quit and return later, **Then** the wizard resumes from where they left off.

---

### User Story 2 — In-Editor AI Compliance Consulting (Priority: P0)

An RD engineer is filling out a Firmware Spec and realises a paragraph may be missing an ISO-26262 Clause 6 reference. Without leaving the document, the engineer clicks the AI consultant button; a side panel opens listing identified gaps with suggested content and the standard clause each suggestion maps to. The engineer reviews each suggestion individually and clicks Accept or Reject. Accepted content appears in the document at the correct position, logged under the engineer's name and timestamp in the audit trail.

**Why this priority**: This is the core daily productivity loop for every RD. It ensures compliance is embedded at authoring time, not discovered at audit time.

**Independent Test**: An RD can open any existing Spec, invoke the AI consultant, receive at least one actionable suggestion, and accept or reject it — with the result visible both in the document and in the audit trail.

**Acceptance Scenarios**:

1. **Given** an RD is editing a Spec with at least one missing required section, **When** the AI consultant is invoked, **Then** the side panel lists identified gaps with specific suggested content and a standard clause reference for each item.
2. **Given** the AI consultant presents a suggestion, **When** the engineer clicks Accept, **Then** the content is inserted at the correct position in the document and an audit log entry is created: "Suggested by AI, accepted by [Engineer Name] on [Date/Time]".
3. **Given** the AI consultant presents a suggestion, **When** the engineer clicks Reject, **Then** the document is unchanged and no audit entry is created for that suggestion.
4. **Given** AI-generated content is presented, **When** the engineer takes no action, **Then** nothing is written to the document automatically — the document is never modified without an explicit Accept action.
5. **Given** a safety-critical Spec (ASIL-B or above) is open, **When** the AI consultant is invoked, **Then** suggestions include explicit references to the relevant ISO-26262 clause numbers.

---

### User Story 3 — Cascade Lock & Dependency Notification (Priority: P0)

The system Architect saves a change to the top-level System Spec. All directly dependent sub-team Specs (FW, HW, SW, and their corresponding Validation Specs) are immediately placed in a LOCKED state. Each affected owner receives an in-app notification and email alert containing a diff view of what changed upstream. For standard Specs, owners self-unlock after marking "Reviewed & Updated". For safety-critical Specs (ASIL-B or above / high CAL), a QRA auditor must additionally approve before the lock clears.

**Why this priority**: This is the primary mechanism preventing stale downstream documents, which is the root cause of the most common audit non-conformances.

**Independent Test**: An Architect can save a top-level Spec change, and all dependent Spec owners can be observed receiving a lock notification and a diff view — demonstrable with two user accounts.

**Acceptance Scenarios**:

1. **Given** the Architect saves a change to the top-level System Spec, **When** the save completes, **Then** all directly dependent sub-team Specs are atomically placed into a LOCKED state with no partial lock states.
2. **Given** a sub-team Spec is LOCKED, **When** the responsible owner opens it, **Then** a prominent red LOCKED banner is displayed along with an inline diff showing what changed in the upstream Spec.
3. **Given** a standard (non-safety-critical) Spec is LOCKED and the owner clicks "Mark as Reviewed & Updated", **When** confirmed, **Then** the lock clears immediately and the document becomes available for Git commit and CodeBeamer export.
4. **Given** a safety-critical Spec (ISO-26262 ASIL-B or above) is LOCKED and the owner clicks "Mark as Reviewed & Updated", **When** confirmed, **Then** the document transitions to a yellow "Pending QRA Approval" state — it is not yet available for commit or export.
5. **Given** a Spec is in Pending QRA Approval, **When** the assigned QRA auditor approves the unlock, **Then** the lock clears, a green banner is shown, and the document is released for Git commit and CodeBeamer export.
6. **Given** a QRA auditor requests revision instead of approving, **When** the revision request is submitted with comments, **Then** the lock remains and the document owner receives a notification with the QRA comments.
7. **Given** any LOCKED document is attempted for Git commit or CodeBeamer export, **When** attempted, **Then** the action is blocked with a clear message indicating the lock reason.

---

### User Story 4 — Traceability Matrix & One-Click Audit Package Export (Priority: P1)

An auditor needs to verify that every requirement in a project traces end-to-end from inception through design and test evidence. The auditor opens the dependency graph, navigates the traceability matrix, runs a one-click compliance check against ASPICE, ISO-26262, and ISO-21434, then generates a CodeBeamer-compatible Excel export package — all without touching CodeBeamer directly.

**Why this priority**: This is the primary output artifact of the system. Reducing audit preparation from days to minutes has a direct business impact.

**Independent Test**: An auditor can run a compliance check on an existing project and download an Excel file — even if the file is not yet perfectly formatted for CodeBeamer.

**Acceptance Scenarios**:

1. **Given** an auditor clicks "Audit Check", **When** the check completes, **Then** a compliance gap report is displayed listing all missing or incomplete items against ASPICE, ISO-26262, and ISO-21434 requirements.
2. **Given** the auditor triggers an export, **When** the generation completes, **Then** a structured `.xlsx` file is downloaded, matching the column structure of Siliconmotion's HW Architectural Design template (RD-03-010-09) fields: Status, Safety Related, Source HSR, Source HSI, SM ID, SM Type, Reaction/Diagnostics, FDTI, FRTI, FHTI, Diagnostic Coverage, Ref., Verification, Dependency, CC-ID, CC Type, Source HCR-ID, Reaction/Response.
3. **Given** the generated Excel is imported into CodeBeamer, **When** imported, **Then** all Spec items map correctly to Tracker Items without manual reformatting.
4. **Given** a project has complete traceability, **When** the traceability matrix is viewed, **Then** every requirement item shows its linked design element, test case, and evidence — with no broken links.

---

### User Story 5 — FMEDA Automation (Priority: P1)

A safety engineer needs to complete a Failure Mode Effects and Diagnostic Analysis (FMEDA) worksheet for an ISO-26262 ASIL-B design. Instead of manually computing safety metrics, the engineer opens the FMEDA module, enters component data and failure mode library references, and the system auto-fills the worksheet and computes SPFM, LFM, and PMHF values — flagging any results that fail to meet ASIL target thresholds.

**Why this priority**: Manual FMEDA calculation is error-prone and a frequent source of ISO-26262 non-conformances; automation directly reduces the most critical risk of quantitative safety analysis errors.

**Independent Test**: A safety engineer can input minimal component data and receive computed SPFM, LFM, and PMHF values — even before the Excel export is ready.

**Acceptance Scenarios**:

1. **Given** a safety engineer inputs component data and a failure mode library reference, **When** calculation is triggered, **Then** SPFM, LFM, and PMHF values are automatically computed and displayed.
2. **Given** a computed metric does not meet the ASIL-B threshold, **When** results are displayed, **Then** the failing metric is flagged with a clear warning and the specific threshold it failed.
3. **Given** the FMEDA worksheet is completed, **When** the engineer triggers export, **Then** a CodeBeamer-compatible Excel file is generated with all FMEDA fields populated.

---

### User Story 6 — Git Commit via DocERP (Priority: P1)

An RD engineer completes updating a Firmware Spec and wants to commit the changes. Without needing to know whether the backend is Gerrit, GitHub, or GitLab, the engineer clicks "Commit" in DocERP, enters a commit message, and the system handles the backend submission — including triggering dependency and audit update routines automatically on successful commit.

**Why this priority**: Engineers should never need to learn or operate version control tooling directly; abstraction enables adoption and reduces errors.

**Independent Test**: An engineer can submit a document commit via the DocERP UI and observe that a corresponding commit appears in the configured Git backend.

**Acceptance Scenarios**:

1. **Given** an unlocked document has pending changes, **When** the engineer clicks Commit in DocERP and enters a message, **Then** the commit is pushed to the configured Git backend (Gerrit / GitHub / GitLab) without the engineer needing to use Git commands.
2. **Given** the Git backend is Gerrit, **When** a commit is submitted, **Then** the commit is pushed through the Gerrit code review workflow without engineer intervention.
3. **Given** a LOCKED document, **When** the engineer attempts to commit, **Then** the commit is blocked with a clear lock-reason message.
4. **Given** a successful commit, **When** complete, **Then** dependency and audit update routines are automatically triggered.

---

### Edge Cases

- What happens when an Architect saves a System Spec change while a sub-team owner is actively editing their dependent Spec — does the lock apply mid-edit and is unsaved work preserved?
- How does the system handle a circular dependency between documents (A depends on B, B depends on A)?
- What happens when two Architects simultaneously save conflicting changes to the top-level System Spec?
- How does the system behave when the cloud AI inference endpoint is unavailable — can engineers still edit and commit documents without AI features?
- What happens if a CodeBeamer Excel import fails due to a template version mismatch?
- What happens when a QRA auditor is unavailable for an extended period and safety-critical Specs remain locked in "Pending QRA Approval"?

---

## Requirements *(mandatory)*

### Functional Requirements

**Org & Project Setup**

- **FR-001**: The system MUST support an organisational hierarchy of up to 5 levels: Company → Business Unit → Process → Department → Sub-department.
- **FR-002**: The system MUST support at least two independent Business Unit contexts (SSD Controller BU and eMMC BU) with distinct document templates and applicable standards per BU.
- **FR-003**: The system MUST allow configuring a project with one or more compliance standards: ASPICE (by level), ISO-26262 (by ASIL rating), and ISO-21434 (by CAL rating).
- **FR-004**: The system MUST enforce role-based access control (RBAC) mapped by both organisational hierarchy level and document type (Manual / Procedure / Spec / Form).
- **FR-005**: The system MUST support R&D department sub-team structure: Architect, FW (+ FW Validation), HW (+ HW Validation), SW (+ SW Validation), and VCT.

**AI Consultant & Spec Builder**

- **FR-006**: The system MUST provide an AI onboarding wizard that asks 6–8 structured questions and generates a pre-populated, role-assigned document framework for the selected BU and compliance standards.
- **FR-007**: The AI consultant MUST operate in suggestion-only mode: all suggestions are presented in a side panel, and no AI-generated content is written to a document without an explicit engineer Accept action.
- **FR-008**: Every accepted AI suggestion MUST be logged in the document audit trail as "Suggested by AI, accepted by [Engineer Name] on [Date/Time]".
- **FR-009**: The AI consultant MUST identify compliance gaps and present suggested content with the specific standard clause reference (e.g., ISO-26262 Part 6 Clause 7.4.2) for each suggestion.

**Document Management & Partitioning**

- **FR-010**: The system MUST partition Specs into phase/domain-specific segments, each enforced by an independent compliance Agent.
- **FR-011**: The system MUST maintain a full version history and audit trail for each document, supporting rollback to any prior version.
- **FR-012**: Each document MUST display both its current lifecycle state (DRAFT / REVIEW / APPROVED / OBSOLETE) and any active lock indicator to all users — on both the document header and the project dashboard. The lifecycle state and lock indicator are shown as two distinct, co-visible elements.
- **FR-013**: Standard (non-safety-critical) documents MUST follow the embedded lock lifecycle: a cascade lock may only be applied when the document is in REVIEW or APPROVED state. After the owner marks "Reviewed & Updated", the document transitions to APPROVED, which automatically clears the lock and makes the document available for Git commit and CodeBeamer export.
- **FR-014**: Safety-critical documents (ISO-26262 ASIL-B or above; ISO-21434 high CAL) MUST follow the embedded lock lifecycle: Locked (document in REVIEW state) → Pending QRA Approval (document remains in REVIEW state) → QRA Approves → document transitions to APPROVED, which automatically clears the lock. Only after APPROVED transition may the document be committed to Git or exported to CodeBeamer.
- **FR-014b**: When a safety-critical document is in Pending QRA Approval state and a QRA auditor is unavailable, a PM or department manager MAY apply an Emergency Override to force-unlock the document. Every Emergency Override MUST be fully logged in the audit trail (actor, timestamp, stated reason) and a notification MUST be sent to the responsible QRA auditor. An Emergency Override sets `lock_state = UNLOCKED` and `lifecycle_state = APPROVED` atomically, with the Override actor recorded as the approval authority in the audit trail.
- **FR-013b**: All document lifecycle state transitions MUST be strictly unidirectional: `DRAFT → REVIEW → APPROVED → OBSOLETE`. The system MUST NOT implement backward lifecycle state transitions. When QRA requests revision of a safety-critical document (i.e., disapproves the unlock), the document retains its current `lifecycle_state` and the system sets a `revision_requested = TRUE` flag on the document record; the document does NOT transition backward. The responsible owner then creates a new document version (starting in `DRAFT` state) to incorporate the requested revisions, following the standard forward lifecycle.
- **FR-015**: When the top-level System Spec is saved, the lock MUST be applied atomically to all directly dependent sub-team Specs — partial lock states are not permitted.
- **FR-015b**: The system MUST use optimistic locking for concurrent editing: multiple users may edit the same document simultaneously; on save, the system detects version conflicts and presents a manual merge interface to the user who saves second. The merge view MUST show a three-way diff (my changes / base / their changes). Conflict resolution is always performed by a human — the system MUST NOT auto-merge document content.
- **FR-015c**: When a Cascade Lock is triggered while a sub-team owner is actively editing their dependent Spec, the lock MUST be deferred and applied only after the owner completes their current save action. The in-progress editing session MUST NOT be interrupted. The lock state transition applies atomically upon the owner's next save event for that document.
- **FR-015d**: The system MUST allow users to create any dependency relationship (Blocking, Blocked By, Related) without real-time validation. After saving, the system MUST asynchronously detect any circular dependency cycles in the Blocking/Blocked By graph and, if a cycle is detected, MUST immediately send an in-app notification and email alert to the owners of all documents involved in the cycle, clearly listing the full circular path. The relationship that completed the cycle MUST be flagged as "Circular Dependency Warning" in the dependency graph view until resolved by a human. The system MUST NOT automatically remove or alter any user-defined dependency relationship.
- **FR-016**: A locked document MUST be blocked from Git commit and CodeBeamer export until unlocked.
- **FR-017**: When a sub-team owner opens a LOCKED document, they MUST be shown an inline diff of exactly what changed in the upstream Spec that triggered the lock.

**Traceability & Dependency Engine**

- **FR-018**: Each Spec item MUST support three dependency relationship types: Blocking (this item blocks downstream items), Blocked By (this item is blocked by upstream items), and Related/Ref. (non-blocking notification-only reference).
- **FR-019**: A single Spec item MUST support multiple simultaneous upstream references (e.g., Blocked By both a HSR source and a HSI source).
- **FR-019b**: Each dependency link MUST carry a `traceability_state` field with values `VALID` or `SUSPECT` (Constitution §II). When the source document of any BLOCKING or BLOCKED_BY dependency link is modified and saved, the system MUST automatically transition the `traceability_state` of all dependency links connected to Spec Items in that document from `VALID` to `SUSPECT`. The `traceability_state` is reset to `VALID` when the downstream document owner marks their Spec as "Reviewed & Updated" (FR-013 / FR-014). Related/Ref. dependency links are exempt from SUSPECT transitions (they trigger notifications only, per FR-018).
- **FR-020**: The system MUST auto-generate and maintain a cross-document dependency graph visible to all roles.
- **FR-021**: When a document changes, the system MUST automatically identify all directly affected downstream documents and notify their responsible owners.
- **FR-022**: The system MUST generate a traceability matrix mapping: requirement → design element → test case → evidence.

**Audit & Compliance Export**

- **FR-023**: The system MUST provide a one-click compliance check that surfaces gaps against ASPICE, ISO-26262, and ISO-21434 requirements for the active project.
- **FR-024**: The system MUST generate a structured `.xlsx` export file matching Siliconmotion's HW Architectural Design template (RD-03-010-09) column structure per Spec item: Status, Safety Related, Source HSR, Source HSI, SM ID, SM Type, Reaction/Diagnostics, FDTI, FRTI, FHTI, Diagnostic Coverage, Ref., Verification, Dependency, CC-ID, CC Type, Source HCR-ID, Reaction/Response.
- **FR-025**: CodeBeamer integration MUST be one-way export only (DocERP pushes; no inbound sync from CodeBeamer).
- **FR-026**: The system MUST perform a post-generation validation pass on the generated `.xlsx` file against the CodeBeamer column schema version configured in system administration settings. If any field type mismatch, missing required column, or column ordering deviation is detected, the file MUST still be made available for download accompanied by a structured "Potential Import Issues" report (see FR-044 for output format definition). The validation MUST NOT block the download. FR-044 is the authoritative specification of the validation output format and delivery mechanism.

**FMEDA Automation**

- **FR-027**: The system MUST provide a dedicated FMEDA module that auto-fills worksheets based on component data and a failure mode library.
- **FR-028**: The FMEDA module MUST automatically calculate SPFM, LFM, and PMHF for each component.
- **FR-029**: The FMEDA module MUST flag results that do not meet the configured ASIL target threshold.
- **FR-030**: The FMEDA module MUST export completed worksheets in a CodeBeamer-compatible Excel format.

**Git & Tool Integration**

- **FR-031**: The system MUST provide a Git abstraction layer allowing users to commit documents via the DocERP UI without needing knowledge of the underlying Git backend (Gerrit, GitHub, or GitLab — configurable per project).
- **FR-032**: All application services, databases, and Git repositories MUST run on Siliconmotion's on-premise infrastructure. No document content may leave the internal network.
- **FR-033**: For AI inference, only the minimal Spec context required for the specific query may be transmitted to the cloud LLM endpoint — full document content MUST NOT be transmitted externally.

**Document Item Attribute Model**

- **FR-033b**: When the cloud LLM API endpoint is unavailable, the AI consultant MUST automatically fall back to a local static compliance rule set (pre-defined ASPICE / ISO-26262 / ISO-21434 checklist) and present partial suggestions based on those rules. A banner MUST notify the user that AI is operating in offline/fallback mode. All non-AI features (editing, version control, dependency graph, Git commit, CodeBeamer export) MUST remain fully operational during AI service unavailability.

- **FR-034**: Every Spec item MUST carry the following structured attributes: (a) Spec Clause Reference (which standard clause this item satisfies), (b) Blocking (list of downstream items this item blocks), (c) Blocked By (list of upstream items this item depends on), (d) Related/Ref. (non-blocking associated items).
- **FR-035**: The attribute schema MUST support incremental additions for new document types without breaking existing document records or export formats, including a schema versioning mechanism.

**Unified FW/HW Development Standard**

- **FR-036**: The system MUST enforce a shared document convention layer for both FW and HW sub-teams, including a document template registry with standard templates for each document type (Spec, Test Plan, Design Description).
- **FR-037**: The AI consultant MUST flag deviations from the unified document standard during editing.

**OBSOLETE Document Downstream Impact**

- **FR-039**: When a Document transitions to the OBSOLETE lifecycle state, the system MUST immediately scan all Dependency Links whose upstream end references any Spec Item in that Document (covering Blocking, Blocked By, and Related relationship types). For each downstream Spec Item found, the system MUST: (a) mark it with an "Upstream Obsolete Warning" flag visible in the document view and dependency graph; (b) deliver an in-app notification and email alert to the downstream Spec Item's responsible owner requesting re-evaluation of the dependency; and (c) record the event in the audit trail. The system MUST NOT automatically remove, modify, or disconnect any existing Dependency Link — all link management remains the sole responsibility of the human owner.

**FMEDA Failure Mode Library**

- **FR-042**: The FMEDA module MUST maintain a versioned Failure Mode Library with the following management model: (a) a pre-loaded baseline library covering common IC design component types (supplied with the DocERP installation) is available immediately without any user configuration; (b) authorised administrators MUST be able to add, edit, or delete custom failure mode entries (including component type, failure rate λ, failure mode distribution ratios, and diagnostic coverage defaults) through a dedicated Library Management UI; (c) bulk import of custom failure mode entries via a standardised Excel template MUST be supported; (d) every addition, modification, or deletion of a library entry MUST be recorded in a versioned audit trail (actor, timestamp, before/after values); (e) FMEDA worksheets MUST reference the library entry version used at calculation time, so that recalculations with an updated library produce a new versioned result without overwriting historical records.

**UI Localisation**

- **FR-040**: The DocERP web UI MUST support two display languages — Traditional Chinese (繁體中文) and English — selectable per user in personal preferences settings. All UI labels, navigation items, system messages, error messages, and notification text MUST be fully localised in both languages. ISO/ASPICE technical terms (e.g., ASIL, CAL, SPFM, LFM, PMHF) MUST remain in their original English abbreviation form in both language modes to preserve audit-terminology consistency. The selected language preference MUST be persisted per user account and applied on subsequent logins without reconfiguration.

**Concurrent Architect Cascade Lock**

- **FR-041**: Cascade Lock events triggered by different Business Unit Architects MUST be scoped to their respective BU boundaries. A Cascade Lock initiated by the SSD Controller BU Architect MUST only lock Spec documents within the SSD Controller BU scope; a Cascade Lock initiated by the eMMC BU Architect MUST only lock documents within the eMMC BU scope. The two BU-scoped Cascade Lock processes MUST execute independently and in parallel without cross-BU interference. If both BU Architects save top-level Spec changes simultaneously, each BU's lock propagation MUST complete atomically within its own scope without waiting for the other BU to complete.

**AI Onboarding Wizard Resume**

- **FR-043**: The AI onboarding wizard MUST implement step-level auto-save for all in-progress wizard sessions. After each question-answer step is completed, the current wizard state (answered questions, selected options, project context) MUST be automatically persisted to the user's account on the server. When the same user logs in again (or navigates back to the wizard) and an incomplete wizard session exists for a project, the system MUST present a prompt offering two actions: (a) "Continue" — resume the wizard from the last completed step, with all previously answered questions pre-filled and visible; or (b) "Start Over" — discard the saved progress and restart the wizard from step 1. If the user selects Start Over, the previous incomplete wizard state MUST be permanently deleted. Auto-saved wizard state MUST NOT be accessible to other users. Wizard sessions that remain incomplete for more than 90 days MUST be automatically expired and deleted, with the user notified by email.

**CodeBeamer Export Validation**

- **FR-044**: When generating a CodeBeamer-compatible `.xlsx` export, the system MUST perform a post-generation validation pass against the known CodeBeamer column schema version configured in the system administration settings. If any field value type mismatch, missing required column, or column ordering deviation is detected, the `.xlsx` file MUST still be made available for download but MUST be accompanied by a "Potential Import Issues" report listing: (a) each detected discrepancy with the specific column name and row reference, (b) the expected format or value type per the configured CodeBeamer schema version, and (c) a recommended corrective action for each issue. The Potential Import Issues report MUST be downloadable as a separate `.pdf` or `.xlsx` file alongside the main export. If no issues are detected, a green "Validation Passed" status indicator MUST be displayed before download. Administrators MUST be able to update the target CodeBeamer schema version definition in the system settings to maintain compatibility with CodeBeamer updates.

**Audit Package Version Retention**

- **FR-045**: Every execution of the one-click audit package export MUST generate a uniquely named, immutable Audit Package archive. The archive filename MUST follow the convention `<project-id>_audit_<YYYY-MM-DD>_<HHmm>_<username>.<ext>`. All historical Audit Packages MUST be retained indefinitely on the system until an administrator explicitly deletes them. An "Audit Package History" page accessible to PM, Auditor, and Administrator roles MUST list all historical packages for a given project in reverse-chronological order, displaying: (a) export timestamp, (b) triggering user, (c) standards scope (ASPICE, ISO-26262, ISO-21434), and (d) a re-download button. Automated deletion of Audit Packages by the system MUST NOT occur. Storage quota warnings MUST be surfaced to administrators via the system dashboard when Audit Package storage exceeds a configurable threshold (default: 80% of allocated volume).

**Email Notification Failure Handling**

- **FR-046**: When the system is unable to deliver an email notification (e.g., SMTP service unavailable, recipient address unreachable), the system MUST silently record the delivery failure in the system log (including: notification type, intended recipient, timestamp, and error reason). No retry MUST be attempted and no in-app fallback notification MUST be generated. All non-email features (in-app banners, dependency locking, document editing, Git commit, export) MUST continue to operate normally regardless of email delivery status. System administrators MAY inspect delivery failure logs via the system administration panel.

**Authentication**

- **FR-038**: The system MUST support a dual-track authentication mechanism: (a) primary LDAP / Active Directory integration for all standard enterprise user login (inheriting Siliconmotion's existing organisational account structure and group memberships), and (b) a local administrator account as fallback, reserved exclusively for emergency access when the LDAP/AD service is unavailable. Every emergency local-account login MUST be logged in the system audit trail with actor, timestamp, and stated reason, and a security alert MUST be sent to the system administrator.

### Key Entities

- **Organisation Node**: Represents one level of the 5-level hierarchy (Company / BU / Process / Department / Sub-department); carries applicable standards and template configurations.
- **Project**: Scoped to a BU; carries selected compliance standards (ASPICE level, ASIL, CAL), participating departments, and role assignments.
- **Document**: A versioned Spec or supporting document belonging to a Project; has a type (Manual / Procedure / Spec / Form), an owner, a partition assignment, a lifecycle state (DRAFT → REVIEW → APPROVED → OBSOLETE), and a full audit trail. Lock semantics are embedded in the lifecycle: cascade locks may only be applied to documents in REVIEW or APPROVED state; transitioning a document to APPROVED automatically clears any active lock.
- **Spec Item**: One atomic requirement, design element, test case, or evidence entry within a Document; carries the Document Item Attribute Model (Clause Reference, Blocking, Blocked By, Related).
- **Dependency Link**: A typed relationship between two Spec Items — Blocking, Blocked By, or Related — forming the edges of the dependency graph. Each link carries a `traceability_state` (VALID / SUSPECT) that is automatically set to SUSPECT when the source document is modified, and reset to VALID upon downstream owner review (FR-019b, Constitution §II).
- **AI Suggestion**: A proposed content insertion for a Spec Item, associated with a standard clause reference, with Accept/Reject status and an audit log entry on acceptance.
- **Lock Event**: A record of a cascade lock trigger: which upstream Document changed, which downstream Documents were locked, and the timestamp.
- **FMEDA Worksheet**: A structured safety analysis artifact containing component data, failure modes, and computed safety metrics (SPFM, LFM, PMHF).
- **Audit Package**: A point-in-time export artifact containing the compliance check result and the CodeBeamer-compatible `.xlsx` file.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Audit document preparation time per project is reduced by 60%, measured by team self-reported pre/post cycle time comparison over the first 3 audits using DocERP.
- **SC-002**: Audit non-conformance findings related to document traceability or cross-document inconsistency are reduced by 80%, tracked via formal ASPICE/ISO audit result records.
- **SC-003**: Any change to a document is reflected in the dependency graph and all affected owner notifications are delivered within 3 seconds of the document save action.
- **SC-004**: The system supports at least 100 concurrent users on internal servers without measurable degradation in response time for standard operations.
- **SC-005**: AI consultant suggestions cover more than 70% of required Spec sections that were incomplete at the time of invocation, as measured by section fill rate before and after accepted suggestions.
- **SC-006**: A new project reaches its first complete, CodeBeamer-ready audit package within 2 calendar weeks of project creation.
- **SC-007**: System availability exceeds 99.5% per calendar month, measured by internal uptime monitoring.
- **SC-008**: CodeBeamer Excel import success rate (no reformatting required) exceeds 99%, tracked via import logs.
- **SC-009**: Git commit failure rate through the DocERP abstraction layer is below 0.1%, tracked per submitted commit.
- **SC-010**: User satisfaction scores across PM, RD, and Auditor roles consistently exceed 4.2 out of 5.0 in periodic in-app surveys.
- **SC-011**: 95% of users successfully complete their primary role-specific task (PM: project setup; RD: Spec update and commit; Auditor: compliance check and export) on first attempt without requiring support.

---

## Assumptions

- **A-001**: Siliconmotion will provide on-premise server resources sufficient to host all DocERP services (web application, document database, Git layer, dependency engine) for Phase 1 (100+ concurrent users).
- **A-002**: AI inference is performed via a third-party cloud LLM API; only the minimal Spec context per query is transmitted, never full document content. The choice of LLM provider is an implementation decision outside this spec.
- **A-003**: CodeBeamer integration does not require a direct API connection — the integration is entirely file-based (locally generated `.xlsx` export downloaded and manually imported into CodeBeamer by a responsible person).
- **A-004**: Siliconmotion will provide access to licensed ASPICE 3.1, ISO-26262, and ISO-21434 reference materials for AI RAG training; DocERP does not embed these texts without a valid license.
- **A-005**: DocERP is not a qualified tool under ISO-26262 Part 8 or any equivalent automotive standard. CodeBeamer remains the certified auditor-facing system of record. DocERP's role is to accelerate internal preparation, not to replace qualified tooling.
- **A-006**: eMMC BU and SSD Controller BU operate as independent contexts in the same DocERP instance; they may share infrastructure but have separate document frameworks, templates, and standard configurations.
- **A-007**: Mobile device support is out of scope for Phase 1; DocERP targets desktop browsers.
- **A-008**: The initial HW document attribute set is defined by the existing RD-03-010-09 template; FW, SW, and Architect-level document type attributes will be added incrementally as their templates are finalised — the system must accommodate this incremental schema evolution without breaking existing records.
- **A-009**: The Gerrit backend is the primary Git integration target for Phase 1; GitHub and GitLab are configurable alternatives.
- **A-010**: All document content and version history is stored exclusively on-premise; this assumption is a hard constraint not subject to change without a formal architectural review per the project constitution.

---

## Clarifications

### Session 2026-04-29

- Q: 文件生命週期狀態機（DRAFT/REVIEW/APPROVED/OBSOLETE）與鎖定狀態機（Locked/Pending QRA/Unlocked）如何共存？ → A: 合併（Option B）：鎖定狀態嵌入生命週期。cascade lock 僅能套用於 REVIEW 或 APPROVED 狀態的文件；文件轉換至 APPROVED 狀態時自動解除任何鎖定。
- Q: 當安全關鍵 Spec 進入「Pending QRA Approval」但 QRA 長時間不可用時，如何處理？ → A: Emergency Override（Option B）：PM 或部門主管可申請強制解鎖，每次 Override 操作須完整記錄於稽核日誌（操作人、時間、原因），並通知 QRA 稽核員。
- Q: 多位工程師同時編輯同一份 Spec 時，如何處理並行編輯衝突？ → A: 樂觀鎖（Option B）：允許並行編輯，儲存時偵測版本衝突並呈現三方 diff merge 介面，人工解決衝突，系統不得自動合併文件內容。
- Q: 當雲端 LLM API 不可用時，AI 顧問應如何處置？ → A: 本地靜態規則 fallback（Option B）：AI 不可用時改用本地預先定義的 ASPICE / ISO 合規規則清單提供 partial 建議，並以 banner 告知使用者目前處於 offline/fallback 模式；所有非 AI 功能維持正常運作。
- Q: 使用者認證機制為何？ → A: 雙軌並行（Option C）：主要採用 LDAP / Active Directory 企業 SSO，備用本地管理員帳號僅供 LDAP/AD 服務不可用時緊急存取，每次緊急登入須完整記錄於稽核日誌並發出安全警報。
- Q: Cascade Lock mid-edit：owner 正在編輯中被上游鎖定，未儲存工作如何處理？ → A: 延遲鎖定（Option B）：鎖定訊號排隊等待，當 owner 完成當前儲存動作後才正式套用鎖定；系統不中斷進行中的編輯，不保留草稿；鎖定狀態的原子性套用於 owner 的下一次 save 事件。
- Q: 循環相依（Circular Dependency）的偵測點與處置行為為何？ → A: 非同步偵測 + 警告通知（Option B）：允許使用者建立任何相依連結，儲存後系統非同步偵測循環；偵測到循環時向所有涉及文件的 owner 發送 in-app 通知與 email 警報，並在相依圖中標示「Circular Dependency Warning」；系統不自動刪除或修改任何使用者定義的相依關係。
- Q: 文件轉為 OBSOLETE 後，仍有下游 Spec Item 以 Blocking/Blocked By/Related 參照它時，系統應如何處理？ → A: 即時掃描 + 標記「Upstream Obsolete Warning」（Option A）：轉換時即時掃描所有相關 Dependency Links，對每個下游 Spec Item 標記警告旗標並通知 owner 重新評估；系統不自動斷開任何連結，所有連結管理由人工決策。
- Q: DocERP UI 介面語系範圍為何？ → A: 雙語 UI（Option A）：繁體中文 + 英文，使用者可在個人偏好設定中切換；ISO/ASPICE 技術術語（ASIL、CAL、SPFM 等）在兩種語系下均保持英文縮寫以確保稽核術語一致性；語系偏好設定持久化於帳號，登入後自動套用。
- Q: 兩位 BU Architect 同時儲存各自頂層 System Spec 時，Cascade Lock 一致性如何確保？ → A: 分 BU 獨立鎖定（Option C）：每個 BU 的 Cascade Lock 事件以各自 BU 範圍為邊界，兩個 BU 的鎖定傳播彼此獨立並行執行，互不干涉；各 BU 內部仍保證原子性套用。
- Q: FMEDA 失效模式庫的來源與維護方式？ → A: 系統預載基礎庫 + 使用者可擴充（Option A）：DocERP 預載涵蓋常見 IC 設計元件的基礎失效模式庫；授權管理員可透過管理 UI 新增/編輯/刪除自訂失效模式，亦支援 Excel 批次匯入；所有庫條目修改納入有版本號的稽核日誌；FMEDA 工作表參照計算時所用的庫條目版本，歷史計算結果不因庫更新而覆寫。
- Q: AI 入職精靈中途中斷後，重新登入應如何恢復？ → A: 逐步自動暫存（Option A）：每答完一題即將精靈進度儲存至使用者帳號；重新登入時若存在未完成的精靈 session，系統提示「繼續上次設定」或「重新開始」；選擇重新開始後舊進度永久刪除；精靈狀態不得被其他使用者存取；超過 90 天未完成的精靈 session 自動過期並以 email 通知使用者。
- Q: CodeBeamer 匯入失敗時（欄位格式不符、版本不相容），DocERP 應如何處置？ → A: 匯出後警告（Option B）：`.xlsx` 檔案仍可下載，但附帶「潛在問題清單」報告列出具體欄位差異、預期格式與修正建議；無問題時顯示綠色「Validation Passed」；管理員可更新 schema 版本設定以維持與 CodeBeamer 新版的相容性。
- Q: 同一專案多次匯出稽核包時，歷史版本如何保留？ → A: 全版本永久保留（Option A）：每次匯出以時間戳記 `<project-id>_audit_<YYYY-MM-DD>_<HHmm>_<username>` 命名，所有版本永久保留並可在「Audit Package History」頁面查閱與重新下載；系統不自動刪除任何歷史版本，由管理員手動清理；儲存用量超過可設定閾值（預設 80%）時向管理員發出 dashboard 警告。
- Q: SMTP 服務不可用時，email 通知送達失敗的處置方式為何？ → A: 靜默放棄（Option B）：email 失敗僅記錄至系統 log（通知類型、受件人、時間戳記、錯誤原因），不重試，不補發 in-app 通知；所有非 email 功能維持正常運作；管理員可透過系統管理面板查閱送達失敗日誌。
