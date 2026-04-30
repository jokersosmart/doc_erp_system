# CodeBeamer Export Schema Contract: DocERP

**Phase**: 1 — Design  
**Date**: 2026-04-29  
**Related**: [rest-api.md](./rest-api.md) | [data-model.md](../data-model.md)

---

## Overview

DocERP generates a `.xlsx` export file matching Siliconmotion's Hardware Architectural Design template **RD-03-010-09**. This contract defines the authoritative column structure, types, and validation rules used by both the export generator and the post-generation validator (FR-024, FR-026, FR-044).

The column definition is stored in the `codebeamer_schema_definitions` table (data-model.md §15) and can be updated by administrators when CodeBeamer is upgraded.

---

## Column Definitions (RD-03-010-09 baseline)

| Order | Column Name | Type | Required | Notes |
|-------|-------------|------|----------|-------|
| 1 | Status | ENUM | Yes | DRAFT / REVIEW / APPROVED / OBSOLETE |
| 2 | Safety Related | BOOLEAN | Yes | Yes / No |
| 3 | Source HSR | TEXT | No | Comma-separated upstream HSR IDs |
| 4 | Source HSI | TEXT | No | Comma-separated upstream HSI IDs |
| 5 | SM ID | TEXT | Yes | e.g., SM-001 |
| 6 | SM Type | ENUM | Yes | Functional / Non-functional / Safety / Security |
| 7 | Reaction in case diagnostics detects a fail | TEXT | No | |
| 8 | FDTI | TEXT | No | Fault Detection Time Interval (ISO-26262 format) |
| 9 | FRTI | TEXT | No | Fault Reaction Time Interval |
| 10 | FHTI | TEXT | No | Fault Handling Time Interval |
| 11 | Diagnostic Coverage | PERCENTAGE | No | e.g., 90% — stored as numeric 0.0–1.0, rendered as % |
| 12 | Ref. | TEXT | No | Related (non-blocking) references; comma-separated item IDs |
| 13 | Verification | TEXT | No | Linked test case IDs or descriptions |
| 14 | Dependency | TEXT | No | Blocking / Blocked By item IDs; format: `BLOCKING:SM-002,BLOCKED_BY:HSR-001` |
| 15 | CC-ID | TEXT | No | Common Cause ID |
| 16 | CC Type | TEXT | No | Common Cause Type |
| 17 | Source HCR-ID | TEXT | No | Upstream HCR reference |
| 18 | Reaction / Response | TEXT | No | Safety response / reaction description |
| 19 | Verification 驗證 | TEXT | No | Secondary verification field (bilingual column name) |

---

## Validation Rules

Post-generation validation checks the following per row:

| Rule ID | Column | Check | Severity |
|---------|--------|-------|----------|
| V-001 | Status | Must be one of DRAFT / REVIEW / APPROVED / OBSOLETE | ERROR |
| V-002 | Safety Related | Must be 'Yes' or 'No' (boolean coercion) | ERROR |
| V-003 | SM ID | Must be non-empty and match pattern `[A-Z]{2,10}-[0-9]+` | ERROR |
| V-004 | SM Type | Must be one of allowed ENUM values | ERROR |
| V-005 | Diagnostic Coverage | If Safety Related = Yes and ASIL ≥ B: must be present and ≥ 60% | WARNING |
| V-006 | FDTI / FRTI / FHTI | If Safety Related = Yes: at least one must be present | WARNING |
| V-007 | Column order | All 19 columns must appear in exact order defined above | ERROR |
| V-008 | Column count | Sheet must have exactly 19 columns (no extra or missing) | ERROR |

---

## File Structure

```
<archive_name>/
├── spec_items_export.xlsx     # Main export matching RD-03-010-09
├── fmeda_export.xlsx          # FMEDA worksheets (if applicable)
├── compliance_check.json      # Compliance gap report
└── validation_report.json     # Post-gen validation results (FR-044)
```

---

## `validation_report.json` Schema

```json
{
  "schema_version": "CB-2024.1",
  "validation_passed": false,
  "issues": [
    {
      "rule_id": "V-005",
      "severity": "WARNING",
      "column_name": "Diagnostic Coverage",
      "row_reference": "Row 12 (SM-011)",
      "expected": "Value >= 60% required for ASIL-B Safety Related items",
      "found": "empty",
      "recommended_action": "Add Diagnostic Coverage value to SM-011 before importing to CodeBeamer."
    }
  ]
}
```
