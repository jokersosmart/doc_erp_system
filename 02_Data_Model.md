# 車用標準文件 ERP 系統 - 資料模型 (Data Model)

## 1. 核心實體關聯 (Entity-Relationship)

本系統採用 Entity-Attribute-Value (EAV) 模型，以支援動態擴展的 ISO 標準屬性。

### 1.1 核心實體 (Entities)

| 實體名稱 | 描述 | 關聯實體 |
|---|---|---|
| **Project** | 專案實體，代表一個完整的開發專案 | 包含多個 Document |
| **Document** | 文件實體，代表一份規格或設計文件 | 屬於 Project，關聯多個 Attribute |
| **Partition** | 組織層級劃分，如 SYS, SWE, HW | 包含多個 Document |
| **Standard** | 參考標準，如 ASPICE 3.1, ISO-26262 | 關聯多個 Requirement |
| **Requirement** | 標準條文要求 | 關聯多個 Document |
| **Traceability** | 追溯關係，記錄文件間的相依性 | 關聯 Source Document 與 Target Document |

### 1.2 屬性實體 (Attributes)

| 實體名稱 | 描述 | 關聯實體 |
|---|---|---|
| **Attribute_Definition** | 屬性定義，如 ASIL Level, Unique ID | 屬於 Standard 或 Partition |
| **Document_Attribute_Value** | 文件屬性值，記錄具體文件的屬性內容 | 關聯 Document 與 Attribute_Definition |

## 2. 資料庫 Schema 設計 (PostgreSQL)

### 2.1 專案與文件表

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE partitions (
    id UUID PRIMARY KEY,
    name VARCHAR(50) NOT NULL, -- e.g., 'SYS', 'SWE', 'HW'
    description TEXT
);

CREATE TABLE documents (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    partition_id UUID REFERENCES partitions(id),
    title VARCHAR(255) NOT NULL,
    content_md TEXT, -- Markdown 內容
    version VARCHAR(20) DEFAULT '1.0',
    status VARCHAR(50) DEFAULT 'DRAFT', -- DRAFT, REVIEW, APPROVED
    owner_id UUID, -- 關聯使用者表
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 EAV 動態屬性表

```sql
CREATE TABLE attribute_definitions (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL, -- e.g., 'ASIL_Level', 'Safety_Goal_ID'
    data_type VARCHAR(50) NOT NULL, -- STRING, INTEGER, BOOLEAN, ENUM
    standard_id UUID, -- 關聯標準表 (若為特定標準專屬屬性)
    is_required BOOLEAN DEFAULT FALSE
);

CREATE TABLE document_attribute_values (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    attribute_id UUID REFERENCES attribute_definitions(id),
    value_string TEXT,
    value_integer INTEGER,
    value_boolean BOOLEAN,
    UNIQUE(document_id, attribute_id)
);
```

### 2.3 相依性與追溯表

```sql
CREATE TABLE traceability_links (
    id UUID PRIMARY KEY,
    source_document_id UUID REFERENCES documents(id),
    target_document_id UUID REFERENCES documents(id),
    link_type VARCHAR(50) NOT NULL, -- e.g., 'SATISFIES', 'VERIFIES', 'IMPLEMENTS'
    status VARCHAR(50) DEFAULT 'VALID', -- VALID, SUSPECT (當 source 變更時標記為 SUSPECT)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.4 標準與條文表

```sql
CREATE TABLE standards (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL, -- e.g., 'ASPICE 3.1', 'ISO-26262'
    version VARCHAR(50)
);

CREATE TABLE standard_requirements (
    id UUID PRIMARY KEY,
    standard_id UUID REFERENCES standards(id),
    clause_id VARCHAR(50) NOT NULL, -- e.g., 'SYS.1.BP1'
    description TEXT NOT NULL
);

CREATE TABLE document_compliance (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    requirement_id UUID REFERENCES standard_requirements(id),
    status VARCHAR(50) DEFAULT 'PENDING', -- COMPLIANT, NON_COMPLIANT, PENDING
    ai_suggestion TEXT
);
```

## 3. 資料流與狀態轉換

### 3.1 文件狀態機 (Document State Machine)
1. **DRAFT (草稿)**：文件建立初期，AI 協助草擬內容。
2. **REVIEW (審查中)**：內容完成，提交給相關 Owner 審查。
3. **APPROVED (已核准)**：審查通過，鎖定版本。
4. **OBSOLETE (已作廢)**：文件被新版本取代。

### 3.2 追溯狀態機 (Traceability State Machine)
1. **VALID (有效)**：上下游文件內容一致，符合相依性。
2. **SUSPECT (可疑)**：當 Source Document 發生變更 (DRAFT -> APPROVED) 時，所有關聯的 Target Document 的 Traceability Link 自動標記為 SUSPECT，觸發 AI 重新評估並發送通知。

---
*Author: Joker*
