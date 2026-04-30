# Phase 0 Research: 文件管理後端 API

**Feature**: `doc-management-backend`  
**Date**: 2025-04-30  
**Status**: Complete — 所有 NEEDS CLARIFICATION 項目已解決

> 本 Spec 的技術假設（A-01~A-12）已由 spec.md 明確定義，無須外部釐清。
> 本文件記錄各關鍵技術決策的研究結論、選型理由與被排除的替代方案。

---

## R-001：FastAPI Async SQLAlchemy 2.0 Session 管理模式

**Decision**: 使用 SQLAlchemy 2.0 `AsyncSession` + `async_sessionmaker`，以 FastAPI dependency（`get_db`）注入至每個 request handler。

**Rationale**:
- SQLAlchemy 2.0 的 `AsyncSession` 原生支援 Python `async/await`，與 FastAPI 的 async event loop 完全對齊
- Dependency injection 確保每個 request 擁有獨立 session，避免跨 request 的 session 狀態污染
- `async_sessionmaker` + `expire_on_commit=False` 可在 commit 後安全存取 ORM 物件屬性（避免 `DetachedInstanceError`）

**Pattern**:
```python
# db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Alternatives Considered**:
- `scoped_session`（Sync）：阻塞 event loop，在高並發下造成效能瓶頸，排除
- 手動 session 管理（不使用 dependency）：增加重複程式碼，session 生命週期難以保證，排除
- SQLModel（基於 SQLAlchemy）：與 Pydantic v2 整合複雜度較高，且限制了 SQLAlchemy 進階功能使用，排除

---

## R-002：EAV 屬性值儲存策略 — 分欄 vs JSONB

**Decision**: **分欄儲存**（`value_string TEXT`, `value_integer INTEGER`, `value_boolean BOOLEAN`）+ ENUM 允許值使用 `allowed_values JSONB`。

**Rationale**:
- 分欄儲存讓 PostgreSQL 可在資料庫層施加型別約束（INTEGER 欄不接受非數字值）
- 應用層 Pydantic v2 + DB 層 CHECK constraint 雙重驗證，滿足 FR-011/FR-012 的驗證要求
- ENUM 允許值使用 JSONB 陣列（`["QM","A","B","C","D"]`）避免額外的 junction table，且長度不固定
- 查詢效能：分欄可在特定型別欄位建立部分索引（如 `CREATE INDEX ... WHERE value_boolean IS NOT NULL`）

**Schema Design**:
```sql
CREATE TABLE document_attribute_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    attribute_id UUID NOT NULL REFERENCES attribute_definitions(id),
    value_string TEXT,
    value_integer INTEGER,
    value_boolean BOOLEAN,
    UNIQUE(document_id, attribute_id),
    -- 確保只有一個值欄位被填入
    CONSTRAINT chk_single_value CHECK (
        (value_string IS NOT NULL)::int +
        (value_integer IS NOT NULL)::int +
        (value_boolean IS NOT NULL)::int <= 1
    )
);
```

**Alternatives Considered**:
- 全 JSONB 單欄（`value JSONB`）：彈性最高但失去 DB 型別約束，驗證完全依賴應用層，排除
- PostgreSQL hstore：不支援巢狀結構與型別區分，功能不足，排除
- 獨立型別表（StringValue, IntegerValue...）：過度複雜，查詢需 UNION，排除

---

## R-003：JWT 安全模式 — Access Token + Refresh Token 策略

**Decision**: Access Token（短效，15 分鐘）+ Refresh Token（長效，7 天）；Refresh Token 以不透明字串（UUID）儲存於 DB，每次 refresh 執行 rotation（舊 token 立即失效）。

**Rationale**:
- Spec FR-021 明確要求支援 `POST /auth/refresh`
- HS256 對稱密鑰（Spec A-02）；密鑰由 `SECRET_KEY` 環境變數注入
- JWT Payload 包含 `user_id`, `role`, `partition_access`, `exp`（FR-019）
- Refresh Token rotation 防止 token 竊取後長期有效的安全風險
- 本期 Spec 不含 Token 黑名單（Access Token 過期即失效，Refresh Token rotation 已足夠）

**JWT Payload Structure**:
```json
{
  "sub": "user_id (UUID)",
  "role": "PM | RD | QA | Admin",
  "partition_access": ["uuid-1", "uuid-2"],
  "exp": 1234567890,
  "iat": 1234567890,
  "type": "access"
}
```

**Refresh Token DB Schema**:
```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA-256 of raw token
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Alternatives Considered**:
- 全 Stateless（Refresh Token 也用 JWT）：Refresh Token 無法撤銷（logout 場景），排除
- 外部 OAuth2 Provider：Spec A-02 明確排除，留後續版本
- RS256 非對稱密鑰：適合多服務驗證場景，本期單體服務不需要，HS256 已足夠，排除

