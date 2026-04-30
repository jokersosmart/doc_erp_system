# Data Model: 文件管理後端 API

**Feature**: `doc-management-backend`  
**Date**: 2025-04-30  
**Database**: PostgreSQL 15+  
**ORM**: SQLAlchemy 2.0 (async)  
**Migration**: Alembic

> 所有實體均可追溯至 spec.md 的 FR 編號與 Key Entities 定義。

---

## 1. Entity-Relationship Overview

```
Standard (1) ──────────── (N) AttributeDefinition
                                      │
                                      │ (N)
Project (1) ────── (N) Document ──── DocumentAttributeValue
    │                    │
    │                    │──── (N) DocumentVersion
    │                    │
    │                    │──── (N) AuditLog
    │                    │
    │              (source/target)
    │                    │
    │              TraceabilityLink (stub)
    │
    └──── (N) Partition
               └──── (N) Document
```

---

## 2. Database Schema

### 2.1 `projects` 表
> 對應實體：Project（FR-016）

```sql
CREATE TABLE projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_projects_name ON projects(name);
```

**欄位說明**:
| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | 憲法原則 1：UUID 主鍵 |
| `name` | VARCHAR(255) | NOT NULL | 專案名稱 |
| `description` | TEXT | nullable | 專案描述 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 建立時間 |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 最後更新時間 |

---

### 2.2 `partitions` 表
> 對應實體：Partition（FR-017）

```sql
CREATE TABLE partitions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(50) NOT NULL UNIQUE,   -- 'SYS', 'SWE', 'HW', 'Safety', 'Security'
    description TEXT,
    project_id  UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_partitions_project_id ON partitions(project_id);
```

**欄位說明**:
| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| `id` | UUID | PK | |
| `name` | VARCHAR(50) | NOT NULL, UNIQUE per project | 縮寫（SYS/SWE/HW/Safety/Security） |
| `description` | TEXT | nullable | |
| `project_id` | UUID | FK → projects.id, RESTRICT | Partition 歸屬專案 |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

> **Seed Data**: `('SYS', 'System'), ('SWE', 'Software'), ('HW', 'Hardware'), ('Safety', 'Functional Safety'), ('Security', 'Cybersecurity')`

---

### 2.3 `documents` 表
> 對應實體：Document（FR-001~FR-009, FR-013~FR-015）

```sql
CREATE TABLE documents (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id     UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    partition_id   UUID NOT NULL REFERENCES partitions(id) ON DELETE RESTRICT,
    title          VARCHAR(255) NOT NULL,
    content_md     TEXT NOT NULL,              -- Markdown 全文，上限 5MB 在應用層控制
    version        VARCHAR(20) NOT NULL DEFAULT '1.0',   -- 'major.minor' 格式
    version_lock   INTEGER NOT NULL DEFAULT 1,            -- 樂觀鎖（SQLAlchemy version_id_col）
    status         VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
                       CHECK (status IN ('DRAFT','REVIEW','APPROVED','OBSOLETE')),
    owner_id       UUID NOT NULL,              -- JWT user_id，不建 FK（無 users 表）
    created_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    -- 確保 partition 屬於同一個 project（應用層也驗證，FR Edge Case）
    CONSTRAINT chk_content_not_empty CHECK (trim(content_md) != '')
);

CREATE INDEX idx_documents_project_id ON documents(project_id);
CREATE INDEX idx_documents_partition_id ON documents(partition_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_owner_id ON documents(owner_id);
CREATE INDEX idx_documents_updated_at ON documents(updated_at DESC);
```

**欄位說明**:
| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| `id` | UUID | PK | |
| `project_id` | UUID | FK → projects.id, RESTRICT | |
| `partition_id` | UUID | FK → partitions.id, RESTRICT | |
| `title` | VARCHAR(255) | NOT NULL | |
| `content_md` | TEXT | NOT NULL, not empty | Markdown 正文 |
| `version` | VARCHAR(20) | NOT NULL, DEFAULT '1.0' | `major.minor` 格式 |
| `version_lock` | INTEGER | NOT NULL, DEFAULT 1 | 樂觀鎖版本號（不是文件語意版本） |
| `status` | VARCHAR(20) | CHECK (DRAFT/REVIEW/APPROVED/OBSOLETE) | 狀態機 |
| `owner_id` | UUID | NOT NULL | JWT 中的 user_id |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | 每次更新自動刷新 |

**狀態機轉換規則**（FR-007）:
```
DRAFT ──→ REVIEW ──→ APPROVED ──→ OBSOLETE
              ↑_____________|（非法）
任何其他路徑均回傳 422 INVALID_STATUS_TRANSITION
```

---

