# Tasks: 車用標準文件 ERP 系統 — 文件管理後端 API

**Feature**: `doc-management-backend`  
**Generated**: 2025-04-30  
**Spec**: `.specify/sessions/doc-management-backend/spec.md`  
**Plan**: `.specify/sessions/doc-management-backend/plan.md`  
**Total Tasks**: 70  
**Target Coverage**: ≥ 85% (SC-007)

---

## 任務總覽

| 分組 | 範圍 | 任務數 |
|------|------|--------|
| Phase 1：基礎建設 | 專案結構、設定、Docker、依賴套件 | T001–T010 |
| Phase 2：資料庫 | SQLAlchemy models、Alembic migrations、Seed Data | T011–T022 |
| Phase 3：認證系統 | JWT 簽發驗證、RBAC 中介層、Auth 端點 | T023–T032 |
| Phase 4：專案與 Partition 管理 API | Projects / Partitions CRUD | T033–T040 |
| Phase 5：文件管理核心 API | Document CRUD + 狀態機 + 版本歷程 | T041–T055 |
| Phase 6：EAV 動態屬性 API | AttributeDefinition CRUD + 驗證服務 | T056–T062 |
| Phase 7：測試套件 | Unit / Integration / Contract tests | T063–T070 |

---

## 任務格式說明

```
- [ ] T### [P] [US?] 實作目標（FR-XXX）
      產出物：`路徑/檔案`
```

- `[P]` = 可與其他 `[P]` 任務**平行執行**（不同檔案，無未完成依賴）
- `[US1~6]` = 對應 spec.md 的 User Story 編號
- FR 編號 = 對應 spec.md 的功能需求

---

## Phase 1：基礎建設

> **目標**：建立可執行的 FastAPI 專案骨架，確保新開發者在 30 分鐘內啟動（SC-010）。

- [X] T001 建立後端專案目錄結構，包含所有必要的子目錄與空的 `__init__.py` 檔案
  - **目標**：確立 `backend/` 整體骨架，所有後續任務均以此結構為基礎
  - **產出物**：
    ```
    backend/
    ├── app/__init__.py
    ├── app/core/__init__.py
    ├── app/db/__init__.py
    ├── app/models/__init__.py
    ├── app/schemas/__init__.py
    ├── app/api/__init__.py
    ├── app/api/v1/__init__.py
    ├── app/api/v1/endpoints/__init__.py
    ├── app/crud/__init__.py
    ├── app/services/__init__.py
    ├── migrations/versions/（空目錄）
    ├── tests/unit/__init__.py
    ├── tests/integration/__init__.py
    └── tests/contract/__init__.py
    ```

- [X] T002 [P] 建立 `requirements.txt`，列出所有正式環境依賴套件及固定版本
  - **目標**：固定所有 production 依賴，確保環境可重現（SC-010）
  - **套件清單**：`fastapi>=0.111`, `uvicorn[standard]>=0.29`, `sqlalchemy[asyncio]>=2.0`, `alembic>=1.13`, `pydantic>=2.0`, `pydantic-settings>=2.0`, `python-jose[cryptography]>=3.3`, `passlib[bcrypt]>=1.7`, `asyncpg>=0.29`, `python-multipart>=0.0.9`
  - **產出物**：`backend/requirements.txt`

- [X] T003 [P] 建立 `requirements-dev.txt`，列出所有開發與測試依賴套件
  - **目標**：隔離開發環境依賴，不影響正式部署映像大小
  - **套件清單**：`pytest>=8.0`, `pytest-asyncio>=0.23`, `pytest-cov>=5.0`, `httpx>=0.27`, `anyio[trio]`
  - **產出物**：`backend/requirements-dev.txt`

- [X] T004 建立 `app/core/config.py`，使用 `pydantic-settings` 的 `BaseSettings` 載入環境變數
  - **目標**：集中管理所有設定，確保敏感資訊從環境變數注入，不硬編碼（A-11）
  - **設定欄位**：
    - `DATABASE_URL: str`（asyncpg 格式，如 `postgresql+asyncpg://user:pass@host/db`）
    - `SECRET_KEY: str`（JWT 對稱密鑰，HS256，A-02）
    - `ACCESS_TOKEN_EXPIRE_MINUTES: int = 15`
    - `REFRESH_TOKEN_EXPIRE_DAYS: int = 7`
    - `MAX_CONTENT_SIZE_MB: int = 5`（FR-001, A-05）
    - `APP_VERSION: str = "1.0.0"`
    - `DEBUG: bool = False`
  - **產出物**：`backend/app/core/config.py`

- [X] T005 [P] 建立 `.env.example`，提供所有環境變數的範例值與說明註解
  - **目標**：讓新開發者快速了解需配置的環境變數（SC-010）
  - **內容**：包含 `DATABASE_URL`, `SECRET_KEY`, `TEST_DATABASE_URL` 等所有 T004 定義的設定欄位，以佔位值填寫
  - **產出物**：`backend/.env.example`

- [X] T006 建立 `app/main.py`，初始化 FastAPI 應用程式，配置 lifespan、middleware 與路由掛載
  - **目標**：建立可啟動的 FastAPI 服務，掛載 `/api/v1` 路由（FR-024）
  - **內容**：
    - `lifespan` context manager（啟動時建立 DB engine，關閉時 dispose）
    - CORS middleware（開發環境允許所有 origins）
    - 統一 Exception Handler（回傳 `{ "detail": "...", "code": "..." }` 格式，FR-022）
    - 掛載 `api/v1/router.py`
    - `/health` 端點（FR-023，不含 Auth）
  - **產出物**：`backend/app/main.py`

- [X] T007 [P] 建立 `app/api/v1/router.py`，彙整所有端點路由
  - **目標**：統一路由進入點，確保所有 endpoint 以 `/api/v1` 為前綴
  - **內容**：`include_router` 各 endpoint 模組（auth、projects、partitions、documents、attributes）
  - **產出物**：`backend/app/api/v1/router.py`

- [X] T008 建立 `Dockerfile`，基於 Python 3.11 slim 映像，設定 uvicorn 啟動指令
  - **目標**：提供可用於生產環境的容器映像建構腳本（A-10）
  - **內容**：多階段建構（builder 安裝依賴 → runtime 精簡映像）、非 root 使用者執行、`EXPOSE 8000`、`CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`
  - **產出物**：`backend/Dockerfile`

- [X] T009 建立 `docker-compose.yml`，包含 `db`（PostgreSQL 15）和 `api`（FastAPI）服務
  - **目標**：一指令啟動完整開發環境（`docker compose up`），滿足 SC-010
  - **內容**：
    - `db` 服務：`postgres:15-alpine`，掛載 volume，設定 `POSTGRES_DB/USER/PASSWORD`
    - `api` 服務：掛載 `./backend` 為 volume（支援 hot reload），注入環境變數，依賴 `db` 健康狀態
    - 網路設定確保 `api` 可連接 `db`
  - **產出物**：`docker-compose.yml`（根目錄）

