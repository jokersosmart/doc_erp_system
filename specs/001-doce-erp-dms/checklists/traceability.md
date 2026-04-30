# Traceability & Dependency Engine — Requirements Quality Checklist

**Purpose**: Validate the completeness, clarity, consistency, and measurability of requirements related to the Dependency Relationship Model (Blocking / Blocked By / Related), Cascade Lock atomicity, OBSOLETE document impact chain, circular dependency detection, and traceability matrix.
**Created**: 2026-04-29
**Depth**: Thorough (~44 items)
**Audience**: Author self-review (pre-PR)
**Primary Spec Sections**: FR-015, FR-015b, FR-015c, FR-015d, FR-016–FR-022, FR-039, FR-041

---

## Dependency Relationship Model — Completeness & Clarity

- [ ] CHK001 - Are the three dependency relationship types (Blocking, Blocked By, Related/Ref.) each defined with their full behavioral consequences — specifically which type triggers a lock, which triggers a notification only, and which direction each applies? [Completeness, Spec §FR-018]
- [ ] CHK002 - Is the semantic difference between "Blocking" and "Blocked By" stated as an explicit directional inverse relationship, rather than left for developers to infer from context? [Clarity, Spec §FR-018]
- [ ] CHK003 - Is "Related/Ref." (non-blocking, notification-only) sufficiently differentiated from "Blocking" with concrete, testable behavioral criteria that prevent implementation ambiguity? [Clarity, Spec §FR-018]
- [ ] CHK004 - Are requirements defined for how each dependency type is visually presented to users (labels, directional indicators, icons) within the dependency graph and Spec item view? [Gap]
- [ ] CHK005 - Is the maximum number of simultaneous upstream references per Spec item explicitly defined or declared unbounded? Is there a performance implication for unbounded references? [Clarity, Spec §FR-019]
- [ ] CHK006 - Are requirements specified for the data model that stores multi-source Blocked By references (e.g., a single SM item blocked by both a HSR and a HSI source simultaneously)? [Completeness, Spec §FR-019]
- [ ] CHK007 - Is there a requirement for how dependency relationships are versioned — if a relationship is changed or deleted, is the prior state preserved in the audit trail? [Gap]

---

## Cascade Lock — Atomicity & State Machine

- [ ] CHK008 - Is "atomicity" in FR-015 defined precisely enough to be objectively testable — specifically, does the spec state what observable system state constitutes a "partial lock" violation? [Measurability, Spec §FR-015]
- [ ] CHK009 - Is the exact trigger event for Cascade Lock defined (e.g., "on save completion" vs. "on save initiation")? An ambiguous trigger point could cause inconsistent lock timing. [Clarity, Spec §FR-015]
- [ ] CHK010 - Is the cascading depth defined — does a lock propagate only one level (System Spec → sub-team Specs) or recursively through all transitive dependents? [Clarity, Spec §FR-015]
- [ ] CHK011 - Do FR-015 (atomic lock on save) and FR-015c (deferred lock when owner is actively editing) contradict each other? Is the priority between these two requirements explicitly resolved? [Consistency, Spec §FR-015, §FR-015c]
- [ ] CHK012 - Is the deferred lock mechanism in FR-015c defined with a complete state transition: what lock state is the document in during the deferral window, and can it be committed or exported during that window? [Clarity, Spec §FR-015c]
- [ ] CHK013 - Are lock state transitions for Standard vs. Safety-critical documents clearly distinguished in terms of who can trigger each transition and what lifecycle state changes accompany each? [Clarity, Spec §FR-013, §FR-014]
- [ ] CHK014 - Is "PM or department manager" in FR-014b (Emergency Override) a formally defined RBAC role that maps to the role definitions in FR-005, or is it an informal description? [Clarity, Spec §FR-014b, §FR-005]
- [ ] CHK015 - Are complete audit trail requirements defined for every lock state transition — specifically, must every state change (including deferred lock application and Emergency Override) be logged with actor and timestamp? [Completeness, Spec §FR-011, §FR-014b]
- [ ] CHK016 - Is there a requirement defining what happens to a locked document when the responsible owner's account is deactivated (e.g., employee departure)? Who inherits unlock authority? [Gap]
- [ ] CHK017 - Is the BU-scoped cascade lock (FR-041) consistent with cross-BU dependency relationships (FR-019)? Does a cross-BU Blocked By relationship bypass or interact with BU-scoped locking? [Consistency, Spec §FR-041, §FR-019]
- [ ] CHK018 - Are requirements specified for what happens to documents in "Pending QRA Approval" state when the assigned QRA auditor's account is deactivated or reassigned? [Gap]

---

## Circular Dependency Detection