### 2.4 `document_versions` 表
> 對應實體：DocumentVersion（FR-013~FR-015）

```sql
CREATE TABLE document_versions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id    UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version        VARCHAR(20) NOT NULL,       -- 對應 documents.version 的快照
    content_md     TEXT NOT NULL,              -- 版本快照，永久保存
    modified_by    UUID NOT NULL,              -- JWT user_id
    commit_message VARCHAR(500) NOT NULL,
    created_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_doc_versions_document_id ON document_versions(document_id);
CREATE INDEX idx_doc_versions_created_at ON document_versions(document_id, created_at DESC);
```

**欄位說明**:
| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| `id` | UUID | PK | |
| `document_id` | UUID | FK → documents.id, CASCADE | |
| `version` | VARCHAR(20) | NOT NULL | 此快照對應的版本號 |
| `content_md` | TEXT | NOT NULL | 完整 Markdown 內容快照（永久保存，FR-015） |
| `modified_by` | UUID | NOT NULL | 操作者 user_id |
| `commit_message` | VARCHAR(500) | NOT NULL | 變更說明（FR-004 要求必填） |
| `created_at` | TIMESTAMPTZ | NOT NULL | 快照建立時間 |

> **Note**: 版本快照在每次 `PUT /documents/{id}` 成功後自動寫入，不可修改（immutable）。

---

### 2.5 `standards` 表
> 對應實體：Standard（FR-010, Assumptions A-12）

```sql
CREATE TABLE standards (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(100) NOT NULL UNIQUE,   -- 'ASPICE 3.1', 'ISO-26262', 'ISO-21434'
    version    VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

> **Seed Data**: `('ASPICE 3.1', '3.1'), ('ISO-26262', '2018'), ('ISO-21434', '2021')`

---

### 2.6 `attribute_definitions` 表
> 對應實體：AttributeDefinition（FR-010~FR-012）

```sql
CREATE TABLE attribute_definitions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name           VARCHAR(100) NOT NULL,
    data_type      VARCHAR(20) NOT NULL
                       CHECK (data_type IN ('STRING','INTEGER','BOOLEAN','ENUM')),
    allowed_values JSONB,                      -- ENUM 時必填，格式: ["QM","A","B","C","D"]
    is_required    BOOLEAN NOT NULL DEFAULT FALSE,
    standard_id    UUID REFERENCES standards(id) ON DELETE SET NULL,
    created_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_enum_has_values CHECK (
        data_type != 'ENUM' OR (allowed_values IS NOT NULL AND jsonb_array_length(allowed_values) > 0)
    ),
    CONSTRAINT chk_name_unique_per_standard UNIQUE (name, standard_id)
);

CREATE INDEX idx_attr_def_standard_id ON attribute_definitions(standard_id);
CREATE INDEX idx_attr_def_is_required ON attribute_definitions(is_required) WHERE is_required = TRUE;
```

**欄位說明**:
| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| `id` | UUID | PK | |
| `name` | VARCHAR(100) | NOT NULL | 屬性名稱（如 `ASIL_Level`） |
| `data_type` | VARCHAR(20) | CHECK | STRING / INTEGER / BOOLEAN / ENUM |
| `allowed_values` | JSONB | nullable, ENUM 時必填 | `["QM","A","B","C","D"]` |
| `is_required` | BOOLEAN | NOT NULL, DEFAULT FALSE | true 時文件必須提供此屬性值（FR-012） |
| `standard_id` | UUID | FK → standards.id, nullable | 歸屬標準（選填） |

> **Seed Data**（ASPICE 3.1 屬性範例）:  
> `ASIL_Level (ENUM: QM/A/B/C/D, is_required: false, standard: ISO-26262)`  
> `Document_Type (ENUM: Spec/Design/Test/Procedure, is_required: true, standard: ASPICE 3.1)`  
> `Document_Owner (STRING, is_required: true, standard: ASPICE 3.1)`  
> `Safety_Goal_ID (STRING, is_required: false, standard: ISO-26262)`

---

### 2.7 `document_attribute_values` 表
> 對應實體：DocumentAttributeValue（FR-011~FR-012）

```sql
CREATE TABLE document_attribute_values (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    attribute_id  UUID NOT NULL REFERENCES attribute_definitions(id) ON DELETE RESTRICT,
    value_string  TEXT,
    value_integer INTEGER,
    value_boolean BOOLEAN,
    created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(document_id, attribute_id),
    CONSTRAINT chk_single_value CHECK (
        (value_string IS NOT NULL)::int +
        (value_integer IS NOT NULL)::int +
        (value_boolean IS NOT NULL)::int <= 1
    )
);