- [X] T010 [P] 建立 `alembic.ini` 與 `migrations/env.py`，設定 Alembic async migration 環境
  - **目標**：建立 Alembic 與 SQLAlchemy 2.0 async engine 整合的 migration 基礎設施（SC-008）
  - **內容**：
    - `alembic.ini`：設定 `script_location = migrations`，`sqlalchemy.url` 從環境變數讀取
    - `migrations/env.py`：使用 `AsyncEngine` + `run_sync` 模式（asyncpg 相容），引入 `Base.metadata`
    - `migrations/script.py.mako`：標準 migration 模板
  - **產出物**：`backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`

---

## Phase 2：資料庫

> **目標**：建立完整的 SQLAlchemy ORM 模型與初始 Migration，確保 Schema 可在全新環境執行（SC-008）。

- [X] T011 建立 `app/db/base.py`，定義 `DeclarativeBase` 與帶有命名慣例的 `MetaData`
  - **目標**：所有 ORM model 的共同基類，確保 constraint 命名一致（避免 Alembic 警告）
  - **內容**：`NAMING_CONVENTION` dict（ix/uq/ck/fk/pk），`class Base(DeclarativeBase)`，匯出供所有 model 使用
  - **產出物**：`backend/app/db/base.py`

- [X] T012 建立 `app/db/session.py`，設定 async SQLAlchemy engine 與 AsyncSession factory
  - **目標**：提供 `get_db` FastAPI dependency，管理請求範圍的資料庫連線（FR-001 ~ FR-017 所有 DB 操作的基礎）
  - **內容**：
    - `create_async_engine`（使用 `config.DATABASE_URL`，pool_size=5, max_overflow=10）
    - `async_session_maker = async_sessionmaker(engine, expire_on_commit=False)`
    - `async def get_db() -> AsyncGenerator[AsyncSession, None]`（yield session + 異常 rollback）
  - **產出物**：`backend/app/db/session.py`

- [X] T013 [P] 建立 `app/models/project.py`，定義 `Project` ORM model
  - **目標**：對應 `projects` 表（FR-016），UUID 主鍵、name、description、timestamps
  - **產出物**：`backend/app/models/project.py`

- [X] T014 [P] 建立 `app/models/partition.py`，定義 `Partition` ORM model
  - **目標**：對應 `partitions` 表（FR-017），包含 `project_id` FK、name UNIQUE、timestamps
  - **產出物**：`backend/app/models/partition.py`

- [X] T015 [P] 建立 `app/models/standard.py`，定義 `Standard` ORM model
  - **目標**：對應 `standards` 表（FR-010，A-12），支援 Seed Data 載入（ASPICE 3.1, ISO-26262, ISO-21434）
  - **產出物**：`backend/app/models/standard.py`

- [X] T016 [P] 建立 `app/models/attribute.py`，定義 `AttributeDefinition` 與 `DocumentAttributeValue` ORM model
  - **目標**：對應 `attribute_definitions` 與 `document_attribute_values` 表（FR-010 ~ FR-012），EAV 核心結構
  - **內容**：
    - `AttributeDefinition`：UUID PK、name、data_type（CHECK 約束）、`allowed_values: Mapped[Optional[list]] = mapped_column(JSONB)`、is_required、standard_id FK
    - `DocumentAttributeValue`：UUID PK、document_id FK（CASCADE）、attribute_id FK（RESTRICT）、value_string/value_integer/value_boolean、UNIQUE(document_id, attribute_id)、CHECK(最多一個值欄位非 null)
  - **產出物**：`backend/app/models/attribute.py`

- [X] T017 建立 `app/models/document.py`，定義 `Document` 與 `DocumentVersion` ORM model
  - **目標**：對應 `documents` 與 `document_versions` 表（FR-001 ~ FR-015），包含樂觀鎖與狀態機 CHECK 約束
  - **內容**：
    - `Document`：UUID PK、project_id/partition_id FK、title、content_md（CHECK not empty）、version（"1.0"）、`version_lock`（`__mapper_args__ = {"version_id_col": version_lock}`）、status（CHECK ENUM）、owner_id、timestamps、relationships（versions, attribute_values, audit_logs）
    - `DocumentVersion`：UUID PK、document_id FK（CASCADE）、version、content_md（快照）、modified_by、commit_message、created_at
  - **產出物**：`backend/app/models/document.py`

- [X] T018 [P] 建立 `app/models/audit_log.py`，定義 `AuditLog` ORM model
  - **目標**：對應 `audit_logs` 表（FR-008），記錄狀態轉換與文件操作歷程
  - **內容**：UUID PK、document_id FK（CASCADE）、operator_id、action_type（STATUS_TRANSITION/CONTENT_UPDATE/VERSION_FORK/DOCUMENT_CREATED）、old_status/new_status、`metadata: Mapped[Optional[dict]] = mapped_column(JSONB)`、created_at
  - **產出物**：`backend/app/models/audit_log.py`

- [X] T019 [P] 建立 `app/models/traceability.py`，定義 `TraceabilityLink` ORM model（Schema Stub）
  - **目標**：對應 `traceability_links` 表（FR-005，A-06），預建 schema 以支援刪除文件時的 409 檢查；業務邏輯留後續 Spec
  - **內容**：UUID PK、source_document_id/target_document_id FK（RESTRICT）、link_type、status（VALID/SUSPECT）、created_by、timestamps、UNIQUE(source, target, link_type)
  - **產出物**：`backend/app/models/traceability.py`

- [X] T020 [P] 建立 `app/models/refresh_token.py`（或整合至 auth models），定義 `RefreshToken` ORM model
  - **目標**：對應 `refresh_tokens` 表（FR-021），支援 Refresh Token Rotation 機制
  - **內容**：UUID PK、user_id（無 FK，JWT 身份）、token_hash（SHA-256，UNIQUE）、expires_at、revoked_at（null = 有效）、created_at
  - **產出物**：`backend/app/models/refresh_token.py`

- [X] T021 建立 Alembic 初始 Migration `migrations/versions/0001_initial_schema.py`
  - **目標**：包含所有表（projects, partitions, standards, documents, document_versions, attribute_definitions, document_attribute_values, audit_logs, traceability_links, refresh_tokens）的建立與刪除指令（SC-008）
  - **要求**：
    - `upgrade()` 按依賴順序建立（無 FK 先建），所有索引也在此建立
    - `downgrade()` 以相反順序 `DROP TABLE IF EXISTS`
    - 可在全新 PostgreSQL 15 環境執行無錯誤
  - **產出物**：`backend/migrations/versions/0001_initial_schema.py`

