# Stage Snapshot (2026-05-22)

## What Works

- US1 document lifecycle endpoints are available under `/api/v1/documents`:
  - `POST /documents`
  - `GET /documents/{documentId}`
  - `PUT /documents/{documentId}`
  - `POST /documents/{documentId}/transitions`
  - `POST /documents/convert`
- US1 lifecycle and EAV data layer is present:
  - Document lifecycle fields (`standards_scope`, `last_transition_at`)
  - Revision and transition event models
  - Standard and requirement models
  - Attribute definition/value models
  - Migration `0003_document_lifecycle_and_eav.py`
- US1 validation and orchestration services are implemented:
  - `attribute_validation_service`
  - `document_lifecycle_service`
- US1 test baseline has passing suites:
  - Contract: document endpoint shape checks
  - Integration: lifecycle transition behavior
  - Unit: required attribute validation logic
- Last known backend baseline:
  - `pytest -q`: 15 passed
  - `pytest tests/integration/test_document_lifecycle.py -q`: 3 passed

## What Is Pending

- US2 implementation has not started in runtime paths:
  - No traceability route implementation yet
  - No suspect propagation service yet
  - No US2 migration (`0004`) yet
- US3 and US4 remain unimplemented:
  - No AI review models/services/routes
  - No export job models/services/routes
- Cross-cutting hardening still pending:
  - Full migration smoke coverage for new phases
  - OpenAPI full reconciliation for all planned stories
  - Localization/message catalog completion

## Risk Notes

- Existing task checkboxes and code can drift; keep tasks updated per merged implementation.
- US2 depends on stable lifecycle revision behavior from US1; avoid changing US1 payload semantics during US2 kickoff.

## Next Slice Recommendation

Implement US2 minimum vertical slice in this order:
1. Add schema stubs for link creation and suspect resolution payloads.
2. Add migration for dependency link health + suspect resolution record.
3. Add minimal endpoints for create link, mark suspect, resolve suspect.
4. Add contract + integration tests for suspect propagation from upstream approved change.
