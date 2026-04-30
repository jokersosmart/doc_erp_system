# UX / Interaction Requirements Quality Checklist: DocERP

**Purpose**: Author self-review — validate completeness, clarity, and consistency of UX/Interaction requirements before PR submission  
**Created**: 2026-04-29  
**Feature**: [spec.md](../spec.md)  
**Depth**: Thorough (~46 items)  
**Domain**: UX / Interaction — Role Dashboards, AI Wizard, AI Consultant Side Panel, Cascade Lock UI, Dependency Graph, Audit Export UI  
**Audience**: Author (pre-PR self-validation)

---

## Role-Specific Dashboards

- [ ] CHK001 - Are the exact content elements of each role-specific dashboard (PM, RD, Auditor) specified with their required information hierarchy, or only described with subjective terms like "clean" and "at a glance"? [Clarity, Ambiguity, Spec §UX]
- [ ] CHK002 - Is the PM cross-department dependency map's visual representation type (graph / table / tree) specified, or left open to implementation interpretation? [Clarity, Gap]
- [ ] CHK003 - Are dashboard loading state requirements defined for scenarios where dependency graph data is slow to fetch (>3s)? [Coverage, Gap]
- [ ] CHK004 - Are refresh frequency requirements for compliance maturity metrics displayed on dashboards defined (real-time, on-demand, scheduled)? [Completeness, Gap]
- [ ] CHK005 - Are requirements defined for what each role sees when their project has zero documents yet (empty state / zero-state)? [Coverage, Gap]

---

## AI Onboarding Wizard

- [ ] CHK006 - Is the exact sequence and minimum required content of each of the 6–8 wizard questions specified, or only the question count? [Clarity, Spec §FR-006]
- [ ] CHK007 - Are input validation rules defined for each wizard question (e.g., ASIL must be one of A/B/C/D; ASPICE level must be 1–5)? [Completeness, Spec §FR-006]
- [ ] CHK008 - Is error handling defined for conflicting wizard selections (e.g., selecting ISO-26262 ASIL-D for a BU whose standard template does not support it)? [Coverage, Gap]
- [ ] CHK009 - Are the UI requirements for the wizard resume prompt specified — what options are shown ("Continue" / "Start Over"), how is remaining progress indicated? [Clarity, Spec §FR-043]
- [ ] CHK010 - Is the 90-day wizard session expiry behavior fully specified — when the email is sent, what happens to in-progress data upon expiry, and what the user sees on next login? [Completeness, Spec §FR-043]
- [ ] CHK011 - Are requirements defined to visually differentiate SSD Controller BU wizard flows from eMMC BU wizard flows when the applicable standards differ? [Completeness, Spec §FR-002]

---

## AI Consultant Side Panel

- [ ] CHK012 - Is the information structure of each suggestion card in the side panel specified — must it show gap description, suggested content, standard clause reference, and Accept/Reject controls as distinct elements? [Completeness, Spec §FR-007, §FR-009]
- [ ] CHK013 - Is the visual distinction between AI-suggested content (in the side panel) and existing document content (in the editor) specified with measurable criteria? [Clarity, Spec §FR-007]
- [ ] CHK014 - Is "inserted at the correct position" (for accepted suggestions) defined with an unambiguous rule — e.g., immediately after the gap paragraph, at cursor position, or at the section end? [Ambiguity, Spec §FR-007]
- [ ] CHK015 - Are side panel behavior requirements defined for offline/fallback mode — does it show fewer suggestions, different labels, or a degraded-mode indicator? [Completeness, Spec §FR-033b]
- [ ] CHK016 - Is the offline/fallback mode banner or indicator specified with required content (what it says, where it appears, whether it is dismissible)? [Clarity, Spec §FR-033b]
- [ ] CHK017 - Are requirements defined for the maximum number of suggestions the side panel can display, and how overflow is handled (pagination, scroll, load-more)? [Completeness, Gap]
- [ ] CHK018 - Is the audit trail entry's format and visibility during editing specified — does the engineer see the "Suggested by AI, accepted by…" log inline or only in the audit trail view? [Clarity, Spec §FR-008]

---

## Cascade Lock UI