- [X] T022 建立 `migrations/versions/0002_seed_data.py`，載入 Standards 與 AttributeDefinition 初始資料
  - **目標**：在 Migration 中預置標準定義與屬性定義 Seed Data（A-12），確保測試與開發環境一致
  - **內容**：
    - Standards: `('ASPICE 3.1', '3.1')`, `('ISO-26262', '2018')`, `('ISO-21434', '2021')`
    - AttributeDefinitions: `ASIL_Level`(ENUM), `Document_Type`(ENUM, is_required=true), `Document_Owner`(STRING, is_required=true), `Safety_Goal_ID`(STRING), `Threat_ID`(STRING)
    - Partitions Seed（預設 5 層：SYS, HW, SWE, Safety, Security）
    - `downgrade()` 以 `DELETE FROM` 清除上述 Seed Data
  - **產出物**：`backend/migrations/versions/0002_seed_data.py`

---

## Phase 3：認證系統

> **目標**：實作 JWT HS256 簽發驗證與 RBAC 中介層（FR-018 ~ FR-021，US6）。

- [X] T023 [US6] 建立 `app/core/security.py`，實作 JWT 簽發、驗證與密碼雜湊函式
  - **目標**：集中所有安全相關操作，確保 JWT 密鑰從環境變數取得不硬編碼（FR-018, FR-019, A-02, A-11）
  - **內容**：
    - `create_access_token(data: dict, expires_delta: timedelta) -> str`：使用 `python-jose` HS256 簽發
    - `create_refresh_token() -> str`：生成安全隨機字串
    - `verify_token(token: str) -> TokenPayload`：驗證簽章與過期時間，過期時拋出 `AUTH_TOKEN_EXPIRED`
    - `hash_password(password: str) -> str` / `verify_password(plain, hashed) -> bool`：使用 `passlib bcrypt`
    - `hash_refresh_token(raw_token: str) -> str`：SHA-256 雜湊
  - **產出物**：`backend/app/core/security.py`

- [X] T024 [P] [US6] 建立 `app/schemas/auth.py`，定義認證相關 Pydantic v2 schema
  - **目標**：定義 Auth 端點的 Request/Response 資料結構（FR-021）
  - **內容**：
    - `LoginRequest`：username, password
    - `TokenResponse`：access_token, refresh_token, token_type, expires_in
    - `RefreshRequest`：refresh_token
    - `TokenPayload`：sub（user_id）, role, partition_access（list[UUID]）, exp, type
  - **產出物**：`backend/app/schemas/auth.py`

- [X] T025 [US6] 建立 FastAPI dependency `get_current_user`，驗證 Bearer JWT 並解析 TokenPayload
  - **目標**：所有受保護端點的統一認證 dependency（FR-018, FR-020）
  - **內容**：
    - 從 `Authorization: Bearer <token>` Header 提取 token
    - 呼叫 `security.verify_token()`，捕捉 `JWTError` → 回傳 `401 AUTH_MISSING_TOKEN` 或 `AUTH_TOKEN_EXPIRED`
    - 回傳 `TokenPayload`（包含 user_id、role、partition_access）
  - **實作位置**：`backend/app/api/dependencies.py`
  - **產出物**：`backend/app/api/dependencies.py`

- [X] T026 [US6] 建立 RBAC 輔助函式，驗證使用者的 Partition 存取權限
  - **目標**：實作 FR-020 的 Partition 存取控制，Admin 角色繞過所有 Partition 限制（FR-020, US6 AC-3, AC-5）
  - **內容**：
    - `require_partition_access(user: TokenPayload, partition_id: UUID) -> None`：若非 Admin 且 partition_id 不在 partition_access 清單中，拋出 `403 PARTITION_ACCESS_DENIED`
    - `require_role(user: TokenPayload, *allowed_roles: str) -> None`：角色不符時拋出 `403 PERMISSION_DENIED`
  - **實作位置**：`backend/app/api/dependencies.py`（擴充 T025）
  - **產出物**：`backend/app/api/dependencies.py`（更新）

- [X] T027 [US6] 建立 `app/crud/auth.py`，實作 Refresh Token 的 DB CRUD 操作
  - **目標**：支援 Refresh Token 儲存、查詢與 Rotation（revoke）（FR-021）
  - **內容**：
    - `create_refresh_token(db, user_id, token_hash, expires_at) -> RefreshToken`
    - `get_refresh_token_by_hash(db, token_hash) -> Optional[RefreshToken]`
    - `revoke_refresh_token(db, token_id) -> None`（設定 revoked_at）
    - `revoke_all_user_tokens(db, user_id) -> None`（登出用）
  - **產出物**：`backend/app/crud/auth.py`

- [X] T028 [US6] 建立 `app/api/v1/endpoints/auth.py`，實作 `POST /auth/login` 與 `POST /auth/refresh`
  - **目標**：提供 JWT 登入與 Token 更新端點（FR-021）
  - **`POST /auth/login` 流程**：
    1. 從 DB 查找使用者（本版本使用 Seed User，Assumption A-03）
    2. `verify_password` 驗證密碼
    3. `create_access_token`（payload 包含 sub/role/partition_access/exp/type）
    4. `create_refresh_token` → 存入 DB（hash 後）
    5. 回傳 `TokenResponse`
  - **`POST /auth/refresh` 流程**：
    1. SHA-256 hash refresh_token → 查 DB
    2. 驗證未過期、未 revoked
    3. `revoke_refresh_token`（Rotation：舊 token 立即失效）
    4. 簽發新 access_token + refresh_token，回傳 `TokenResponse`
  - **Error 處理**：無效帳密 → `401 AUTH_INVALID_TOKEN`；無效/過期 refresh_token → `401`
  - **產出物**：`backend/app/api/v1/endpoints/auth.py`

- [X] T029 [P] [US6] 建立 Seed User 資料，提供開發與測試使用的帳號
  - **目標**：滿足 Assumption A-03（使用者帳號以 Seed Data 預先載入）
  - **內容**：建立 `app/db/seed_users.py`，包含 4 個預設帳號（roles: Admin, PM, RD, QA），密碼以 bcrypt 雜湊存儲；整合至 `migrations/versions/0002_seed_data.py` 或獨立 `0003_seed_users.py`
  - **預設帳號**：`admin/admin123`, `pm.user/password`, `rd.user/password`, `qa.user/password`（僅限開發環境）
  - **產出物**：`backend/app/db/seed_users.py`、`backend/migrations/versions/0003_seed_users.py`

- [X] T030 [P] [US6] 實作 `/health` 端點，回傳服務狀態與 DB 連線狀態
  - **目標**：滿足 FR-023，用於 Railway/Docker 容器健康檢查
  - **內容**：嘗試執行輕量 DB query（如 `SELECT 1`），成功回傳 `{"status": "healthy", "database": "connected", "version": "..."}` (200)，失敗回傳 503
  - **位置**：`app/main.py`（直接掛載，不在 `/api/v1` 路徑下）
  - **產出物**：`backend/app/main.py`（更新）

- [X] T031 [P] [US6] 建立 `app/schemas/` 的共用 Pydantic schema（分頁、錯誤回應）
  - **目標**：定義可重用的分頁 Response 與統一錯誤回應格式（FR-022, FR-006）
  - **內容**：
    - `PaginatedResponse[T]`（Generic）：items, total, page, page_size, has_next, has_prev
    - `ErrorResponse`：detail, code
    - `UUIDField`：UUID v4 格式驗證 Validator（Edge Case 防護）
  - **產出物**：`backend/app/schemas/common.py`