---

## R-004：樂觀鎖實作 — 並發寫入衝突控制

**Decision**: 在 `documents` 表新增 `version_lock INTEGER NOT NULL DEFAULT 1`，每次更新時遞增並在 WHERE 子句比對。請求 body 帶入 `current_version_lock`，不匹配時回傳 `409 Conflict`。

**Rationale**:
- Spec Edge Cases 明確要求：並發寫入時回傳 `409 Conflict` 並提示當前版本號
- 樂觀鎖不阻塞讀取，適合低衝突頻率的文件編輯場景
- SQLAlchemy 2.0 原生支援 `version_id_col` 樂觀鎖機制

**SQLAlchemy Optimistic Lock Pattern**:
```python
class Document(Base):
    __tablename__ = "documents"
    # ...
    version_lock: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version_lock}
    # SQLAlchemy 自動在 UPDATE 時比對並遞增 version_lock
    # 若不匹配，拋出 StaleDataError → 轉換為 HTTP 409
```

**Alternatives Considered**:
- 悲觀鎖（`SELECT ... FOR UPDATE`）：阻塞讀取，不適合文件系統場景，排除
- ETag Header 機制：需額外的 header 管理，不如 version_lock 直覺，排除
- PostgreSQL Advisory Lock：功能過重，適合長事務，排除

---

## R-005：Alembic Async Migration 整合模式

**Decision**: 使用 Alembic `run_sync` 模式搭配 async engine，在 `env.py` 中以 `asyncio.run()` 執行 migration。

**Rationale**:
- SQLAlchemy 2.0 async engine 不直接支援同步 migration，需透過 `run_sync` 橋接
- 使用 `Base.metadata` 作為 `target_metadata`，確保 autogenerate 可正確偵測 schema diff

**Alembic env.py Pattern**:
```python
# migrations/env.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

def run_migrations_online():
    connectable = create_async_engine(settings.DATABASE_URL)
    
    async def run_async_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    
    asyncio.run(run_async_migrations())
```

**Alternatives Considered**:
- Sync engine 僅用於 migration：需維護兩個 engine，設定複雜，排除
- 手動 SQL migration：失去 autogenerate 能力，維護成本高，排除

---

## R-006：文件版本號語意 — 版本遞增規則

**Decision**: 版本號格式為 `{major}.{minor}` 字串（如 `"1.0"`, `"1.1"`, `"2.0"`）。

- **初始版本**：`1.0`（文件建立時）
- **內容更新（DRAFT/REVIEW 狀態）**：minor 遞增（`1.0` → `1.1` → `1.2`）
- **APPROVED 後 Version Fork**：major 遞增（`1.x` → `2.0`）原 APPROVED 版本保留
- `document_versions` 表記錄每次快照，`documents` 表的 `version` 欄位記錄當前版本

**Rationale**:
- ASPICE 語意版本習慣：major 代表重大審核通過，minor 代表草稿迭代
- Spec FR-009 要求：APPROVED 後的修改需建立新版本，不覆蓋原版本

**Alternatives Considered**:
- SemVer（major.minor.patch）：過於複雜，ASPICE 不需要 patch 層級，排除
- 整數自增版本號：不符合 ASPICE 文件管理習慣，排除
- Git commit SHA：需 Git 整合（Spec A-04 明確排除），排除

---

## R-007：RBAC 授權中介層設計

**Decision**: 實作 FastAPI dependency 函式（`require_role(*roles)`, `require_partition_access(partition_id)`），在路由層宣告式注入。

**Rationale**:
- FastAPI dependency injection 機制天然適合中介層邏輯，不污染業務邏輯
- `Depends(get_current_user)` 解碼 JWT → `CurrentUser` dataclass
- `Depends(require_role("Admin", "PM"))` 檢查角色
- `partition_access` 驗證在 CRUD 層（`document_service.py`）根據資源的 `partition_id` 比對

**RBAC Matrix**:

