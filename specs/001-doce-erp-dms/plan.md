# Implementation Plan: DocERP — Spec-Driven Document Management System

**Branch**: `002-doce-erp-dms` | **Date**: 2026-04-29 | **Spec**: [specs/001-doce-erp-dms/spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-doce-erp-dms/spec.md`

## Summary

DocERP is an on-premise, spec-driven document management ERP for Siliconmotion, purpose-built for ASPICE 3.1, ISO-26262, and ISO-21434 compliance workflows. The system manages versioned documents across a 5-level org hierarchy and two BUs, enforces bi-directional traceability through a typed dependency graph, automates cascade locking when upstream Specs change, and provides an AI compliance consultant (suggestion-only, human-in-the-loop) backed by RAG over licensed standard texts. All data remains on-premise; only minimal Spec context is sent to an external LLM API per query. Secondary modules include FMEDA automation and a one-way CodeBeamer Excel export pipeline.

Technical approach: Python 3.11 (FastAPI) backend + React 18 (TypeScript) frontend + PostgreSQL EAV data model + Celery/Redis async task queue for dependency propagation + GitPython abstraction layer + LangChain RAG pipeline.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x / React 18 (frontend), Node 20 (build tooling)
**Primary Dependencies**: FastAPI 0.110+, SQLAlchemy 2.x (async), Celery 5.x, Redis 7.x, LangChain 0.2+, openpyxl 3.x, GitPython 3.x, python-ldap 3.x, Alembic (migrations)
**Storage**: PostgreSQL 16 (primary — mandated by constitution; EAV schema), Redis 7 (task queue + session cache), on-premise Git repositories (Gerrit / GitHub / GitLab)
**Testing**: pytest + pytest-asyncio + httpx (backend), Vitest + React Testing Library (frontend), Playwright (E2E)
**Target Platform**: Linux server on-premise (Docker / docker-compose), Desktop browsers (Chrome, Edge, Firefox latest)
**Project Type**: Full-stack web application (REST API service + SPA frontend)
**Performance Goals**: Dependency graph update < 3 s after document save (SC-003); AI suggestion generation < 10 s; page load < 2 s; Git commit round-trip < 5 s
**Constraints**: 100+ concurrent users (SC-004); 99.5% monthly uptime (SC-007); Git sync failure < 0.1% (SC-009); no full document content leaves the on-premise network; CodeBeamer import success > 99% (SC-008)
**Scale/Scope**: 12 departments, 5 org levels, 2 BUs, ~46 FRs, 9 core entities, 3-phase rollout

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status | Notes |
|-----------|------|--------|-------|
| I. SDD — 規格驅動開發 | All features traceable to spec FR-XXX | ✅ PASS | Plan derived directly from 46 FRs in spec.md |
| II. Automated Traceability | Bi-directional traceability engine present | ✅ PASS | FR-018–022 define dependency graph + cascade lock |
| III. AI-Assisted Compliance | AI suggestion-only, human-in-the-loop | ✅ PASS | FR-007–009 mandate suggestion panel + audit log |
| IV. Dynamic Standard Extension | EAV architecture; no hardcoded standard columns | ✅ PASS | FR-034–035 mandate EAV + schema versioning |
| V. Structured Exportability | xlsx/XML export, CodeBeamer mapping | ✅ PASS | FR-024–026 define export pipeline |
| Data Model: UUID PKs | All core entities use UUID | ✅ PASS | All 9 Key Entities carry UUID |
| Data Model: State Machine | DRAFT→REVIEW→APPROVED→OBSOLETE enforced | ✅ PASS | FR-012–014 + Clarification Q1 |
| Data Model: PostgreSQL | Core data in PostgreSQL | ✅ PASS | Mandated by constitution; Redis is queue/cache only |
| Governance: Complexity Control | New tools justified in spec | ✅ PASS | Celery + Redis justified by SC-003 async constraint |

**Pre-Phase 0 Gate Result: ALL PASS — proceed to research.**

## Project Structure

### Documentation (this feature)

```text
specs/001-doce-erp-dms/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── rest-api.md      # REST API contract (FastAPI routes)
│   ├── events.md        # Async event/task contract (Celery)
│   └── export-schema.md # CodeBeamer xlsx column schema
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── documents.py       # Document CRUD, lifecycle, lock endpoints
│   │   │   ├── spec_items.py      # Spec Item + dependency endpoints
│   │   │   ├── projects.py        # Project & org setup endpoints
│   │   │   ├── ai.py              # AI consultant + wizard endpoints
│   │   │   ├── audit.py           # Compliance check + export endpoints
│   │   │   ├── fmeda.py           # FMEDA module endpoints
│   │   │   └── auth.py            # LDAP + local auth endpoints
│   │   └── deps.py                # Shared FastAPI dependencies (auth, db)
│   ├── models/
│   │   ├── org.py                 # Organisation, Project, BU
│   │   ├── document.py            # Document, lifecycle state machine
│   │   ├── spec_item.py           # SpecItem, DependencyLink, AttributeValue
│   │   ├── lock_event.py          # LockEvent, CascadeLock
│   │   ├── fmeda.py               # FMEDAWorksheet, FailureModeLibrary
│   │   └── audit_package.py       # AuditPackage, ComplianceCheckResult
│   ├── services/
│   │   ├── dependency_engine.py   # Graph build, cycle detect, cascade lock
│   │   ├── ai_consultant.py       # RAG pipeline, suggestion generation
│   │   ├── git_abstraction.py     # Gerrit/GitHub/GitLab adapter
│   │   ├── export_service.py      # xlsx generation + CodeBeamer schema validation
│   │   ├── fmeda_calculator.py    # SPFM, LFM, PMHF computation
│   │   └── notification.py        # In-app + email notification dispatch
│   ├── tasks/
│   │   ├── cascade_lock.py        # Celery task: BU-scoped atomic lock propagation
│   │   ├── cycle_detection.py     # Celery task: async circular dependency scan
│   │   └── obsolete_scan.py       # Celery task: downstream Obsolete Warning scan
│   ├── core/
│   │   ├── config.py              # Settings (env vars, LDAP, DB, Redis, LLM)
│   │   ├── database.py            # SQLAlchemy async engine + session
│   │   └── security.py            # LDAP bind, JWT, local-account fallback
│   └── migrations/                # Alembic migration scripts
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
└── pyproject.toml

frontend/
├── src/
│   ├── components/
│   │   ├── editor/                # Spec document editor + AI side panel
│   │   ├── dashboard/             # Role-specific dashboard widgets
│   │   ├── dependency/            # Dependency graph visualisation
│   │   ├── lock/                  # Lock banners, diff view, QRA approval flow
│   │   ├── fmeda/                 # FMEDA worksheet UI
│   │   └── wizard/                # AI onboarding wizard (step auto-save)
│   ├── pages/
│   ├── services/                  # API client, WebSocket (notifications)
│   └── i18n/                      # zh-TW + en locale files
├── tests/
└── package.json

docker-compose.yml                 # Local dev: postgres, redis, backend, frontend
```

**Structure Decision**: Web application (Option 2: backend + frontend) — DocERP is a browser-based SPA backed by a REST API service. Separated to allow independent scaling and for the on-premise Docker deployment model.

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
|----------|------------|--------------------------------------|
| Celery + Redis task queue | Async cascade lock propagation must complete in < 3 s (SC-003) across potentially many dependent docs without blocking the HTTP response | Synchronous propagation in the HTTP request would timeout under load; threading without a queue has no retry/dead-letter guarantees |
| EAV attribute schema (PostgreSQL) | FR-035: schema must evolve per document type without migrations breaking existing records | Fixed-column schema cannot accommodate incremental addition of doc-type-specific fields (FW, SW, HW, Architect templates not yet finalised — A-008) |
| LangChain RAG pipeline | FR-007/009: AI must cite specific standard clauses and operate offline-fallback mode — requires structured retrieval over ASPICE/ISO texts | Direct LLM prompt without RAG cannot guarantee clause-level citation accuracy needed for ISO-26262 audit defensibility |
| GitPython multi-backend abstraction | FR-031: supports Gerrit, GitHub, GitLab from a single UI | Direct Gerrit/GitHub SDKs per backend would require three separate codepaths and engineer-visible config differences |