- [X] T032 [US6] 建立 `app/crud/base.py`，定義 `CRUDBase` 泛型類別
  - **目標**：提供所有 CRUD 模組的公共基礎（get, list, create, update, delete），減少重複程式碼
  - **內容**：`class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType])`，方法：`get_by_id`, `get_multi`, `create`, `update`, `delete`（均為 async）
  - **產出物**：`backend/app/crud/base.py`

---

## Phase 4：專案與 Partition 管理 API

> **目標**：實作 Admin 可操作的 Projects 與 Partitions 管理端點（FR-016, FR-017，US3）。

- [X] T033 [P] [US3] 建立 `app/schemas/project.py`，定義 Project 相關 Pydantic v2 schema
  - **目標**：定義 Projects API 的 Request/Response 資料結構（FR-016）
  - **內容**：`ProjectCreate`（name, description）、`ProjectRead`（id, name, description, created_at, updated_at）、`ProjectList`（PaginatedResponse[ProjectRead]）
  - **產出物**：`backend/app/schemas/project.py`

- [X] T034 [P] [US3] 建立 `app/schemas/partition.py`，定義 Partition 相關 Pydantic v2 schema
  - **目標**：定義 Partitions API 的 Request/Response 資料結構（FR-017）
  - **內容**：`PartitionCreate`（name, description, project_id）、`PartitionRead`（id, name, description, project_id, created_at）
  - **產出物**：`backend/app/schemas/partition.py`

- [X] T035 [US3] 建立 `app/crud/project.py`，實作 Project DB 操作
  - **目標**：繼承 `CRUDBase`，提供 Project 的 create、get_by_id、get_multi、check_has_documents 等操作（FR-016）
  - **內容**：
    - `create_project(db, project_in) -> Project`
    - `get_project(db, project_id) -> Optional[Project]`
    - `get_projects(db, page, page_size) -> tuple[list[Project], int]`
    - `has_documents(db, project_id) -> bool`（用於刪除時的 409 檢查，US3 AC-4）
  - **產出物**：`backend/app/crud/project.py`

- [X] T036 [US3] 建立 `app/crud/partition.py`，實作 Partition DB 操作
  - **目標**：提供 Partition 的 create、get_by_id、get_multi 等操作（FR-017）
  - **內容**：
    - `create_partition(db, partition_in) -> Partition`
    - `get_partition(db, partition_id) -> Optional[Partition]`
    - `get_partitions_by_project(db, project_id) -> list[Partition]`
    - `validate_partition_belongs_to_project(db, partition_id, project_id) -> bool`（用於文件建立的 Edge Case 驗證）
  - **產出物**：`backend/app/crud/partition.py`

- [X] T037 [US3] 建立 `app/api/v1/endpoints/projects.py`，實作 Projects API 端點
  - **目標**：對應 `contracts/projects.md` 的所有端點（FR-016，US3 AC-1 ~ AC-4）
  - **端點**：
    - `POST /projects`：Admin only → `require_role(..., "Admin")`，呼叫 `crud.project.create_project`，回傳 201
    - `GET /projects`：All roles，分頁查詢
    - `GET /projects/{id}`：All roles，404 若不存在
    - `DELETE /projects/{id}`：Admin only，呼叫 `has_documents` → 409 若有文件（US3 AC-4）
  - **產出物**：`backend/app/api/v1/endpoints/projects.py`

- [X] T038 [US3] 建立 `app/api/v1/endpoints/partitions.py`，實作 Partitions API 端點
  - **目標**：對應 `contracts/partitions.md`（FR-017，US3 AC-1 ~ AC-3）
  - **端點**：
    - `POST /partitions`：Admin only，驗證 project_id 存在，建立 Partition，回傳 201（US3 AC-2）
    - `GET /partitions`：All roles，支援 `project_id` 篩選
  - **產出物**：`backend/app/api/v1/endpoints/partitions.py`

- [X] T039 [P] [US3] 在 `app/api/v1/router.py` 中掛載 Projects 與 Partitions 路由
  - **目標**：將 T037、T038 的 router 掛載至主路由（`/api/v1/projects`, `/api/v1/partitions`）
  - **產出物**：`backend/app/api/v1/router.py`（更新）

- [X] T040 [US3] 手動執行整合測試：Admin 建立 Project → 建立 Partition → 非 Admin 嘗試建立被拒
  - **目標**：驗證 Phase 4 可獨立運作，確認 US3 AC-1 ~ AC-4 Acceptance Scenarios 通過
  - **步驟**：啟動 docker-compose → 執行 migration → 以 admin token 建立 project/partition → 以 rd token 嘗試建立 partition（期望 403）
  - **產出物**：手動驗證記錄（記入 PR 描述或 quickstart.md）

---

## Phase 5：文件管理核心 API

> **目標**：實作文件 CRUD、狀態機、版本歷程（FR-001 ~ FR-015，US1, US2, US5）。

- [X] T041 [P] [US1] 建立 `app/schemas/document.py`，定義文件相關 Pydantic v2 schema
  - **目標**：定義所有 Document 端點的 Request/Response 資料結構（FR-001 ~ FR-015）
  - **內容**：
    - `DocumentAttributeValueInput`：attribute_id（UUID）, value（Any）
    - `DocumentCreate`：project_id, partition_id, title, content_md（min_length=1）, attributes（list[DocumentAttributeValueInput]，可選）
    - `DocumentUpdate`：content_md, attributes, commit_message（必填）, current_version_lock（整數，用於樂觀鎖）
    - `DocumentRead`：id, project_id, partition_id, title, content_md, version, version_lock, status, owner_id, created_at, updated_at, attributes（list[AttributeValueRead]）
    - `DocumentListItem`：id, title, version, status, owner_id, updated_at（不含 content_md 和 attributes）
    - `StatusTransitionRequest`：status（DRAFT/REVIEW/APPROVED/OBSOLETE）
    - `StatusTransitionResponse`：id, status, version, updated_at, audit_log_id
    - `VersionListItem`：id, version, modified_by, commit_message, created_at
    - `VersionRead`：id, document_id, version, content_md, modified_by, commit_message, created_at
  - **產出物**：`backend/app/schemas/document.py`