- [ ] CHK019 - Is the scope of circular dependency detection clearly bounded — is it limited to Blocking/Blocked By relationships only, or does it also apply to Related/Ref. chains? [Clarity, Spec §FR-015d]
- [ ] CHK020 - Is "resolved by a human" (FR-015d) sufficiently specified — does resolution require deleting the flagged relationship, or are other paths (e.g., converting to Related) acceptable, and must the resolution action be logged? [Clarity, Spec §FR-015d]
- [ ] CHK021 - Are latency requirements defined for the asynchronous circular dependency detection scan — how quickly after saving must the system complete the cycle check and send notifications? [Gap]
- [ ] CHK022 - Is the behavior defined when a circular dependency is created in a document that is currently in LOCKED state — does the detection proceed, and does the notification reach the locked document's owner? [Gap]
- [ ] CHK023 - Are circular dependency detection requirements defined for cross-BU dependency chains — can a cycle span two BUs, and does the notification system reach owners across BU boundaries? [Coverage, Gap]
- [ ] CHK024 - Is there a requirement for how "Circular Dependency Warning" flags in the dependency graph are cleared — only upon human resolution, or also upon document deletion or relationship removal? [Clarity, Spec §FR-015d]

---

## OBSOLETE Document Impact Chain

- [ ] CHK025 - Is the "Upstream Obsolete Warning" notification content specified with sufficient precision — must it include the name of the OBSOLETE document, the specific affected Spec items, and the type of relationship (Blocking / Blocked By / Related)? [Clarity, Spec §FR-039]
- [ ] CHK026 - Are the allowable preceding lifecycle states before OBSOLETE defined — can only APPROVED documents transition to OBSOLETE, or also REVIEW and DRAFT? [Gap]
- [ ] CHK027 - Is there a requirement specifying how long "Upstream Obsolete Warning" persists on downstream items — does it auto-clear when the downstream owner acknowledges it, or only when they manually remove the dependency? [Clarity, Spec §FR-039]
- [ ] CHK028 - Are requirements defined for exporting a document that has active "Upstream Obsolete Warning" flags — is export to CodeBeamer blocked, allowed with warnings, or silently permitted? [Gap]
- [ ] CHK029 - Is the OBSOLETE transition reversible? If a document is erroneously marked OBSOLETE, can it return to APPROVED, and are previously issued "Upstream Obsolete Warning" flags automatically retracted? [Gap]
- [ ] CHK030 - Are requirements defined for what happens to Blocking relationships when the upstream (blocking) document transitions to OBSOLETE — do downstream items remain locked indefinitely, or does the lock release automatically? [Gap]

---

## Traceability Matrix

- [ ] CHK031 - Are the four entity types in the traceability chain (requirement → design element → test case → evidence) each explicitly defined with their data model representation, or are they implied from context? [Clarity, Spec §FR-022]
- [ ] CHK032 - Is "broken link" in the traceability matrix defined — what conditions constitute a broken link (e.g., deleted target item, OBSOLETE upstream), and how must broken links be surfaced to users? [Clarity, Gap]
- [ ] CHK033 - Is the traceability matrix scope defined — does it cover all document types uniformly, or only specific Spec types (e.g., HW Architectural Design)? [Completeness, Spec §FR-022]
- [ ] CHK034 - Is there a latency requirement for traceability matrix updates after a document change — is this covered by SC-006 (<3 seconds), or does it have a separate, possibly longer acceptable latency? [Gap]
- [ ] CHK035 - Are acceptance criteria defined for traceability completeness — what percentage of Spec items must have a full requirement-to-evidence chain to pass a compliance check? [Gap]

---

## Dependency Graph — Completeness & Performance

- [ ] CHK036 - Is "auto-generated cross-document dependency graph visible to all roles" (FR-020) specified with minimum information requirements per node (e.g., document name, owner, lock state) and per edge (relationship type, directionality)? [Clarity, Spec §FR-020]
- [ ] CHK037 - Are performance requirements for the dependency graph defined under maximum scale conditions (e.g., 12 departments × 100+ Specs × 1,000+ items each)? [Gap]
- [ ] CHK038 - Is the dependency graph update mechanism defined as real-time reactive or batch/polling? Does SC-006 (<3 seconds) apply to the graph UI rendering, backend computation, or both? [Clarity, Spec §SC-006]
- [ ] CHK039 - Are filtering and navigation requirements defined for the dependency graph (e.g., filter by BU, document type, lock state, ASIL level)? [Gap]

---

## Notification Requirements for Dependency Events

- [ ] CHK040 - Are notification requirements for dependency change events (FR-021) explicitly distinguished from cascade lock notifications — do they use the same channel (in-app + email) or a separate mechanism? [Clarity, Spec §FR-021]
- [ ] CHK041 - Is "directly affected downstream documents" (FR-021) defined as first-level dependents only, or does it include all transitive dependents through the full dependency chain? [Clarity, Spec §FR-021]
- [ ] CHK042 - Are notification requirements for Related/Ref. changes differentiated from Blocking changes in terms of urgency level, notification channel, or required content? [Gap]

---

## Acceptance Criteria Quality & Non-Functional

- [ ] CHK043 - Is SC-006 (dependency graph update <3 seconds) defined with explicit test conditions — under what document size, number of concurrent users, and network conditions must this threshold be met? [Measurability, Spec §SC-006]
- [ ] CHK044 - Are requirements defined for dependency relationship data integrity when a Spec item is deleted — must all Blocking, Blocked By, and Related relationships that reference the deleted item be automatically cleaned up, and must impacted owners be notified? [Gap]
