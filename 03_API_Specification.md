# 車用標準文件 ERP 系統 - API 規格 (API Specification)

## 1. 核心 API 設計原則

本系統採用 RESTful 架構，並以 JSON 格式進行資料交換。所有 API 請求皆需攜帶 JWT (JSON Web Token) 進行身份驗證與授權。

### 1.1 基礎 URL
`https://api.doc-erp.example.com/v1`

### 1.2 認證方式
- **Header**: `Authorization: Bearer <token>`
- **Token 類型**: JWT (包含 User ID, Role, Partition Access)

## 2. 文件管理 API (Document Management)

### 2.1 建立新文件
- **Endpoint**: `POST /documents`
- **Description**: 建立一份新的規格或設計文件。
- **Request Body**:
  ```json
  {
    "project_id": "uuid",
    "partition_id": "uuid",
    "title": "System Requirements Specification",
    "content_md": "# SRS Content...",
    "attributes": [
      { "attribute_id": "uuid", "value": "ASIL B" }
    ]
  }
  ```
- **Response**: `201 Created` (回傳 Document ID)

### 2.2 取得文件詳情
- **Endpoint**: `GET /documents/{id}`
- **Description**: 取得文件內容及其所有動態屬性。
- **Response**: `200 OK` (包含 Markdown 內容與屬性列表)

### 2.3 更新文件內容
- **Endpoint**: `PUT /documents/{id}`
- **Description**: 更新文件內容，並觸發相依性檢查。
- **Request Body**:
  ```json
  {
    "content_md": "# Updated SRS Content...",
    "commit_message": "Updated safety goals"
  }
  ```
- **Response**: `200 OK` (回傳更新後版本號)

## 3. 相依性追蹤 API (Traceability)

### 3.1 建立追溯連結
- **Endpoint**: `POST /traceability`
- **Description**: 建立兩份文件之間的相依性連結。
- **Request Body**:
  ```json
  {
    "source_document_id": "uuid",
    "target_document_id": "uuid",
    "link_type": "SATISFIES"
  }
  ```
- **Response**: `201 Created`

### 3.2 取得受影響文件 (Impact Analysis)
- **Endpoint**: `GET /documents/{id}/impacts`
- **Description**: 當指定文件變更時，取得所有受影響的下游文件列表。
- **Response**: `200 OK`
  ```json
  {
    "impacted_documents": [
      { "id": "uuid", "title": "Software Architecture", "status": "SUSPECT" }
    ]
  }
  ```

## 4. AI 規格檢查與建議 API (AI Advisor)

### 4.1 請求 AI 審查
- **Endpoint**: `POST /ai/review/{document_id}`
- **Description**: 請求 AI Agent 審查文件是否符合 ASPICE/ISO 標準。
- **Request Body**:
  ```json
  {
    "standards": ["ASPICE 3.1", "ISO-26262"]
  }
  ```
- **Response**: `202 Accepted` (非同步處理，回傳 Job ID)

### 4.2 取得 AI 建議 (Cursor-like Diff)
- **Endpoint**: `GET /ai/suggestions/{document_id}`
- **Description**: 取得 AI 針對文件變更所生成的修改建議 (Diff 格式)。
- **Response**: `200 OK`
  ```json
  {
    "suggestions": [
      {
        "original_text": "The system shall monitor speed.",
        "suggested_text": "The system shall monitor vehicle speed with an accuracy of +/- 1 km/h (ASIL B).",
        "reason": "Missing quantitative requirement and ASIL allocation per ISO-26262 Part 3."
      }
    ]
  }
  ```

## 5. Codebeamer 整合 API (Codebeamer Sync)

### 5.1 匯出至 Codebeamer
- **Endpoint**: `POST /integrations/codebeamer/export`
- **Description**: 將指定專案的文件結構化匯出，並同步至 Codebeamer Tracker。
- **Request Body**:
  ```json
  {
    "project_id": "uuid",
    "target_tracker_id": "12345",
    "mapping_profile": "ASPICE_SYS_REQ"
  }
  ```
- **Response**: `202 Accepted` (非同步處理，回傳 Sync Job ID)

---
*Author: Joker*