- [X] T042 [US1] 建立 `app/services/document_service.py`，封裝文件業務邏輯
  - **目標**：集中管理狀態機轉換、版本號遞增、Version Fork、AuditLog 寫入等業務邏輯（FR-002, FR-004, FR-007 ~ FR-009, FR-015），確保可獨立 unit test
  - **內容**：
    - `increment_minor_version(current_version: str) -> str`：`"1.0" → "1.1"`, `"1.9" → "1.10"` 等
    - `increment_major_version(current_version: str) -> str`：`"1.x" → "2.0"`（Version Fork）
    - `VALID_STATUS_TRANSITIONS: dict`：`{"DRAFT": ["REVIEW"], "REVIEW": ["APPROVED", "DRAFT"], "APPROVED": ["OBSOLETE"], "OBSOLETE": []}`
    - `validate_status_transition(current_status, new_status) -> None`：非法路徑拋出 `422 INVALID_STATUS_TRANSITION`
    - `check_transition_permission(user_role, current_status, new_status) -> None`：角色授權矩陣（FR-007，US2 AC-5）
    - `create_version_snapshot(db, document, modified_by, commit_message) -> DocumentVersion`：寫入版本快照（FR-015）
    - `write_audit_log(db, document_id, operator_id, action_type, old_status, new_status, metadata) -> AuditLog`（FR-008）
  - **產出物**：`backend/app/services/document_service.py`

- [X] T043 [US1] 建立 `app/crud/document.py`，實作文件 DB CRUD 操作
  - **目標**：提供所有 Document DB 操作，不含業務邏輯（FR-001 ~ FR-015）
  - **內容**：
    - `create_document(db, document_in, owner_id) -> Document`：INSERT + 同步 version snapshot（initial 1.0）
    - `get_document(db, document_id) -> Optional[Document]`：含 joinedload attribute_values
    - `get_documents(db, filters, page, page_size) -> tuple[list[Document], int]`：支援 project_id/partition_id/status/owner_id 篩選，按 updated_at DESC 排序（FR-006）
    - `update_document(db, document, update_in) -> Document`：版本快照 + 樂觀鎖比對（FR-004）
    - `delete_document(db, document_id) -> None`：先查 traceability_links → 有則 409（FR-005）
    - `get_versions(db, document_id) -> list[DocumentVersion]`：按 created_at DESC（FR-013）
    - `get_version_by_number(db, document_id, version) -> Optional[DocumentVersion]`（FR-014）
    - `upsert_attribute_values(db, document_id, attribute_inputs) -> None`：含重複 attribute_id 合併邏輯（Edge Case）
  - **產出物**：`backend/app/crud/document.py`

- [X] T044 [US1] 建立 `app/services/attribute_service.py`，實作 EAV 屬性驗證邏輯
  - **目標**：集中 EAV 屬性的型別驗證、ENUM 合法性驗證、必填屬性檢查（FR-011, FR-012，SC-005）
  - **內容**：
    - `validate_attribute_value(attr_def: AttributeDefinition, value: Any) -> None`：依 data_type 驗證型別與 ENUM 值合法性，失敗拋出 `422 INVALID_ATTRIBUTE_VALUE`
    - `check_required_attributes(db, provided_attribute_ids: list[UUID]) -> None`：查詢所有 is_required=true 的屬性，對比是否均已提供，缺少則拋出 `422 REQUIRED_ATTRIBUTE_MISSING`（FR-012，SC-005）
    - `resolve_value_column(data_type, value) -> dict`：將 Python 值對映至 EAV 分欄（value_string/value_integer/value_boolean）
  - **產出物**：`backend/app/services/attribute_service.py`

- [X] T045 [US1] [US5] 建立 `app/api/v1/endpoints/documents.py`，實作 Document CRUD 端點
  - **目標**：實作文件建立與查詢端點（FR-001 ~ FR-006，US1 AC-1 ~ AC-4，US5 AC-1）
  - **`POST /documents` 流程**（FR-001, FR-002）：
    1. `get_current_user` 驗證 JWT（FR-018）
    2. `require_partition_access`（FR-020）
    3. 驗證 `content_md` 大小 ≤ 5MB（回傳 413，A-05）
    4. 驗證 `partition_id` 屬於 `project_id`（422 PARTITION_PROJECT_MISMATCH）
    5. `attribute_service.check_required_attributes`（FR-012）
    6. 批次 `attribute_service.validate_attribute_value`（FR-011）
    7. `crud.document.create_document`（自動設定 UUID/version 1.0/status DRAFT）
    8. `crud.document.upsert_attribute_values`
    9. `document_service.write_audit_log`（DOCUMENT_CREATED）
    10. 回傳 201 + `DocumentRead`
  - **`GET /documents` 流程**（FR-006）：含分頁、篩選、Partition 存取控制
  - **`GET /documents/{id}` 流程**（FR-003）：Partition 存取控制（403 不洩露存在，US1 AC-4）
  - **產出物**：`backend/app/api/v1/endpoints/documents.py`（PUT, DELETE, PATCH, versions 端點於 T046~T048 繼續）

- [X] T046 [US1] [US2] 在 `documents.py` 新增 `PUT /documents/{id}` 端點（文件更新）
  - **目標**：實作文件內容更新，含版本遞增、樂觀鎖、APPROVED 狀態阻止（FR-004, FR-009，US1 AC-3，US2 AC-3）
  - **流程**：
    1. 驗證 JWT 與 Partition 存取權
    2. 驗證使用者為 Owner 或 Admin（`403 PERMISSION_DENIED`）
    3. 若 status=APPROVED → 回傳 `409 DOCUMENT_APPROVED`（US2 AC-3）
    4. 比對 `current_version_lock` == DB 值 → 不符則 `409 VERSION_CONFLICT`（Edge Case）
    5. 驗證並儲存屬性值
    6. 遞增 minor version（如 1.0 → 1.1）
    7. `crud.document.upsert_attribute_values`
    8. `document_service.create_version_snapshot`（FR-015）
    9. `document_service.write_audit_log`（CONTENT_UPDATE）
    10. 回傳 200 + `DocumentRead`（version 已遞增）
  - **產出物**：`backend/app/api/v1/endpoints/documents.py`（更新）

- [X] T047 [US2] 在 `documents.py` 新增 `PATCH /documents/{id}/status` 端點（狀態轉換）
  - **目標**：實作四段式狀態機（FR-007, FR-008，US2 AC-1 ~ AC-5）
  - **流程**：
    1. 驗證 JWT 與 Partition 存取權
    2. `document_service.validate_status_transition`（422 INVALID_STATUS_TRANSITION，US2 AC-4）
    3. `document_service.check_transition_permission`（403 PERMISSION_DENIED，US2 AC-5）
    4. 更新 document.status
    5. `document_service.write_audit_log`（STATUS_TRANSITION，含 old_status, new_status，FR-008，SC-004）
    6. 回傳 200 + `StatusTransitionResponse`（含 audit_log_id）
  - **產出物**：`backend/app/api/v1/endpoints/documents.py`（更新）

- [X] T048 [US5] 在 `documents.py` 新增版本歷程端點
  - **目標**：實作版本列表與版本快照查詢（FR-013, FR-014，US5 AC-2, AC-3）
  - **端點**：
    - `GET /documents/{id}/versions`：回傳 `{ document_id, current_version, versions: [VersionListItem] }`（由新至舊）
    - `GET /documents/{id}/versions/{version}`：回傳 `VersionRead`（含完整 content_md 快照）
  - **產出物**：`backend/app/api/v1/endpoints/documents.py`（更新）

