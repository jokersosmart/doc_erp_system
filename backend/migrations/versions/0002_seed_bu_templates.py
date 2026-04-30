"""Seed BU templates, organisation_nodes, attribute_definitions.

T033: Initial data migration.
Revision: 0002_seed_bu_templates
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column, String, Boolean, Integer, JSON, DateTime, UUID

# revision identifiers
revision = "0002_seed_bu_templates"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

# ── Helper tables for inserts ─────────────────────────────────────────────────

org_nodes = table(
    "organisation_nodes",
    column("id", UUID),
    column("name", String),
    column("level", Integer),
    column("node_type", String),
    column("bu_scope", String),
    column("parent_id", UUID),
    column("created_at", DateTime),
)

attr_defs = table(
    "attribute_definitions",
    column("id", UUID),
    column("attribute_key", String),
    column("display_label", String),
    column("data_type", String),
    column("is_required", Boolean),
    column("schema_version", String),
    column("clause_reference", String),
    column("options_json", JSON),
    column("created_at", DateTime),
)


def upgrade() -> None:
    now = datetime.now(UTC)

    # ── Organisation nodes (root + BU nodes) ─────────────────────────────────
    root_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    ssd_bu_id = uuid.UUID("10000000-0000-0000-0000-000000000002")
    emmc_bu_id = uuid.UUID("10000000-0000-0000-0000-000000000003")
    nand_bu_id = uuid.UUID("10000000-0000-0000-0000-000000000004")

    op.bulk_insert(org_nodes, [
        {"id": root_id, "name": "Siliconmotion", "level": 0, "node_type": "COMPANY", "bu_scope": None, "parent_id": None, "created_at": now},
        {"id": ssd_bu_id, "name": "SSD Controller BU", "level": 1, "node_type": "BU", "bu_scope": "SSD_CONTROLLER", "parent_id": root_id, "created_at": now},
        {"id": emmc_bu_id, "name": "eMMC BU", "level": 1, "node_type": "BU", "bu_scope": "EMMC", "parent_id": root_id, "created_at": now},
        {"id": nand_bu_id, "name": "NAND Flash BU", "level": 1, "node_type": "BU", "bu_scope": "NAND_FLASH", "parent_id": root_id, "created_at": now},
    ])

    # ── Attribute Definitions: RD-03-010-09 base HW template fields ──────────
    # Per FR-034, FR-035: CC-ID, Status, Safety Related, Source HSR/HSI, etc.
    schema_v = "RD-03-010-09-v1"
    attr_rows = [
        {"key": "cc_id", "label": "CC-ID", "dtype": "string", "required": True, "clause": "RD-03-010-09 §4.1"},
        {"key": "cc_type", "label": "CC Type", "dtype": "enum", "required": True, "clause": "RD-03-010-09 §4.2"},
        {"key": "status", "label": "Status", "dtype": "enum", "required": True, "clause": "RD-03-010-09 §4.3"},
        {"key": "safety_related", "label": "Safety Related", "dtype": "boolean", "required": True, "clause": "ISO-26262 Part 8 Clause 6"},
        {"key": "source_hsr", "label": "Source HSR", "dtype": "string", "required": False, "clause": "ISO-26262 Part 3 Clause 7"},
        {"key": "source_hsi", "label": "Source HSI", "dtype": "string", "required": False, "clause": "ISO-26262 Part 4 Clause 8"},
        {"key": "sm_id", "label": "SM ID", "dtype": "string", "required": False, "clause": "RD-03-010-09 §5.1"},
        {"key": "sm_type", "label": "SM Type", "dtype": "enum", "required": False, "clause": "RD-03-010-09 §5.2"},
        {"key": "reaction_diagnostics", "label": "Reaction/Diagnostics", "dtype": "text", "required": False, "clause": "ISO-26262 Part 6 Clause 7.4"},
        {"key": "fdti", "label": "FDTI", "dtype": "string", "required": False, "clause": "ISO-26262 Part 5 Clause 9"},
        {"key": "frti", "label": "FRTI", "dtype": "string", "required": False, "clause": "ISO-26262 Part 5 Clause 9"},
        {"key": "fhti", "label": "FHTI", "dtype": "string", "required": False, "clause": "ISO-26262 Part 5 Clause 9"},
        {"key": "diagnostic_coverage", "label": "Diagnostic Coverage", "dtype": "percentage", "required": False, "clause": "ISO-26262 Part 5 Annex D"},
        {"key": "clause_reference", "label": "Clause Reference", "dtype": "string", "required": True, "clause": "ASPICE SWE.1 BP1"},
        {"key": "verification", "label": "Verification Method", "dtype": "enum", "required": False, "clause": "ASPICE SWE.6 BP1"},
        {"key": "source_hcr_id", "label": "Source HCR-ID", "dtype": "string", "required": False, "clause": "ISO-21434 Clause 15"},
        {"key": "reaction_response", "label": "Reaction/Response", "dtype": "text", "required": False, "clause": "ISO-21434 Clause 15.4"},
    ]
    op.bulk_insert(attr_defs, [
        {
            "id": uuid.uuid4(),
            "attribute_key": r["key"],
            "display_label": r["label"],
            "data_type": r["dtype"],
            "is_required": r["required"],
            "schema_version": schema_v,
            "clause_reference": r["clause"],
            "options_json": None,
            "created_at": now,
        }
        for r in attr_rows
    ])


def downgrade() -> None:
    op.execute("DELETE FROM attribute_definitions WHERE schema_version = 'RD-03-010-09-v1'")
    op.execute(
        "DELETE FROM organisation_nodes WHERE id IN ("
        "'10000000-0000-0000-0000-000000000001',"
        "'10000000-0000-0000-0000-000000000002',"
        "'10000000-0000-0000-0000-000000000003',"
        "'10000000-0000-0000-0000-000000000004')"
    )
