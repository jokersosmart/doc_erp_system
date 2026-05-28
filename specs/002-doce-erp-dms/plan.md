# Implementation Plan: DocERP Core Workflow and Traceability

**Branch**: `002-doce-erp-dms` | **Date**: 2026-04-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-doce-erp-dms/spec.md`

## Summary

Deliver a backend-first implementation of DocERP core workflow capabilities: controlled document lifecycle, dynamic attributes (EAV), bi-directional traceability with automatic SUSPECT propagation, AI-assisted compliance review workflow, and structured audit export. The plan extends the existing FastAPI + SQLAlchemy foundation and defines contract-first REST interfaces so Phase 2 task generation can split execution into independent vertical slices with testable outcomes.

## Technical Context

**Language/Version**: Python 3.11 (backend), SQL migrations via Alembic
**Primary Dependencies**: FastAPI, SQLAlchemy asyncio, asyncpg, Alembic, Pydantic v2, pydantic-settings
**Storage**: PostgreSQL (primary relational store), filesystem export artifacts under `backend/storage/audit_packages`
**Testing**: pytest, pytest-asyncio, migration smoke tests, unit/integration tests, new contract tests for API schemas
**Target Platform**: Internal enterprise web application (backend API on Linux container/server; developer workflow includes Windows)
**Project Type**: Web application monorepo (implemented backend, contract-first frontend consumer)
**Performance Goals**: 95% of interactive operations <= 3s; 90% of AI review first findings <= 10s; impacted link marking visible <= 1 minute
**Constraints**: Enforce UUID primary keys, lifecycle state machine, RBAC + partition scope, immutable audit evidence, one-way export sync, no hardcoded per-standard document columns
**Scale/Scope**: Support >=5 organization levels and >=12 parallel departments per process layer; multi-project document graphs with dependency impact views

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Assessment

| Principle / Rule | Status | Plan Coverage |
|------------------|--------|---------------|
| I. Specification-Driven Development | PASS | Scope, contracts, data model, and quickstart all derived from `spec.md` before implementation tasks |
| II. Automated Traceability | PASS | Includes dependency link health transitions, SUSPECT propagation, impact analysis outputs, and resolution evidence |
| III. AI-Assisted Compliance | PASS | Defines advisory AI review jobs, finding/suggestion capture, and human accept/reject decision records |
| IV. Dynamic Standard Extension (EAV) | PASS | Adds attribute definition/value model scoped by standard and partition; avoids hardcoded standard-specific columns |
| V. Structured Exportability | PASS | Defines structured export package schema, validation report, and one-way synchronization boundary |
| Data Model Standard: UUID keys | PASS | All new entities use UUID as primary key |
| Data Model Standard: Lifecycle and dependency state machines | PASS | Explicit transition rules defined in `data-model.md` |
| Data Model Standard: Relational DB (PostgreSQL) | PASS | Existing PostgreSQL stack retained and extended |

### Post-Phase 1 Re-check

Re-checked after creating `research.md`, `data-model.md`, `contracts/rest-api.yaml`, and `quickstart.md`: all constitution gates remain PASS with no required exceptions.

## Project Structure

### Documentation (this feature)

```text
specs/002-doce-erp-dms/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── rest-api.yaml
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── core/
│   ├── models/
│   ├── services/
│   ├── api/                 # to be added in this feature
│   └── schemas/             # to be added in this feature
├── migrations/
│   └── versions/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/            # to be added in this feature
└── storage/
    └── audit_packages/

frontend/
├── src/
│   └── components/
│       ├── dashboard/
│       ├── dependency/
│       ├── fmeda/
│       └── lock/
└── tests/
    └── e2e/
```

**Structure Decision**: Use the existing backend/frontend monorepo structure. Implement feature-critical domain behavior and APIs in `backend/` first, then expose stable contracts for frontend and external integration consumers.

## Complexity Tracking

No constitution violations identified; no complexity exception tracking required.
