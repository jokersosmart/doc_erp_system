# Quickstart: DocERP Core Workflow and Traceability

This guide is for implementing and validating the feature plan in incremental slices.

## 1. Prerequisites

- Python 3.11+
- PostgreSQL 15+
- PowerShell (Windows) or compatible shell
- Repository checked out on branch 002-doce-erp-dms

## 2. Backend Environment Setup

From repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Create backend/.env (or set environment variables):

```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://doce_erp:changeme@localhost:5432/doce_erp
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me
```

## 3. Database Initialization

```powershell
cd backend
alembic upgrade head
```

Expected result:
- All baseline tables plus feature tables are created successfully.
- Enum creation is idempotent across repeated migration runs.

## 4. Run API Locally

```powershell
cd backend
uvicorn app.main:app --reload
```

Health check:
- GET /health returns 200 with status ok.

## 5. Implementation Slices

## Slice A: Document lifecycle and revision control

- Add models and migrations for DocumentRevision and DocumentTransitionEvent.
- Implement lifecycle transition service with validation and authorization hooks.
- Add APIs:
  - POST /documents
  - PUT /documents/{documentId}
  - POST /documents/{documentId}/transitions
- Add tests:
  - unit: transition rules and validation failures
  - integration: immutable approved revision behavior

Done criteria:
- DRAFT -> REVIEW blocks when required attributes are missing.
- APPROVED revisions cannot be directly edited.

## Slice B: Traceability and suspect management

- Extend DependencyLink with health status fields.
- Add SuspectResolution model and service logic.
- Implement APIs:
  - POST /traceability/links
  - GET /documents/{documentId}/impacts
  - POST /traceability/links/{linkId}/resolve
- Add tests for circular dependency prevention and suspect propagation.

Done criteria:
- Upstream approved revision changes mark downstream links SUSPECT.
- Resolution is recorded with actor/timestamp/rationale.

## Slice C: AI compliance review workflow

- Add AIReviewJob, AIReviewFinding, AISuggestionDecision models.
- Implement durable async state handling with retryable status.
- Implement APIs:
  - POST /ai/reviews
  - GET /ai/reviews/{jobId}
  - POST /ai/reviews/{jobId}/suggestions/{suggestionId}/decisions
- Add tests for delayed/partial/unavailable AI scenarios.

Done criteria:
- Job state is preserved across service restart.
- Accept/reject decisions are auditable and queryable.

## Slice D: Export package and validation reporting

- Add ExportJob, ExportArtifact, ExportIssue models.
- Implement package assembly and validation report generation.
- Implement APIs:
  - POST /exports
  - GET /exports/{jobId}
- Persist generated artifact metadata under backend/storage/audit_packages.

Done criteria:
- Validation issues are returned with actionable entity references.
- One-way sync boundary is preserved.

## 6. Test Execution

```powershell
cd backend
pytest
```

Recommended grouping while developing:

```powershell
pytest tests/unit
pytest tests/integration
pytest tests/contract
```

## 7. Contract and Documentation Checks

- Keep API implementation aligned with contracts/rest-api.yaml.
- Keep migration and model changes aligned with data-model.md.
- Keep acceptance behavior aligned with spec.md scenarios and FR list.

## 8. Operational Validation Targets

- 95% interactive operations <= 3 seconds.
- 90% AI review jobs return first actionable findings <= 10 seconds.
- 100% dependency and lifecycle changes create audit evidence records.

## 9. Impact Analysis Commands (Cross-Document SUSPECT Validation)

From repository root:

```powershell
cd hyperframes_relation_viz
npm install
npm run build:data
npm run analyze:impact
```

Optional: analyze a focused file set with explicit depth.

```powershell
node .\scripts\analyze-impact.mjs --changed specs/002-doce-erp-dms/spec.md,backend/app/services/dependency_engine.py --depth 2
```

Expected outputs:

- `hyperframes_relation_viz/data/relations.json`
- `hyperframes_relation_viz/data/impact-report.json`

Validation checkpoints:

- `impact-report.json` includes `changed` and `suspect_*` candidate lists.
- Navigation metadata (`from`, `to`, `returnTo`) is available on impacted items.
