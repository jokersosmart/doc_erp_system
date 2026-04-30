# Implementation Plan: 車用標準文件 ERP 系統 — 文件管理後端 API

**Branch**: `doc-management-backend` | **Date**: 2025-04-30 | **Spec**: `.specify/sessions/doc-management-backend/spec.md`  
**Input**: Feature specification from `.specify/sessions/doc-management-backend/spec.md`

---

## Summary

本計畫為「車用標準文件 ERP 系統」核心後端 API 的完整實作藍圖，對應 ASPICE 3.1 / ISO-26262 / ISO-21434 標準文件管理需求。

**核心需求**：建立一套以 Python FastAPI 為基礎的 RESTful API，支援：
- 文件 CRUD 與語意版本控制（Snapshot-based）
- 四段式狀態機（DRAFT → REVIEW → APPROVED → OBSOLETE）及稽核日誌
- EAV 動態屬性系統（支援 ASPICE/ISO 自訂屬性，不硬編碼欄位）
- 五層 Partition 組織結構（SYS / HW / SWE / Safety / Security）
- JWT RBAC 身份驗證（role + partition_access）

**技術方案**：FastAPI + PostgreSQL + SQLAlchemy ORM + Alembic Migration + Pydantic v2 + python-jose JWT + pytest，部署於 Docker Compose（開發）/ Railway（驗證）。

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI 0.111+, SQLAlchemy 2.0+, Alembic 1.13+, Pydantic v2, python-jose[cryptography] 3.3+, passlib[bcrypt] 1.7+, asyncpg 0.29+ (async PostgreSQL driver), uvicorn 0.29+  
**Storage**: PostgreSQL 15+（主資料庫；EAV 屬性值分欄儲存以利型別約束）  
**Testing**: pytest + pytest-asyncio + httpx (AsyncClient) + pytest-cov；目標覆蓋率 ≥ 85%  
**Target Platform**: Linux server（Docker Compose 本地開發；Railway 雲端驗證）  
**Project Type**: Web Service — RESTful Backend API  
**Performance Goals**:
- `POST /documents` → p90 ≤ 500 ms
- `GET /documents/{id}` → p99 ≤ 200 ms
- 50 並發使用者（70% 讀 / 30% 寫）無資料不一致

**Constraints**:
- `content_md` 上限 5 MB per 文件（FR spec A-05）
- JWT 使用對稱式 HS256，密鑰由環境變數注入（不硬編碼）
- 所有核心實體主鍵使用 UUID v4
- 資料庫 Schema 變更必須透過 Alembic Migration 管理且支援 downgrade

**Scale/Scope**: 初期目標 SiliconMotion 5 層組織 × 12 職能部門；Seed Data 預設標準（ASPICE 3.1, ISO-26262, ISO-21434）與屬性定義；單租戶（本版本不含 Multi-tenancy）

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | 憲法原則 | 狀態 | 說明 |
|---|----------|------|------|
| I | **規格驅動開發**：所有功能以規格文件為起點 | ✅ PASS | spec.md 已完整定義 FR-001~FR-024，本 plan.md 忠實反映規格 |
| II | **自動化追溯**：雙向追溯矩陣，source 變更時自動標記 SUSPECT | ⚠️ PARTIAL | 本 Spec 範疇內不含 Traceability API 實作（A-06 明確排除），`traceability_links` 表結構已設計留白，供後續 Spec 擴展。狀態轉換觸發 AuditLog 已包含 | 
| III | **AI 輔助合規**：ASPICE/ISO 條文自動合規檢查 | ⚠️ PARTIAL | 本 Spec 範疇為後端資料基礎建設，AI 審查模組為後續功能（A-06），EAV 屬性系統已設計為其資料輸入來源 |
| IV | **EAV 動態擴展**：禁止為單一標準 Hardcode 專屬欄位 | ✅ PASS | 所有標準屬性（ASIL Level, Safety Goal ID 等）透過 `attribute_definitions` + `document_attribute_values` 實作，嚴禁在 `documents` 表新增標準專屬欄位 |
| V | **結構化可匯出性**：支援與 Codebeamer 整合 | ✅ PASS | EAV 屬性分欄儲存（value_string/value_integer/value_boolean）確保無損轉換；匯出介面留白於後續 Spec |

**Gate 結論**：**PASS（含兩項 PARTIAL 說明，均有規格依據豁免）**。PARTIAL 項目已在 spec.md Assumptions A-06 中明確排除於本 Spec 範疇，不構成違規。

### Post-Design Constitution Re-Check（Phase 1 後更新）

