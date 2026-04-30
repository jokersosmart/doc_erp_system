"""Seed data: Standards and AttributeDefinitions.

Revision ID: 0002
Revises: 0001
Create Date: 2025-04-30

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Pre-defined UUIDs for reproducible seeding
ASPICE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ISO_26262_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
ISO_21434_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

NOW = datetime(2025, 4, 30, 0, 0, 0, tzinfo=timezone.utc)


def upgrade() -> None:
    conn = op.get_bind()

    # Insert Standards
    conn.execute(
        sa.text(
            "INSERT INTO standards (id, name, version, created_at) VALUES "
            "(:id1, :name1, :ver1, :now), "
            "(:id2, :name2, :ver2, :now), "
            "(:id3, :name3, :ver3, :now) "
            "ON CONFLICT (name) DO NOTHING"
        ),
        {
            "id1": str(ASPICE_ID),
            "name1": "ASPICE 3.1",
            "ver1": "3.1",
            "id2": str(ISO_26262_ID),
            "name2": "ISO-26262",
            "ver2": "2018",
            "id3": str(ISO_21434_ID),
            "name3": "ISO-21434",
            "ver3": "2021",
            "now": NOW,
        },
    )

    # Insert AttributeDefinitions
    attr_defs = [
        {
            "id": str(uuid.UUID("00000000-0000-0000-0001-000000000001")),
            "name": "ASIL_Level",
            "data_type": "ENUM",
            "allowed_values": '["QM", "ASIL A", "ASIL B", "ASIL C", "ASIL D"]',
            "is_required": False,
            "standard_id": str(ISO_26262_ID),
        },
        {
            "id": str(uuid.UUID("00000000-0000-0000-0001-000000000002")),
            "name": "Document_Type",
            "data_type": "ENUM",
            "allowed_values": '["Spec", "Plan", "Report", "Manual", "Procedure", "Form"]',
            "is_required": True,
            "standard_id": str(ASPICE_ID),
        },
        {
            "id": str(uuid.UUID("00000000-0000-0000-0001-000000000003")),
            "name": "Document_Owner",
            "data_type": "STRING",
            "allowed_values": None,
            "is_required": True,
            "standard_id": None,
        },
        {
            "id": str(uuid.UUID("00000000-0000-0000-0001-000000000004")),
            "name": "Safety_Goal_ID",
            "data_type": "STRING",
            "allowed_values": None,
            "is_required": False,
            "standard_id": str(ISO_26262_ID),
        },
        {
            "id": str(uuid.UUID("00000000-0000-0000-0001-000000000005")),
            "name": "Threat_ID",
            "data_type": "STRING",
            "allowed_values": None,
            "is_required": False,
            "standard_id": str(ISO_21434_ID),
        },
    ]

    for attr in attr_defs:
        if attr["allowed_values"] is not None:
            conn.execute(
                sa.text(
                    "INSERT INTO attribute_definitions "
                    "(id, name, data_type, allowed_values, is_required, standard_id, created_at, updated_at) "
                    "VALUES (:id, :name, :data_type, :allowed_values::jsonb, :is_required, :standard_id, :now, :now) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {**attr, "now": NOW},
            )
        else:
            conn.execute(
                sa.text(
                    "INSERT INTO attribute_definitions "
                    "(id, name, data_type, allowed_values, is_required, standard_id, created_at, updated_at) "
                    "VALUES (:id, :name, :data_type, NULL, :is_required, :standard_id, :now, :now) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {**{k: v for k, v in attr.items() if k != "allowed_values"}, "now": NOW},
            )


def downgrade() -> None:
    conn = op.get_bind()
    # Remove seeded attribute definitions
    attr_ids = [
        "00000000-0000-0000-0001-000000000001",
        "00000000-0000-0000-0001-000000000002",
        "00000000-0000-0000-0001-000000000003",
        "00000000-0000-0000-0001-000000000004",
        "00000000-0000-0000-0001-000000000005",
    ]
    for attr_id in attr_ids:
        conn.execute(
            sa.text("DELETE FROM attribute_definitions WHERE id = :id"),
            {"id": attr_id},
        )
    # Remove seeded standards
    for std_id in [str(ASPICE_ID), str(ISO_26262_ID), str(ISO_21434_ID)]:
        conn.execute(
            sa.text("DELETE FROM standards WHERE id = :id"), {"id": std_id}
        )