- [X] T049 [US1] 在 `documents.py` 新增 `DELETE /documents/{id}` 端點
  - **目標**：實作文件刪除，含追溯連結檢查（FR-005，Edge Case）
  - **流程**：Admin only → 查 `traceability_links` → 有則 `409 DOCUMENT_HAS_DEPENDENCIES` → `crud.document.delete_document` → 204
  - **產出物**：`backend/app/api/v1/endpoints/documents.py`（更新）

- [X] T050 [P] [US1] 在 `app/api/v1/router.py` 中掛載 Documents 路由
  - **目標**：將所有 Document 端點掛載至 `/api/v1/documents`
  - **產出物**：`backend/app/api/v1/router.py`（更新）

- [X] T051 [US1] 實作 content_md 大小限制中介層（413 Request Entity Too Large）
  - **目標**：在請求解析前驗證 content_md ≤ 5MB（Edge Case，A-05）
  - **內容**：在 `POST /documents` 與 `PUT /documents/{id}` 的 Pydantic schema 中使用 `@field_validator`，或在 middleware 中設定 `max_request_size`；超出時回傳 `413 CONTENT_TOO_LARGE`
  - **產出物**：`backend/app/schemas/document.py`（更新）或 `backend/app/main.py`（middleware）

- [X] T052 [US1] [US5] 驗證文件 UUID 路徑參數格式（422 Edge Case）
  - **目標**：非合法 UUID v4 格式的路徑參數應回傳 `422 VALIDATION_ERROR`，不是 `500`（Edge Case）
  - **內容**：在 FastAPI 路由的路徑參數型別宣告為 `UUID`（`from uuid import UUID`），FastAPI 自動驗證格式並回傳 422
  - **產出物**：`backend/app/api/v1/endpoints/documents.py`（確認型別標注）

- [X] T053 [US1] 驗證 `partition_id` 屬於 `project_id` 的應用層檢查
  - **目標**：建立文件時，若 partition_id 不屬於 project_id，回傳 `422 PARTITION_PROJECT_MISMATCH`（Edge Case）
  - **內容**：在 `POST /documents` handler 中呼叫 `crud.partition.validate_partition_belongs_to_project(db, partition_id, project_id)`，失敗拋出 422
  - **產出物**：`backend/app/api/v1/endpoints/documents.py`（更新）

- [X] T054 [US2] 驗證空 Markdown 內容的 422 回應（Edge Case）
  - **目標**：content_md 為空字串或僅含空白字元時，回傳 `422 Unprocessable Entity`（Edge Case）
  - **內容**：在 `DocumentCreate` schema 中加入 `@field_validator("content_md")` 驗證 `value.strip() != ""`，並在 Pydantic 設定 `min_length=1`
  - **產出物**：`backend/app/schemas/document.py`（確認 validator）

- [X] T055 [US2] 驗證稽核日誌完整性：所有狀態轉換均寫入 AuditLog
  - **目標**：確保 FR-008 實作正確，SC-004（日誌遺失率 0%）的程式層保障
  - **內容**：在 `document_service.write_audit_log` 中使用資料庫 transaction，確保 AuditLog 與 Document 狀態更新在同一 transaction 內提交（atomic）
  - **產出物**：`backend/app/services/document_service.py`（更新，確認 transaction scope）

---

## Phase 6：EAV 動態屬性 API

> **目標**：實作 AttributeDefinition CRUD 端點（FR-010 ~ FR-012，US4）。

- [X] T056 [P] [US4] 建立 `app/schemas/attribute.py`，定義屬性定義相關 Pydantic v2 schema
  - **目標**：定義 Attribute Definitions API 的 Request/Response 資料結構（FR-010）
  - **內容**：
    - `AttributeDefinitionCreate`：name（1~100 字元）、data_type（STRING/INTEGER/BOOLEAN/ENUM）、allowed_values（ENUM 時必填，非空 list[str]）、is_required（預設 false）、standard_id（選填 UUID）
    - `AttributeDefinitionRead`：id, name, data_type, allowed_values, is_required, standard_id, standard_name, created_at
    - `AttributeValueRead`：attribute_id, name, value, data_type（用於 DocumentRead 的 attributes 欄位）
    - `@model_validator`：確保 ENUM 時 allowed_values 非空
  - **產出物**：`backend/app/schemas/attribute.py`

- [X] T057 [US4] 建立 `app/crud/attribute.py`，實作 AttributeDefinition DB CRUD 操作
  - **目標**：提供屬性定義的 create、get、list 等操作（FR-010）
  - **內容**：
    - `create_attribute_definition(db, attr_in) -> AttributeDefinition`
    - `get_attribute_definition(db, attr_id) -> Optional[AttributeDefinition]`
    - `get_attribute_definitions(db, standard_id, is_required, page, page_size) -> tuple[list[AttributeDefinition], int]`
    - `get_required_attribute_ids(db) -> list[UUID]`（用於 FR-012 必填屬性檢查）
    - `get_attributes_by_ids(db, attr_ids: list[UUID]) -> list[AttributeDefinition]`（批次查詢，用於值驗證）
  - **產出物**：`backend/app/crud/attribute.py`

- [X] T058 [US4] 建立 `app/api/v1/endpoints/attributes.py`，實作 AttributeDefinition API 端點
  - **目標**：對應 `contracts/attribute-definitions.md`（FR-010，US4 AC-4）
  - **端點**：
    - `POST /attribute-definitions`：Admin only → `require_role("Admin")` → 驗證 standard_id 存在 → `crud.attribute.create_attribute_definition` → 201（US4 AC-4）
    - `GET /attribute-definitions`：All roles → 支援 `standard_id`、`is_required` 篩選 → 分頁回傳
  - **Error 處理**：非 Admin → 403；standard_id 不存在 → 404；ENUM 無 allowed_values → 422
  - **產出物**：`backend/app/api/v1/endpoints/attributes.py`

- [X] T059 [P] [US4] 在 `app/api/v1/router.py` 中掛載 Attribute Definitions 路由
  - **目標**：將 T058 的 router 掛載至 `/api/v1/attribute-definitions`
  - **產出物**：`backend/app/api/v1/router.py`（更新，最終版本）

- [X] T060 [US4] 驗證 EAV 型別系統：ENUM 值合法性與不合法值的 422 回應
  - **目標**：確保 SC-005（EAV 驗證覆蓋率 100%），實作 US4 AC-1 ~ AC-3 的驗證邏輯
  - **內容**：完善 `attribute_service.validate_attribute_value`：
    - STRING：值必須為字串
    - INTEGER：值必須可轉換為 int
    - BOOLEAN：值必須為 bool（不接受 "yes"/"no" 字串）
    - ENUM：值必須在 `allowed_values` 列表中，否則 `422 INVALID_ATTRIBUTE_VALUE`（US4 AC-3）
  - **產出物**：`backend/app/services/attribute_service.py`（確認完整實作）

