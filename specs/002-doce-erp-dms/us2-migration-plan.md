# US2 Migration Plan (Dependency Health + Suspect Resolution)

## Goal

Prepare database changes for User Story 2 minimum slice:
- Track dependency link health state transitions.
- Record suspect resolution evidence with actor and rationale.

## Migration Target

- File: `backend/migrations/versions/0004_traceability_suspect_management.py`
- Down revision: `0003_document_lifecycle_and_eav`

## Schema Changes

### 1) Extend `dependency_links`

Add fields:
- `health_state` (enum/string): `HEALTHY | SUSPECT | RESOLVED`
- `suspect_reason` (text, nullable)
- `last_health_transition_at` (timestamp with timezone, nullable)
- `last_health_transition_by` (uuid, nullable)

Add indexes:
- `(downstream_item_id, health_state)` for impact listing
- `(upstream_item_id, health_state)` for propagation scans

### 2) Add `suspect_resolutions`

New table columns:
- `id` uuid primary key
- `dependency_link_id` uuid not null fk -> `dependency_links.id`
- `resolution_action` text not null
- `rationale` text not null
- `evidence_ref` text nullable
- `resolved_by` uuid not null fk -> `users.id`
- `resolved_at` timestamp with timezone not null default now

Add indexes:
- `ix_suspect_resolutions_dependency_link_id`
- `ix_suspect_resolutions_resolved_at`

## Data Safety and Rollback

- New columns are additive and nullable first, so rollback risk is low.
- Downgrade should drop `suspect_resolutions` first, then new indexes, then new columns.
- Do not backfill health state in migration; initialize in service layer for first US2 slice.

## Validation Checklist

- Alembic upgrade from clean database succeeds.
- Alembic downgrade/upgrade cycle succeeds for 0004.
- Existing US1 tests remain green after migration introduction.
- New US2 migration smoke test validates enum/index/table presence.