CREATE INDEX idx_attr_values_document_id ON document_attribute_values(document_id);
```

**EAV 值欄位對應 data_type**:
| data_type | 使用欄位 | 驗證 |
|-----------|----------|------|
| STRING | `value_string` | 非空字串 |
| INTEGER | `value_integer` | 整數範圍 |
| BOOLEAN | `value_boolean` | true/false |
| ENUM | `value_string` | 值必須在 `allowed_values` 清單中（應用層驗證） |

---

### 2.8 `audit_logs` 表
> 對應實體：AuditLog（FR-008）

```sql
CREATE TABLE audit_logs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    operator_id   UUID NOT NULL,               -- JWT user_id
    action_type   VARCHAR(50) NOT NULL,        -- 'STATUS_TRANSITION', 'CONTENT_UPDATE', 'VERSION_FORK'
    old_status    VARCHAR(20),                 -- 狀態轉換前（nullable，非狀態操作時為 null）
    new_status    VARCHAR(20),                 -- 狀態轉換後
    metadata      JSONB,                       -- 附加資訊（如 commit_message, version）
    created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_document_id ON audit_logs(document_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(document_id, created_at DESC);
```

**action_type 值**:
| 值 | 觸發時機 |
|----|----------|
| `STATUS_TRANSITION` | `PATCH /documents/{id}/status` 成功時 |
| `CONTENT_UPDATE` | `PUT /documents/{id}` 成功時 |
| `VERSION_FORK` | APPROVED 文件建立新版本時 |
| `DOCUMENT_CREATED` | `POST /documents` 成功時 |

---

### 2.9 `traceability_links` 表（Schema Stub）
> 對應實體：TraceabilityLink（本期 Spec 範疇外，A-06）

```sql
-- Schema 結構預先建立，業務邏輯留後續 Spec
CREATE TABLE traceability_links (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    target_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    link_type          VARCHAR(50) NOT NULL,   -- 'SATISFIES', 'VERIFIES', 'IMPLEMENTS'
    status             VARCHAR(20) NOT NULL DEFAULT 'VALID'
                           CHECK (status IN ('VALID', 'SUSPECT')),
    created_by         UUID NOT NULL,
    created_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(source_document_id, target_document_id, link_type)
);

CREATE INDEX idx_trace_source ON traceability_links(source_document_id);
CREATE INDEX idx_trace_target ON traceability_links(target_document_id);
```

> **Purpose**: 預先建立 schema stub 以確保 `FR-005`（刪除有追溯連結的文件返回 409）可正確實作；完整業務邏輯由後續追溯追蹤 Spec 定義。

---

### 2.10 `refresh_tokens` 表
> 支援 FR-021（Token Refresh 機制）

```sql
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    token_hash  VARCHAR(64) NOT NULL UNIQUE,   -- SHA-256(raw_token)
    expires_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at  TIMESTAMP WITH TIME ZONE,      -- null = 有效
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
```

---

## 3. SQLAlchemy ORM Models

### 3.1 Base 設定

```python
# app/db/base.py
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

### 3.2 Document Model（核心範例）

```python
# app/models/document.py
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, UUID, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Document(Base):
    __tablename__ = "documents"
    __mapper_args__ = {"version_id_col": "version_lock"}  # 樂觀鎖

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    partition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("partitions.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    version_lock: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    attribute_values: Mapped[list["DocumentAttributeValue"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','REVIEW','APPROVED','OBSOLETE')", name="ck_documents_status"),
        CheckConstraint("trim(content_md) != ''", name="ck_documents_content_not_empty"),
    )
```

---

## 4. Pydantic v2 Schemas

### 4.1 Document Schemas

```python
# app/schemas/document.py
from uuid import UUID
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

DocumentStatus = Literal["DRAFT", "REVIEW", "APPROVED", "OBSOLETE"]

class DocumentAttributeValueInput(BaseModel):
    attribute_id: UUID
    value: str | int | bool  # 應用層根據 AttributeDefinition.data_type 驗證

class DocumentCreate(BaseModel):
    project_id: UUID
    partition_id: UUID
    title: str = Field(min_length=1, max_length=255)
    content_md: str = Field(min_length=1)
    attributes: list[DocumentAttributeValueInput] = []

    @field_validator("content_md")
    @classmethod
    def content_not_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content_md cannot be empty or whitespace only")
        if len(v.encode("utf-8")) > 5 * 1024 * 1024:  # 5MB
            raise ValueError("content_md exceeds 5MB limit")
        return v

class DocumentUpdate(BaseModel):
    content_md: str | None = Field(None, min_length=1)
    attributes: list[DocumentAttributeValueInput] | None = None
    commit_message: str = Field(min_length=1, max_length=500)
    current_version_lock: int = Field(ge=1)  # 樂觀鎖比對

class StatusTransitionRequest(BaseModel):
    status: DocumentStatus

class DocumentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    partition_id: UUID
    title: str
    content_md: str
    version: str
    version_lock: int
    status: DocumentStatus
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    attributes: list["AttributeValueRead"] = []

class VersionListItem(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    version: str
    modified_by: UUID
    commit_message: str
    created_at: datetime

class VersionRead(VersionListItem):
    content_md: str

class DocumentListItem(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    title: str
    version: str
    status: DocumentStatus
    owner_id: UUID
    updated_at: datetime
```

### 4.2 Auth Schemas

```python
# app/schemas/auth.py
from pydantic import BaseModel
from uuid import UUID
from typing import Literal

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenPayload(BaseModel):
    sub: UUID          # user_id
    role: Literal["PM", "RD", "QA", "Admin"]
    partition_access: list[UUID]
    exp: int
    iat: int
    type: Literal["access", "refresh"]
```

---

## 5. 版本號遞增演算法

```python
# app/services/document_service.py

def increment_version(current_version: str, is_fork: bool = False) -> str:
    """
    current_version: "major.minor" 格式
    is_fork: True 時（APPROVED 後建立新版本），major += 1, minor = 0
             False 時（一般更新），minor += 1
    """
    major, minor = current_version.split(".")
    if is_fork:
        return f"{int(major) + 1}.0"
    else:
        return f"{major}.{int(minor) + 1}"

# 狀態機合法轉換定義
VALID_TRANSITIONS = {
    "DRAFT": ["REVIEW"],
    "REVIEW": ["APPROVED", "DRAFT"],   # REVIEW 可退回 DRAFT（由 QA 決定）
    "APPROVED": ["OBSOLETE"],
    "OBSOLETE": [],                    # 終態
}

def validate_status_transition(current: str, target: str) -> None:
    if target not in VALID_TRANSITIONS.get(current, []):
        raise InvalidStatusTransitionError(
            f"Cannot transition from {current} to {target}. "
            f"Allowed: {VALID_TRANSITIONS.get(current, [])}"
        )
```

> **Note on REVIEW→DRAFT**: spec.md User Story 2 AC5 說明「非 Owner 或非主管角色無法推進」，但未明確禁止退回。保守設計允許 REVIEW→DRAFT 退回（需 Owner 或 Admin 角色），以支援審查退件場景。若需嚴格單向，可在後續 Spec 中明確。

---

## 6. 資料完整性規則

| 規則 | 實作層級 | 說明 |
|------|----------|------|
| `content_md` 非空 | DB CHECK + Pydantic | `trim(content_md) != ''` |
| `content_md` ≤ 5MB | Pydantic validator | 在序列化前檢查 byte 長度 |
| UUID 格式正確 | Pydantic（FastAPI 自動） | 路徑參數與 body UUID 自動驗證 |
| Partition 屬於 Project | Application layer | `document_service.create_document()` 中查詢驗證 |
| ENUM 屬性值合法 | Application layer | `attribute_service.validate_value()` 比對 `allowed_values` JSONB |
| 必填屬性 | Application layer | `attribute_service.check_required()` 查詢所有 `is_required=True` 屬性 |
| 樂觀鎖衝突 | SQLAlchemy (StaleDataError) | `version_id_col` 機制，轉換為 HTTP 409 |
| APPROVED 文件不可直接修改 | Application layer | `document_service.update_document()` 檢查 status |
| 非法狀態轉換 | Application layer | `validate_status_transition()` 函式 |
| 有追溯連結的文件不可刪除 | Application layer | 刪除前查詢 `traceability_links` |
| 有文件的 Project 不可刪除 | DB (RESTRICT) + Application | FK ON DELETE RESTRICT 兜底 |

---

## 7. 索引策略

| 索引 | 資料表 | 目的 |
|------|--------|------|
| `idx_documents_project_id` | documents | 按專案篩選文件（FR-006） |
| `idx_documents_partition_id` | documents | 按 Partition 篩選（FR-006） |
| `idx_documents_status` | documents | 按狀態篩選（FR-006） |
| `idx_documents_owner_id` | documents | 按 owner 篩選（FR-006） |
| `idx_documents_updated_at` | documents | 按更新時間排序（FR-006） |
| `idx_doc_versions_document_id` | document_versions | 查詢版本歷程（FR-013） |
| `idx_attr_values_document_id` | document_attribute_values | 讀取文件屬性（FR-003） |
| `idx_attr_def_is_required` | attribute_definitions | 查詢必填屬性（FR-012，partial index） |
| `idx_audit_logs_document_id` | audit_logs | 查詢稽核日誌（FR-008） |
| `idx_trace_source/target` | traceability_links | 刪除前檢查依賴（FR-005） |