- [X] T061 [US4] 驗證重複 attribute_id 的合併策略
  - **目標**：同一文件的 attributes 陣列中含重複 attribute_id 時，後者覆蓋前者（Edge Case，contracts/attribute-definitions.md 合併策略）
  - **內容**：在 `crud.document.upsert_attribute_values` 中，使用 Python dict 對 `attribute_id` 去重（後者覆蓋），再批次 upsert（使用 PostgreSQL `ON CONFLICT DO UPDATE`）
  - **產出物**：`backend/app/crud/document.py`（確認 upsert 邏輯）

- [X] T062 [US4] 完成 `DocumentRead` 的屬性值序列化，確保 `GET /documents/{id}` 正確回傳 EAV 屬性
  - **目標**：`DocumentRead.attributes` 欄位應正確從 EAV 分欄（value_string/value_integer/value_boolean）序列化為統一 `value` 欄位（FR-003，US4 AC-1）
  - **內容**：在 `app/schemas/document.py` 的 `DocumentRead` 加入 `@field_validator` 或 `model_validator`，從 `document_attribute_values` 中組裝 `AttributeValueRead` 清單（含 attribute name 與 data_type）
  - **產出物**：`backend/app/schemas/document.py`（確認序列化邏輯）

---

## Phase 7：測試套件

> **目標**：達成 85% 以上測試覆蓋率，涵蓋正向與負向情境（SC-007）。

- [X] T063 建立 `tests/conftest.py`，定義所有 pytest fixtures
  - **目標**：提供測試環境的共用 fixtures，確保測試可在獨立 PostgreSQL test database 執行（SC-008）
  - **內容**：
    - `event_loop`：asyncio event loop fixture
    - `test_engine`：建立 test DB（`TEST_DATABASE_URL`），執行所有 migration，測試結束後 drop
    - `test_db`：每個測試提供 transactional session（測試後 rollback，確保隔離）
    - `async_client`：使用 `httpx.AsyncClient` + `ASGITransport`，覆蓋 `get_db` dependency
    - `admin_token`, `rd_token`, `qa_token`, `pm_token`：各角色的 JWT fixture（含 partition_access）
    - `sample_project`, `sample_partition`, `sample_document`：基礎測試資料 fixture
  - **產出物**：`backend/tests/conftest.py`

- [X] T064 [P] 建立 `tests/unit/test_security.py`，測試 JWT 簽發與驗證邏輯
  - **目標**：單元測試 `app/core/security.py` 的所有函式（US6）
  - **測試案例**：
    - `test_create_access_token_contains_required_fields`：payload 包含 sub/role/partition_access/exp/type
    - `test_verify_token_success`：合法 token 可正確解析
    - `test_verify_token_expired`：過期 token 拋出 AUTH_TOKEN_EXPIRED
    - `test_verify_token_invalid_signature`：篡改 token 拋出 AUTH_INVALID_TOKEN
    - `test_password_hash_and_verify`：密碼雜湊與驗證正確
  - **產出物**：`backend/tests/unit/test_security.py`

- [X] T065 [P] 建立 `tests/unit/test_document_service.py`，測試狀態機與版本遞增邏輯
  - **目標**：單元測試 `app/services/document_service.py`（US2 狀態機邏輯）
  - **測試案例**：
    - `test_valid_status_transitions`：DRAFT→REVIEW→APPROVED→OBSOLETE 均合法
    - `test_invalid_status_transitions`：APPROVED→DRAFT、OBSOLETE→DRAFT 等回傳 422
    - `test_increment_minor_version`：`"1.0" → "1.1"`, `"1.9" → "1.10"`, `"2.3" → "2.4"`
    - `test_increment_major_version`：`"1.5" → "2.0"`（Version Fork）
    - `test_check_transition_permission_rd_cannot_approve`：RD 角色不能 APPROVE（403）
    - `test_check_transition_permission_admin_can_all`：Admin 可執行所有轉換
  - **產出物**：`backend/tests/unit/test_document_service.py`

- [X] T066 [P] 建立 `tests/unit/test_attribute_service.py`，測試 EAV 驗證邏輯
  - **目標**：單元測試 `app/services/attribute_service.py`（US4 EAV 驗證）
  - **測試案例**：
    - `test_validate_string_value_success`
    - `test_validate_integer_value_success_and_fail`：整數合法，"forty-two" 失敗
    - `test_validate_enum_value_in_allowed_values`：`"ASIL B"` in QM/A/B/C/D 合法
    - `test_validate_enum_value_not_in_allowed_values`：`"ASIL E"` 回傳 422 INVALID_ATTRIBUTE_VALUE
    - `test_validate_boolean_strict`：`"yes"` 不接受，`True` 合法
    - `test_resolve_value_column_string`：STRING 對映至 value_string
    - `test_resolve_value_column_integer`：INTEGER 對映至 value_integer
  - **產出物**：`backend/tests/unit/test_attribute_service.py`

- [X] T067 建立 `tests/integration/test_auth.py`，端對端測試 Auth 流程
  - **目標**：驗證 JWT 登入、Token 刷新、無效 Token 處理（FR-018, FR-021，US6 AC-1 ~ AC-5）
  - **測試案例**：
    - `test_login_success`：正確帳密 → 200, 回傳 access_token 與 refresh_token
    - `test_login_wrong_password`：錯誤密碼 → 401 AUTH_INVALID_TOKEN
    - `test_refresh_token_success`：合法 refresh_token → 200, 回傳新 access_token
    - `test_refresh_token_rotation`：舊 refresh_token 使用後失效 → 401
    - `test_access_protected_without_token`：無 Token → 401 AUTH_MISSING_TOKEN（US6 AC-1）
    - `test_access_protected_with_expired_token`：過期 Token → 401 AUTH_TOKEN_EXPIRED（US6 AC-2）
  - **產出物**：`backend/tests/integration/test_auth.py`

- [X] T068 建立 `tests/integration/test_documents.py`，端對端測試文件管理完整流程
  - **目標**：涵蓋 US1、US2、US5 的所有 Acceptance Scenarios 及 Edge Cases
  - **測試案例**（正向）：
    - `test_create_document_with_attributes`：US1 AC-1（201, version 1.0, DRAFT, EAV 正確）
    - `test_get_document_by_id`：US1 AC-2（200, 內容與屬性完整）
    - `test_update_document_increments_version`：US1 AC-3（200, 1.0→1.1, 舊版本可查）
    - `test_document_status_transition_draft_to_review`：US2 AC-1（200, audit log 存在）
    - `test_document_status_transition_to_approved`：US2 AC-2（版本號鎖定）
    - `test_get_version_history`：US5 AC-2（versions 由新至舊）
    - `test_get_version_snapshot`：US5 AC-3（版本快照 content_md 正確）
  - **測試案例**（負向/Edge Case）：
    - `test_access_other_partition_document_returns_403`：US1 AC-4（403，不洩露存在）
    - `test_update_approved_document_returns_409`：US2 AC-3（409 DOCUMENT_APPROVED）
    - `test_invalid_status_transition_returns_422`：US2 AC-4（422 INVALID_STATUS_TRANSITION）
    - `test_non_owner_cannot_advance_to_review`：US2 AC-5（403）
    - `test_concurrent_update_optimistic_lock`：並發寫入 → 409 VERSION_CONFLICT（Edge Case）
    - `test_empty_content_md_returns_422`：空 Markdown → 422（Edge Case）
    - `test_invalid_uuid_path_param_returns_422`：非 UUID → 422（Edge Case）
    - `test_partition_project_mismatch_returns_422`：Partition 不屬於 Project → 422（Edge Case）
    - `test_content_size_over_limit_returns_413`：>5MB → 413（Edge Case）
  - **產出物**：`backend/tests/integration/test_documents.py`