- [ ] CHK019 - Are the visual specifications for the red LOCKED banner defined — required page position (header overlay, sticky banner, modal), mandatory content fields, and minimum contrast ratio? [Clarity, Spec §FR-012, §US3-AC2]
- [ ] CHK020 - Are the yellow "Pending QRA Approval" and green "Approved/Unlocked" banner requirements defined with equal specificity to the red LOCKED banner (position, content, contrast)? [Consistency, Spec §FR-014, §US3-AC4, §US3-AC5]
- [ ] CHK021 - Is the inline diff view's required information defined — must it show changed lines, change author, timestamp, and affected standard clause? Or only changed text? [Clarity, Spec §FR-017, §US3-AC2]
- [ ] CHK022 - Is the "Mark as Reviewed & Updated" action's confirmation flow specified — is there a confirmation dialog to prevent accidental clicks, and what is shown if the owner clicks it before reviewing the diff? [Completeness, Spec §FR-013]
- [ ] CHK023 - Are UI requirements for the Emergency Override action defined — who can see the button (PM/manager only), where it appears relative to the Pending QRA state, and what input fields are required (reason text field mandatory)? [Completeness, Spec §FR-014b]
- [ ] CHK024 - Is the QRA auditor's review interface specified — what document information, diff view, and actions (Approve / Request Revision with mandatory comment field) must be present? [Completeness, Spec §US3-AC5, §US3-AC6]
- [ ] CHK025 - Are requirements defined for the project dashboard's view of all documents currently LOCKED or Pending QRA Approval — is this a dedicated section, a filter, or inline indicators? [Completeness, Spec §FR-012]
- [ ] CHK026 - Is the deferred lock notification (shown to the owner after their save completes and the lock then applies) specified — timing, visual prominence, and content? [Clarity, Spec §FR-015c]

---

## Optimistic Locking / Conflict Resolution UI

- [ ] CHK027 - Is the three-way merge interface fully specified — must it show "my changes," "base (common ancestor)," and "their changes" as three distinct panels? [Completeness, Spec §FR-015b]
- [ ] CHK028 - Is it specified which user sees the merge interface (the one who saves second), and what feedback the first user who saved successfully receives? [Clarity, Spec §FR-015b]
- [ ] CHK029 - Are requirements defined for the post-merge flow — after the human resolves and confirms the merge, does the result require an additional explicit save action before it is committed? [Completeness, Gap]

---

## Dependency Graph

- [ ] CHK030 - Is the dependency graph's visual differentiation between Blocking, Blocked By, and Related relationship types specified (distinct colors, line styles, icons, or labels)? [Completeness, Spec §FR-018, §FR-020]
- [ ] CHK031 - Is the "Circular Dependency Warning" flag's visual representation in the dependency graph fully specified — color, icon, tooltip content, and whether the flagged edge is highlighted? [Clarity, Spec §FR-015d]
- [ ] CHK032 - Is the "Upstream Obsolete Warning" flag's visual representation in both the dependency graph and the individual Spec Item view specified with the same level of detail? [Clarity, Consistency, Spec §FR-039]
- [ ] CHK033 - Are requirements defined for navigating or filtering large dependency graphs (e.g., 100+ nodes across 12 departments and 5 org levels) — zoom, search, filter by BU, collapse? [Coverage, Gap]
- [ ] CHK034 - Is a loading/recalculating indicator specified for the dependency graph during the ≤3-second post-save update window? [Completeness, Spec §SC-011]

---

## Audit & Compliance Export UI

- [ ] CHK035 - Is the compliance gap report's structure defined — required fields per gap item (gap description, standard clause, affected document, severity level, responsible owner)? [Completeness, Spec §FR-023, §US4-AC1]
- [ ] CHK036 - Is the Audit Package History page's required information per row specified — timestamp format, triggering username, download link, file size display? [Completeness, Spec §FR-045]
- [ ] CHK037 - Is the storage usage warning's display location and content specified — is it a dashboard widget, a sticky banner, a toast, and what does the threshold percentage message say? [Clarity, Spec §FR-045]
- [ ] CHK038 - Is the CodeBeamer export "potential problems" list's format defined — table structure, column headers (field name / expected format / actual value / suggested fix), and severity classification? [Clarity, Spec §FR-044]

---

## Localisation (Dual-Language UI)

- [ ] CHK039 - Is there an explicit list or rule specifying which technical terms must NOT be translated (e.g., ASIL, CAL, SPFM, LFM, PMHF, FMEDA) in both Traditional Chinese and English modes? [Completeness, Spec §FR-040]
- [ ] CHK040 - Is the location of the language switcher control specified (global header, user profile menu, settings page) and consistent across all pages? [Clarity, Spec §FR-040]
- [ ] CHK041 - Are requirements defined for how mixed-language content is handled — e.g., an English document title displayed in a Traditional Chinese UI, or a user-entered English free-text note? [Coverage, Gap]

---

## Non-Functional: Accessibility & Responsiveness

- [ ] CHK042 - Are accessibility requirements defined for the dependency graph — specifically keyboard navigation between graph nodes and screen reader support for relationship types? [Coverage, Gap]
- [ ] CHK043 - Are minimum color-contrast ratios specified for the red/yellow/green lock state banners to confirm WCAG AA compliance (≥4.5:1 for normal text, ≥3:1 for large text)? [Completeness, Gap]
- [ ] CHK044 - Are responsive design breakpoints or minimum viewport requirements defined for the AI consultant side panel (which appears alongside the document editor, requiring significant horizontal space)? [Coverage, Gap]

---

## In-App Notification System

- [ ] CHK045 - Is the required content structure of in-app notifications specified — notification type label, affected document name, action required, direct link to document, timestamp? [Completeness, Gap]
- [ ] CHK046 - Are requirements defined for the notification centre / inbox — retention period, read/unread state, dismiss action, and maximum number of stored notifications per user? [Completeness, Gap]