| # | 憲法原則 | 狀態 | 說明 |
|---|----------|------|------|
| I | 規格驅動開發 | ✅ PASS | data-model.md 所有實體均可追溯至 FR/SC 編號 |
| II | 自動化追溯 | ✅ PASS | `traceability_links` 表結構已設計，狀態欄位留 VALID/SUSPECT；AuditLog 完整記錄每次狀態轉換 |
| IV | EAV 動態擴展 | ✅ PASS | `attribute_definitions.allowed_values` 使用 JSONB 儲存 ENUM 允許值，資料型別約束在應用層 Pydantic v2 + 資料庫 CHECK 約束雙重保障 |
| V | 可匯出性 | ✅ PASS | 所有 EAV 值分欄儲存，API 回應統一序列化，結構清晰可供後續匯出轉換 |

---

## Project Structure

### Documentation (this feature)

```text
.specify/sessions/doc-management-backend/
├── plan.md              ← 本檔案（Phase 0+1 產出）
├── research.md          ← Phase 0 研究結論
├── data-model.md        ← Phase 1 資料模型設計
├── quickstart.md        ← Phase 1 開發者快速入門
├── contracts/           ← Phase 1 API 合約
│   ├── openapi-overview.md
│   ├── auth.md
│   ├── projects.md
│   ├── documents.md
│   ├── partitions.md
│   └── attribute-definitions.md
└── tasks.md             ← Phase 2 產出（由 /speckit.tasks 生成）
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                   # FastAPI application entry point, lifespan, middleware
│   ├── core/
│   │   ├── config.py             # Settings (pydantic-settings BaseSettings, .env 載入)
│   │   └── security.py           # JWT 簽發/驗證 (python-jose), password hashing (passlib)
│   ├── db/
│   │   ├── base.py               # SQLAlchemy DeclarativeBase, metadata
│   │   └── session.py            # async engine, AsyncSession factory, get_db dependency
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── project.py            # Project
│   │   ├── document.py           # Document + DocumentVersion
│   │   ├── partition.py          # Partition
│   │   ├── attribute.py          # AttributeDefinition + DocumentAttributeValue
│   │   ├── standard.py           # Standard
│   │   ├── audit_log.py          # AuditLog
│   │   └── traceability.py       # TraceabilityLink (schema stub，邏輯留後續 Spec)
│   ├── schemas/                  # Pydantic v2 request/response schemas
│   │   ├── auth.py               # LoginRequest, TokenResponse, TokenPayload
│   │   ├── project.py            # ProjectCreate, ProjectRead
│   │   ├── partition.py          # PartitionCreate, PartitionRead
│   │   ├── document.py           # DocumentCreate, DocumentRead, DocumentUpdate,
│   │   │                         # DocumentListItem, StatusTransitionRequest,
│   │   │                         # VersionRead, VersionListItem
│   │   └── attribute.py          # AttributeDefinitionCreate, AttributeDefinitionRead,
│   │                             # DocumentAttributeValueInput
│   ├── api/
│   │   └── v1/
│   │       ├── router.py         # APIRouter 總成（include 各 endpoint router）
│   │       └── endpoints/
│   │           ├── auth.py       # POST /auth/login, POST /auth/refresh
│   │           ├── projects.py   # POST/GET /projects, GET /projects/{id}
│   │           ├── partitions.py # POST/GET /partitions
│   │           ├── documents.py  # Full document CRUD + status + versions
│   │           └── attributes.py # POST/GET /attribute-definitions
│   ├── crud/                     # DB 操作函式（不含業務邏輯）
│   │   ├── base.py               # CRUDBase generic class
│   │   ├── project.py
│   │   ├── partition.py
│   │   ├── document.py           # 含版本快照寫入邏輯
│   │   └── attribute.py
│   └── services/                 # 業務邏輯（狀態機、EAV 驗證、版本號遞增）
│       ├── document_service.py   # create_document, update_document, transition_status
│       └── attribute_service.py  # validate_attributes, resolve_required_attrs
├── migrations/                   # Alembic migration scripts
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_schema.py
├── tests/
│   ├── conftest.py               # pytest fixtures: test DB, async client, seed data
│   ├── unit/
│   │   ├── test_security.py
│   │   ├── test_document_service.py  # 狀態機 transition 邏輯
│   │   └── test_attribute_service.py # EAV 驗證邏輯
│   ├── integration/
│   │   ├── test_auth.py
│   │   ├── test_projects.py
│   │   ├── test_partitions.py
│   │   ├── test_documents.py     # CRUD + 版本 + 狀態機 + RBAC
│   │   └── test_attributes.py
│   └── contract/
│       └── test_openapi_schema.py # 驗證 /openapi.json 符合預期 schema
├── requirements.txt
├── requirements-dev.txt          # pytest, httpx, pytest-cov, pytest-asyncio
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── alembic.ini
```

**Structure Decision**: 採單一 backend 專案結構（前端 UI 在本 Spec 範疇外，A-06）。`app/` 分層依循關注點分離原則：`models` 為純 ORM schema，`schemas` 為 Pydantic DTO，`crud` 為純 DB 操作，`services` 封裝業務邏輯（狀態機、EAV 驗證），`api/endpoints` 僅做路由委派。此分層確保業務邏輯可獨立 unit test，不依賴 HTTP 層。

