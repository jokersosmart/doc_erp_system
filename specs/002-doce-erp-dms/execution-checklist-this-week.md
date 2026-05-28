# Execution Checklist (Today to This Week)

## Scope

Stabilize current US1 baseline, then prepare entry to US2 implementation.

## Today

- [x] Fix backend test environment dependency gap (`httpx`)
- [x] Run full backend tests and capture baseline status
- [x] Remove lifecycle integration warning caused by improper async mocking
- [x] Verify document lifecycle API behavior against contract examples (`/documents`, `/documents/{id}`, `/documents/{id}/transitions`)
- [x] Freeze US1 API response shape and error code mapping notes

## Tomorrow

- [x] Add stage snapshot report (`what works / what is pending`) in `specs/002-doce-erp-dms/`
- [x] Add US2 kickoff schema stubs: traceability link payload and suspect resolution payload
- [x] Draft migration plan for US2 entities (dependency health + suspect resolution)

## This Week

- [x] Implement US2 minimum slice (create link + mark suspect + resolve suspect)
- [x] Add contract tests for US2 minimum slice
- [x] Add integration test for suspect propagation from upstream change
- [x] Add one reviewer workflow run using impact report output and record findings
- [x] Update quickstart runbook with impact-analysis commands

### Reviewer Workflow Run (2026-05-25)

- Commands executed in `hyperframes_relation_viz/`: `npm run build:data`, `npm run analyze:impact`
- Impact summary: `changed=6`, `suspect_document=58`, `suspect_paragraph=0`, `suspect_trace=0`, `suspect_clause=0`, `suspect_checklist=0`
- Sample suspect documents: `backend/app/api/router.py`, `backend/app/core/config.py`, `backend/app/core/database.py`
- Navigation payload check: navigation metadata exists on all suspect items (`58/58`)

## Current Baseline (Auto-verified)

- Backend tests: 15 passed (`pytest -q`)
- Lifecycle integration tests: 3 passed (`pytest tests/integration/test_document_lifecycle.py -q`)
- Last validation timestamp: 2026-05-22
- Impact workflow: available under `hyperframes_relation_viz/` and executable
