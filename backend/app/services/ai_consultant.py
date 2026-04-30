"""
AI Consultant Service (T031, T032, T040, T044).
- generate_wizard_questions(): config-driven static questions (phase 1, no LLM)
- generate_document_framework(): scaffold Documents + SpecItems from BU template
- gap_analysis(): LangChain RAG pipeline (T040, enabled in US2)
- check_template_compliance(): EAV attribute compliance check (T044)
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, LifecycleState, LockState
from app.models.org import Project, WizardSession
from app.models.spec_item import AttributeDefinition, SpecItem

logger = logging.getLogger(__name__)

# ── Wizard Question Config (T031) ─────────────────────────────────────────────
# Static config-driven questions; LLM RAG integration added in T040 (US2).

WIZARD_QUESTIONS: list[dict[str, Any]] = [
    {
        "step": 0,
        "key": "project_name",
        "type": "text",
        "label_zh": "專案名稱",
        "label_en": "Project Name",
        "placeholder_zh": "例：SSD Controller Gen5 FW v1.0",
        "placeholder_en": "e.g. SSD Controller Gen5 FW v1.0",
        "required": True,
    },
    {
        "step": 1,
        "key": "bu",
        "type": "select",
        "label_zh": "業務單位（BU）",
        "label_en": "Business Unit (BU)",
        "options": [
            {"value": "SSD_CONTROLLER", "label_zh": "SSD Controller 部門", "label_en": "SSD Controller BU"},
            {"value": "EMMC", "label_zh": "eMMC 部門", "label_en": "eMMC BU"},
            {"value": "NAND_FLASH", "label_zh": "NAND Flash 部門", "label_en": "NAND Flash BU"},
            {"value": "OTHER", "label_zh": "其他", "label_en": "Other"},
        ],
        "required": True,
    },
    {
        "step": 2,
        "key": "aspice_level",
        "type": "select",
        "label_zh": "目標 ASPICE 等級",
        "label_en": "Target ASPICE Level",
        "options": [
            {"value": 0, "label_zh": "Level 0 – 未執行", "label_en": "Level 0 – Incomplete"},
            {"value": 1, "label_zh": "Level 1 – 已執行", "label_en": "Level 1 – Performed"},
            {"value": 2, "label_zh": "Level 2 – 受管理", "label_en": "Level 2 – Managed"},
            {"value": 3, "label_zh": "Level 3 – 已建立", "label_en": "Level 3 – Established"},
        ],
        "required": True,
    },
    {
        "step": 3,
        "key": "safety_standards",
        "type": "multiselect",
        "label_zh": "適用安全標準（可複選）",
        "label_en": "Applicable Safety Standards (multi-select)",
        "options": [
            {"value": "ISO-26262", "label_zh": "ISO 26262 功能安全 (Automotive)", "label_en": "ISO 26262 Functional Safety (Automotive)"},
            {"value": "ISO-21434", "label_zh": "ISO 21434 車用資安", "label_en": "ISO 21434 Automotive Cybersecurity"},
            {"value": "IEC-61508", "label_zh": "IEC 61508", "label_en": "IEC 61508"},
            {"value": "NONE", "label_zh": "無（純 ASPICE）", "label_en": "None (ASPICE only)"},
        ],
        "required": True,
    },
    {
        "step": 4,
        "key": "asil_cal_level",
        "type": "select",
        "label_zh": "最高 ASIL / CAL 等級",
        "label_en": "Highest ASIL / CAL Level",
        "options": [
            {"value": "QM", "label_zh": "QM（無特定安全要求）", "label_en": "QM (no specific safety requirement)"},
            {"value": "ASIL-A", "label_zh": "ASIL-A", "label_en": "ASIL-A"},
            {"value": "ASIL-B", "label_zh": "ASIL-B", "label_en": "ASIL-B"},
            {"value": "ASIL-C", "label_zh": "ASIL-C", "label_en": "ASIL-C"},
            {"value": "ASIL-D", "label_zh": "ASIL-D", "label_en": "ASIL-D"},
            {"value": "CAL-1", "label_zh": "CAL-1", "label_en": "CAL-1"},
            {"value": "CAL-2", "label_zh": "CAL-2", "label_en": "CAL-2"},
            {"value": "CAL-3", "label_zh": "CAL-3", "label_en": "CAL-3"},
            {"value": "CAL-4", "label_zh": "CAL-4", "label_en": "CAL-4"},
        ],
        "depends_on": {"key": "safety_standards", "not_value": "NONE"},
        "required": False,
    },
    {
        "step": 5,
        "key": "departments",
        "type": "multiselect",
        "label_zh": "參與部門",
        "label_en": "Participating Departments",
        "options": [
            {"value": "SYS", "label_zh": "系統工程 (SYS)", "label_en": "Systems Engineering (SYS)"},
            {"value": "HW", "label_zh": "硬體 (HW)", "label_en": "Hardware (HW)"},
            {"value": "SWE", "label_zh": "軟體 (SWE)", "label_en": "Software (SWE)"},
            {"value": "SAFETY", "label_zh": "功能安全 (SAFETY)", "label_en": "Functional Safety"},
            {"value": "SECURITY", "label_zh": "資安 (SECURITY)", "label_en": "Cybersecurity"},
            {"value": "VCT", "label_zh": "驗證與確認 (VCT)", "label_en": "Verification & Validation"},
        ],
        "required": True,
    },
    {
        "step": 6,
        "key": "document_types",
        "type": "multiselect",
        "label_zh": "需要產生的文件類型",
        "label_en": "Document Types to Generate",
        "options": [
            {"value": "HARA", "label_zh": "HARA（危害分析）", "label_en": "HARA (Hazard Analysis)"},
            {"value": "SYS_SPEC", "label_zh": "系統規格 (System Spec)", "label_en": "System Specification"},
            {"value": "SW_SPEC", "label_zh": "軟體架構規格 (SW Arch Spec)", "label_en": "SW Architecture Specification"},
            {"value": "HW_SPEC", "label_zh": "硬體規格 (HW Spec)", "label_en": "HW Specification"},
            {"value": "FW_SPEC", "label_zh": "韌體規格 (FW Spec)", "label_en": "FW Specification"},
            {"value": "VCT_PLAN", "label_zh": "驗證計畫 (VCT Plan)", "label_en": "Verification & Validation Plan"},
            {"value": "SECURITY_TARA", "label_zh": "資安 TARA", "label_en": "Security TARA"},
        ],
        "required": True,
    },
    {
        "step": 7,
        "key": "git_backend",
        "type": "select",
        "label_zh": "Git 版本管理系統",
        "label_en": "Git Backend",
        "options": [
            {"value": "gerrit", "label_zh": "Gerrit（推薦）", "label_en": "Gerrit (recommended)"},
            {"value": "github", "label_zh": "GitHub Enterprise", "label_en": "GitHub Enterprise"},
            {"value": "gitlab", "label_zh": "GitLab", "label_en": "GitLab"},
        ],
        "required": True,
    },
]


def generate_wizard_questions(bu: str | None = None, standards: list[str] | None = None) -> list[dict[str, Any]]:
    """Return config-driven wizard questions (T031). LLM customisation added in T040."""
    return WIZARD_QUESTIONS


# ── BU Document Framework Templates (T032) ───────────────────────────────────

_SSD_CONTROLLER_DOCS = [
    {"key": "HARA", "title": "Hazard Analysis and Risk Assessment (HARA)", "partition": "SAFETY", "is_safety_critical": True, "schema_version": "RD-03-010-09-v1"},
    {"key": "SYS_SPEC", "title": "System Requirements Specification", "partition": "SYS", "is_safety_critical": False, "schema_version": "RD-03-010-09-v1"},
    {"key": "FW_SPEC", "title": "Firmware Architecture Specification", "partition": "SWE", "is_safety_critical": False, "schema_version": "RD-03-010-09-v1"},
    {"key": "HW_SPEC", "title": "Hardware Design Specification", "partition": "HW", "is_safety_critical": False, "schema_version": "RD-03-010-09-v1"},
    {"key": "SW_SPEC", "title": "Software Requirements Specification", "partition": "SWE", "is_safety_critical": False, "schema_version": "RD-03-010-09-v1"},
    {"key": "VCT_PLAN", "title": "Verification and Validation Plan", "partition": "VCT", "is_safety_critical": False, "schema_version": "RD-03-010-09-v1"},
]

_EMMC_DOCS = [
    {"key": "SYS_SPEC", "title": "eMMC System Requirements Specification", "partition": "SYS", "is_safety_critical": False, "schema_version": "RD-03-010-09-v1"},
    {"key": "FW_SPEC", "title": "eMMC Firmware Architecture Specification", "partition": "SWE", "is_safety_critical": False, "schema_version": "RD-03-010-09-v1"},
    {"key": "HW_SPEC", "title": "eMMC Hardware Design Specification", "partition": "HW", "is_safety_critical": False, "schema_version": "RD-03-010-09-v1"},
    {"key": "VCT_PLAN", "title": "eMMC Validation Plan", "partition": "VCT", "is_safety_critical": False, "schema_version": "RD-03-010-09-v1"},
]

# ASIL-B+ adds HARA + SECURITY_TARA by default
_SAFETY_CRITICAL_ADDITIONS: list[dict[str, Any]] = [
    {"key": "SECURITY_TARA", "title": "Threat Analysis and Risk Assessment (TARA)", "partition": "SECURITY", "is_safety_critical": True, "schema_version": "RD-03-010-09-v1"},
]

BU_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "SSD_CONTROLLER": _SSD_CONTROLLER_DOCS,
    "EMMC": _EMMC_DOCS,
    "NAND_FLASH": _SSD_CONTROLLER_DOCS,  # same template as SSD for now
    "OTHER": _SSD_CONTROLLER_DOCS,
}

# Sections pre-populated as SpecItem rows (title → section heading placeholder)
_SECTION_SKELETONS: dict[str, list[str]] = {
    "HARA": ["1. Scope", "2. Hazard Identification", "3. Risk Assessment", "4. Safety Goals", "5. Safe States", "6. Review & Sign-off"],
    "SYS_SPEC": ["1. Introduction", "2. System Overview", "3. Stakeholder Requirements", "4. System Requirements", "5. External Interfaces", "6. Non-Functional Requirements", "7. Traceability", "8. Open Issues"],
    "FW_SPEC": ["1. Introduction", "2. Firmware Architecture", "3. Module Decomposition", "4. Interface Control", "5. Timing & Resource Constraints", "6. ASPICE SWE.3 Checklist"],
    "HW_SPEC": ["1. Introduction", "2. Block Diagram", "3. Pin Description", "4. Electrical Specifications", "5. PCB Layout Guidelines", "6. Design Verification Items"],
    "SW_SPEC": ["1. Introduction", "2. SW Architecture", "3. Component Design", "4. Data Flow", "5. Error Handling", "6. Interface Contracts"],
    "VCT_PLAN": ["1. Scope", "2. Test Strategy", "3. Test Environment", "4. Test Schedule", "5. Entry/Exit Criteria", "6. Test Cases (high-level)", "7. Traceability to Requirements"],
    "SECURITY_TARA": ["1. Scope", "2. Asset Identification", "3. Threat Scenarios", "4. Risk Assessment", "5. Cybersecurity Goals", "6. Controls & Mitigations"],
}


async def generate_document_framework(wizard_session: WizardSession, project: Project, db: AsyncSession) -> list[Document]:
    """
    T032: Create Document + SpecItem scaffold rows from BU template.
    Selects only the doc types the PM chose in answers_json['document_types'].
    Safety-critical additions triggered if asil_cal_level is ASIL-B or higher.
    """
    answers: dict[str, Any] = wizard_session.answers_json or {}
    bu = answers.get("bu", "OTHER")
    selected_types: list[str] = answers.get("document_types", [tpl["key"] for tpl in BU_TEMPLATES.get(bu, _SSD_CONTROLLER_DOCS)])
    asil_cal = answers.get("asil_cal_level", "QM")
    safety_standards: list[str] = answers.get("safety_standards", [])

    base_templates = BU_TEMPLATES.get(bu, _SSD_CONTROLLER_DOCS)
    templates_to_create = [t for t in base_templates if t["key"] in selected_types]

    # Auto-add SECURITY_TARA for ISO-21434 or ASIL-B+ projects
    if "ISO-21434" in safety_standards or asil_cal in ("ASIL-B", "ASIL-C", "ASIL-D", "CAL-3", "CAL-4"):
        for extra in _SAFETY_CRITICAL_ADDITIONS:
            if extra["key"] in selected_types and extra not in templates_to_create:
                templates_to_create.append(extra)

    created_docs: list[Document] = []
    for tpl in templates_to_create:
        doc = Document(
            project_id=project.id,
            bu_node_id=project.bu_node_id,
            title=tpl["title"],
            partition=tpl["partition"],
            is_safety_critical=tpl["is_safety_critical"],
            schema_version=tpl["schema_version"],
            lifecycle_state=LifecycleState.DRAFT,
            lock_state=LockState.UNLOCKED,
            current_version=0,
        )
        db.add(doc)
        await db.flush()  # get doc.id before adding spec items

        sections = _SECTION_SKELETONS.get(tpl["key"], ["1. Introduction", "2. Content", "3. Appendix"])
        for idx, section_title in enumerate(sections):
            spec_item = SpecItem(
                document_id=doc.id,
                item_type="SECTION",
                title=section_title,
                content_markdown=f"## {section_title}\n\n<!-- Add content here -->",
                order_index=idx,
                schema_version=tpl["schema_version"],
            )
            db.add(spec_item)

        created_docs.append(doc)

    await db.flush()
    logger.info("Generated %d documents for project %s (BU=%s)", len(created_docs), project.id, bu)
    return created_docs


# ── Stub for US2 gap analysis (T040) ─────────────────────────────────────────

async def gap_analysis(document_id: str, spec_item_id: str | None, db: AsyncSession) -> dict[str, Any]:  # noqa: ARG001
    """
    T040: LangChain RAG gap analysis.
    Returns AI_OFFLINE_MODE=True with static rule checklist when LLM unavailable.
    Full implementation in US2 (T040).
    """
    logger.warning("gap_analysis: LLM pipeline not yet implemented; returning static offline rules")
    return {
        "ai_offline_mode": True,
        "suggestions": [
            {
                "type": "static_rule",
                "gap": "Clause reference missing",
                "clause_reference": "ASPICE SWE.1 BP1",
                "suggested_content": "Add explicit clause reference: ASPICE SWE.1 BP1 — Software Requirements Elicitation.",
                "severity": "warning",
            }
        ],
    }


# ── US2 template compliance check (T044) ─────────────────────────────────────

async def check_template_compliance(document_id: str, db: AsyncSession) -> list[dict[str, Any]]:
    """
    T044: Compare document attribute_values against attribute_definitions registry.
    Flags missing required attributes as compliance gaps.
    """
    from sqlalchemy import select as _select  # local import to avoid circular
    from app.models.spec_item import AttributeValue

    result = await db.execute(
        _select(AttributeDefinition).where(
            AttributeDefinition.schema_version.isnot(None),
            AttributeDefinition.is_required == True,  # noqa: E712
        )
    )
    required_attrs = result.scalars().all()

    gaps: list[dict[str, Any]] = []
    for attr_def in required_attrs:
        val_result = await db.execute(
            _select(AttributeValue).join(SpecItem, AttributeValue.spec_item_id == SpecItem.id)
            .where(SpecItem.document_id == document_id, AttributeValue.attribute_definition_id == attr_def.id)
        )
        values = val_result.scalars().all()
        if not values:
            gaps.append({
                "type": "missing_required_attribute",
                "attribute_key": attr_def.attribute_key,
                "label": attr_def.display_label,
                "schema_version": attr_def.schema_version,
                "clause_reference": attr_def.clause_reference,
                "severity": "error",
                "suggested_content": f"Populate required attribute '{attr_def.display_label}' per {attr_def.clause_reference or 'template definition'}.",
            })
    return gaps