---

## Complexity Tracking

| 複雜度項目 | 理由 | 更簡單替代方案被排除的原因 |
|-----------|------|--------------------------|
| EAV 動態屬性 (`attribute_definitions` + `document_attribute_values`) | 憲法原則 IV 強制要求；支援 ASPICE/ISO 標準動態擴展屬性 | Hardcode 欄位違反憲法，且無法在不修改 schema 的情況下支援新標準 |
| 獨立 `document_versions` 快照表 | FR-015 要求保留所有歷史版本；ASPICE 稽核需要逐版本追溯 | Git-based 版本控制（A-04 明確排除）；資料庫快照為唯一合規選項 |
| Services 層（非僅 CRUD）| 狀態機 transition 邏輯、EAV 驗證、樂觀鎖等業務邏輯需集中測試 | 若直接置於 endpoint handler，業務邏輯無法獨立 unit test |
| Async SQLAlchemy 2.0 + asyncpg | 50 并發目標（SC-003）；FastAPI 原生 async 生態 | Sync SQLAlchemy 在高並發下會阻塞 event loop |

---

## Implementation Phases

### Phase 0: Research（已完成）→ `research.md`

所有技術決策均已由 spec.md 中的 Assumptions（A-01~A-12）明確定義，無 NEEDS CLARIFICATION 項目。研究重點：

1. **FastAPI async SQLAlchemy 2.0 最佳實踐**：Session lifecycle + dependency injection 模式
2. **EAV 分欄 vs JSONB 儲存**：型別約束 vs 彈性的取捨
3. **JWT Refresh Token 安全模式**：Rotation + 黑名單策略
4. **樂觀鎖實作**：版本號欄位 vs PostgreSQL advisory lock
5. **Alembic async migration**：與 SQLAlchemy 2.0 async engine 的整合

→ 詳見 `research.md`

### Phase 1: Design & Contracts（已完成）

| 產出物 | 路徑 | 狀態 |
|--------|------|------|
| 資料模型設計 | `data-model.md` | ✅ 完成 |
| API 合約總覽 | `contracts/openapi-overview.md` | ✅ 完成 |
| Auth API 合約 | `contracts/auth.md` | ✅ 完成 |
| Projects API 合約 | `contracts/projects.md` | ✅ 完成 |
| Documents API 合約 | `contracts/documents.md` | ✅ 完成 |
| Partitions API 合約 | `contracts/partitions.md` | ✅ 完成 |
| AttributeDefinitions API 合約 | `contracts/attribute-definitions.md` | ✅ 完成 |
| 開發者快速入門 | `quickstart.md` | ✅ 完成 |

### Phase 2: Task Generation（下一步）

執行 `/speckit.tasks` 指令，依本 plan.md 生成可執行的 `tasks.md`，任務應依以下優先順序分組：

1. **T-001 ~ T-010**: 基礎建設（專案結構、DB 連線、Alembic、Docker）
2. **T-011 ~ T-020**: 認證模組（JWT 簽發、RBAC 中介層、login/refresh 端點）
3. **T-021 ~ T-035**: 核心文件 API（CRUD、版本控制、狀態機、AuditLog）
4. **T-036 ~ T-045**: EAV 屬性系統（AttributeDefinition CRUD、驗證邏輯）
5. **T-046 ~ T-055**: 專案與 Partition 管理
6. **T-056 ~ T-065**: 測試套件（unit + integration + contract）
7. **T-066 ~ T-070**: 文件與部署（Dockerfile、docker-compose、.env.example、/health）

---

## Key Decisions

| 決策 | 選擇 | 理由 |
|------|------|------|
| ORM | SQLAlchemy 2.0 async | FastAPI 原生 async 生態；2.0 API 更簡潔 |
| Migration | Alembic | SQLAlchemy 官方搭配；支援 async engine |
| JWT | python-jose HS256 | Spec A-02 明確指定；輕量無外部依賴 |
| Password Hash | passlib bcrypt | 工業標準；FastAPI 官方推薦 |
| EAV 值儲存 | 分欄（value_string/value_integer/value_boolean） | 資料庫層型別約束；避免全 JSONB 失去 DB 驗證 |
| ENUM 允許值 | JSONB 陣列欄位（`allowed_values JSONB`） | 允許值清單長度不定；避免額外 junction table |
| 版本號格式 | `major.minor` 字串（如 "1.0", "1.1"） | ASPICE 語意版本習慣；APPROVED 後 minor 凍結 |
| 樂觀鎖 | `version` 欄位比對（請求帶 current_version） | 實作簡單；Edge Case spec 已明確要求 409 |
| 測試 DB | 獨立 PostgreSQL test database（Docker） | 確保 migration 可在全新環境執行（SC-008） |
| API 版本 | `/api/v1/` prefix | 為未來版本升級預留空間；不影響本期實作 |