| 操作 | PM | RD | QA | Admin |
|------|----|----|----|----|
| 建立文件 | 所在 Partition | 所在 Partition | ✗ | 全部 |
| 讀取文件 | 所在 Partition | 所在 Partition | 所在 Partition | 全部 |
| 更新文件 | 僅 Owner | 僅 Owner | ✗ | 全部 |
| 刪除文件 | ✗ | ✗ | ✗ | 全部 |
| DRAFT→REVIEW | 僅 Owner | 僅 Owner | ✗ | 全部 |
| REVIEW→APPROVED | ✗ | ✗ | ✅ | 全部 |
| 建立 Project/Partition | ✗ | ✗ | ✗ | ✅ |
| 建立 AttributeDefinition | ✗ | ✗ | ✗ | ✅ |

**Alternatives Considered**:
- Middleware-based RBAC（全域）：粒度不足，無法處理 Partition-level 存取控制，排除
- 資料庫層 Row-Level Security（PostgreSQL RLS）：維護複雜度高，與 SQLAlchemy ORM 整合麻煩，排除

---

## R-008：錯誤回應格式標準化

**Decision**: 統一錯誤回應格式，透過 FastAPI `exception_handler` 攔截並轉換。

**Standard Error Response**:
```json
{
  "detail": "人類可讀的錯誤說明",
  "code": "機器可讀的錯誤代碼"
}
```

**Error Code Registry**:
| HTTP Status | code | 場景 |
|-------------|------|------|
| 401 | `AUTH_MISSING_TOKEN` | 缺少 Authorization header |
| 401 | `AUTH_TOKEN_EXPIRED` | JWT 已過期 |
| 401 | `AUTH_INVALID_TOKEN` | JWT 格式或簽名無效 |
| 403 | `PERMISSION_DENIED` | 角色不足 |
| 403 | `PARTITION_ACCESS_DENIED` | 無 Partition 存取權 |
| 404 | `RESOURCE_NOT_FOUND` | 資源不存在 |
| 409 | `VERSION_CONFLICT` | 樂觀鎖版本衝突 |
| 409 | `STATUS_TRANSITION_INVALID` | 非法狀態轉換 → 改用 422 |
| 409 | `DOCUMENT_HAS_DEPENDENCIES` | 文件有追溯連結，無法刪除 |
| 409 | `PROJECT_NOT_EMPTY` | Project 有文件，無法刪除 |
| 413 | `CONTENT_TOO_LARGE` | content_md 超過 5MB |
| 422 | `VALIDATION_ERROR` | 請求體驗證失敗（Pydantic） |
| 422 | `INVALID_STATUS_TRANSITION` | 狀態轉換路徑非法 |
| 422 | `REQUIRED_ATTRIBUTE_MISSING` | 必填 EAV 屬性未提供 |
| 422 | `INVALID_ATTRIBUTE_VALUE` | EAV 屬性值不合法（型別/ENUM） |
| 422 | `PARTITION_PROJECT_MISMATCH` | partition_id 不屬於 project_id |

---

## R-009：測試策略

**Decision**: 三層測試（Unit + Integration + Contract），使用獨立 Test Database。

**Unit Tests**（不需 DB）:
- `test_security.py`：JWT 簽發/驗證、password hashing
- `test_document_service.py`：狀態機 transition 邏輯、版本號遞增、樂觀鎖
- `test_attribute_service.py`：EAV 型別驗證、ENUM 值驗證、必填屬性檢查

**Integration Tests**（需 Test DB）:
- 使用 `pytest-asyncio` + `httpx.AsyncClient`
- 每個 test function 使用 transaction rollback（`async with session.begin_nested()`）確保隔離
- Fixtures：`test_db`（建立測試 DB + 執行 migration）、`async_client`、`seed_data`（預設 Standard/AttributeDefinition/User）

**Contract Tests**:
- 驗證 `/openapi.json` schema 中所有端點的 response model 符合合約規範
- 確保 breaking change 被及早發現

**Coverage Goal**: ≥ 85%（SC-007），使用 `pytest-cov` 量測，CI pipeline 中設定門檻。

---

## 研究結論摘要

| 項目 | 決策 | 信心度 |
|------|------|--------|
| ORM | SQLAlchemy 2.0 async | 高 |
| EAV 儲存 | 分欄 + JSONB allowed_values | 高 |
| JWT | python-jose HS256 + Refresh Token rotation | 高 |
| 樂觀鎖 | SQLAlchemy `version_id_col` | 高 |
| Migration | Alembic async run_sync | 高 |
| 版本號 | `major.minor` 字串 | 高 |
| RBAC | FastAPI dependency injection | 高 |
| 錯誤格式 | `{detail, code}` + exception_handler | 高 |
| 測試策略 | 三層 + 獨立 Test DB + rollback isolation | 高 |

**所有決策均已明確，無待解決的 NEEDS CLARIFICATION 項目。**