- [X] T069 [P] 建立 `tests/integration/test_projects.py` 與 `tests/integration/test_attributes.py`
  - **目標**：驗證 Projects/Partitions 與 AttributeDefinitions 的 API 行為（US3, US4）
  - **test_projects.py 測試案例**：
    - `test_create_project_as_admin`：US3 AC-1（201）
    - `test_create_project_as_non_admin_returns_403`：US3 AC-3（403）
    - `test_create_partition_as_admin`：US3 AC-2（201）
    - `test_delete_project_with_documents_returns_409`：US3 AC-4（409）
  - **test_attributes.py 測試案例**：
    - `test_create_attribute_definition_as_admin`：US4 AC-4（201）
    - `test_create_enum_without_allowed_values_returns_422`：422 VALIDATION_ERROR
    - `test_create_document_missing_required_attribute_returns_422`：US4 AC-2（422 REQUIRED_ATTRIBUTE_MISSING）
    - `test_create_document_with_invalid_enum_value_returns_422`：US4 AC-3（422 INVALID_ATTRIBUTE_VALUE）
    - `test_duplicate_attribute_id_merges`：重複 attribute_id 後者覆蓋（Edge Case）
  - **產出物**：`backend/tests/integration/test_projects.py`, `backend/tests/integration/test_attributes.py`

- [X] T070 建立 `tests/contract/test_openapi_schema.py`，驗證 OpenAPI schema 符合預期
  - **目標**：確保 FR-024（OpenAPI 文件）自動生成正確，所有端點均已定義（SC-009）
  - **測試案例**：
    - `test_openapi_json_accessible`：`GET /openapi.json` 回傳 200
    - `test_all_expected_paths_exist`：驗證以下路徑均出現在 schema 中：`/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/projects`, `/api/v1/partitions`, `/api/v1/documents`, `/api/v1/documents/{id}`, `/api/v1/documents/{id}/status`, `/api/v1/documents/{id}/versions`, `/api/v1/attribute-definitions`, `/health`
    - `test_docs_endpoint_accessible`：`GET /docs` 回傳 200（Swagger UI）
    - `test_required_security_scheme_defined`：OpenAPI schema 中 bearerAuth 安全方案已定義
  - **產出物**：`backend/tests/contract/test_openapi_schema.py`

---

## 依賴圖（執行順序）

```
Phase 1（基礎建設）
  T001 → T002, T003, T004, T005（並行）
  T004 → T006 → T007（串行）
  T001 → T008, T009, T010（並行）

Phase 2（資料庫）
  T001 → T011 → T012（串行，DB 基礎）
  T011 → T013, T014, T015, T016, T018, T019, T020（並行 ORM models）
  T017（依賴 T013, T014, T016）
  T013~T020 全部完成 → T021（初始 Migration）
  T021 → T022（Seed Data Migration）

Phase 3（認證）
  T004, T012 → T023（security.py）
  T023 → T024, T025, T026（並行）
  T025, T026 → T027, T028（串行）
  T021, T022 → T029（Seed Users）
  T006 → T030（health endpoint）
  T031, T032（可並行於 Phase 3 早期）

Phase 4（Projects/Partitions）
  T032 → T035, T036（CRUD）
  T033, T034（schema，並行）
  T035 → T037；T036 → T038（串行）
  T037, T038 → T039（router 掛載）

Phase 5（文件管理）
  T032, T035, T036 → T043（document CRUD）
  T041（schema，並行於 Phase 5 早期）
  T043 → T042（service 依賴 CRUD）
  T043, T042 → T044（attribute service）
  T041, T042, T043, T044 → T045~T055（endpoints）

Phase 6（EAV）
  T044, T057 → T058（endpoint）
  T056（schema，並行）
  T044 → T060, T061, T062

Phase 7（測試）
  所有 Phase 1~6 完成 → T063（conftest）
  T063 → T064, T065, T066（並行 unit tests）
  T063 → T067, T068, T069, T070（並行 integration tests）
```

---

## 平行執行建議

### Sprint 1（基礎建設 + 資料庫）
可並行：T002, T003, T005（需求文件） | T013, T014, T015, T016, T018, T019, T020（ORM models）

### Sprint 2（認證 + 專案管理）
可並行：T024, T031, T033, T034 | T025, T026 | T035, T036

### Sprint 3（文件 API 核心）
可並行：T041, T042, T043, T044 | T056, T057

### Sprint 4（測試套件）
可並行：T064, T065, T066 | T067, T068, T069, T070

---

## 獨立可測試增量

| 里程碑 | 可交付功能 | 對應任務 |
|--------|-----------|----------|
| **M1** | Docker 環境啟動 + DB migration 成功 | T001~T022 |
| **M2** | JWT 登入/刷新可用 + /health 正常 | T023~T032 |
| **M3** | 專案與 Partition 管理 API 可用（US3） | T033~T040 |
| **M4** | 文件 CRUD + 狀態機 + 版本歷程（US1, US2, US5） | T041~T055 |
| **M5** | EAV 動態屬性 API 可用（US4） | T056~T062 |
| **M6** | 測試覆蓋率 ≥ 85%（SC-007） | T063~T070 |

**MVP Scope**（優先交付）：M1 + M2 + M4（文件管理核心功能，對應 P1 User Stories 1, 2, 6）

---

## 非功能性需求驗收標準

| SC 編號 | 驗收標準 | 對應任務 |
|---------|---------|---------|
| SC-001 | POST /documents p90 ≤ 500ms | T045（async DB）|
| SC-002 | GET /documents/{id} p99 ≤ 200ms | T043（索引優化）|
| SC-003 | 50 并發無資料不一致 | T017（樂觀鎖）、T046（VERSION_CONFLICT）|
| SC-004 | AuditLog 遺失率 0% | T055（atomic transaction）|
| SC-005 | EAV 驗證 100% 覆蓋 | T044、T060、T066 |
| SC-006 | 跨 Partition 資料洩露 0 件 | T025、T026、T068 |
| SC-007 | 測試覆蓋率 ≥ 85% | T063~T070（`pytest --cov`）|
| SC-008 | Migration 可在全新環境執行 | T021、T022（含 downgrade）|
| SC-009 | OpenAPI 文件自動生成 | T006（FastAPI 內建）、T070 |
| SC-010 | 新人 30 分鐘內啟動環境 | T009（docker compose）、T005（.env.example）|
