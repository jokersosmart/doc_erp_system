# API Contract: Documents

**Base Path**: `/api/v1/documents`  
**Auth Required**: ✅ Bearer JWT  
**Spec FR**: FR-001 ~ FR-015

---

## POST `/documents` — 建立文件
> FR-001, FR-002 | 角色：PM/RD/Admin（限所在 Partition）

**Request**:
```http
POST /api/v1/documents
Authorization: Bearer <token>
Content-Type: application/json

{
  "project_id": "uuid",
  "partition_id": "uuid",
  "title": "Software Architecture Specification",
  "content_md": "# Overview\n\nThis document describes...",
  "attributes": [
    { "attribute_id": "uuid-of-ASIL_Level", "value": "ASIL B" },
    { "attribute_id": "uuid-of-Document_Type", "value": "Spec" },
    { "attribute_id": "uuid-of-Document_Owner", "value": "john.doe" }
  ]
}
```

**Success Response `201 Created`**:
```json
{
  "id": "doc-uuid",
  "project_id": "uuid",
  "partition_id": "uuid",
  "title": "Software Architecture Specification",
  "content_md": "# Overview\n\nThis document describes...",
  "version": "1.0",
  "version_lock": 1,
  "status": "DRAFT",
  "owner_id": "user-uuid",
  "created_at": "2025-04-30T10:00:00Z",
  "updated_at": "2025-04-30T10:00:00Z",
  "attributes": [
    { "attribute_id": "uuid-of-ASIL_Level", "name": "ASIL_Level", "value": "ASIL B", "data_type": "ENUM" },
    { "attribute_id": "uuid-of-Document_Type", "name": "Document_Type", "value": "Spec", "data_type": "ENUM" },
    { "attribute_id": "uuid-of-Document_Owner", "name": "Document_Owner", "value": "john.doe", "data_type": "STRING" }
  ]
}
```

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 401 | `AUTH_MISSING_TOKEN` | 未攜帶 JWT |
| 403 | `PARTITION_ACCESS_DENIED` | JWT 無此 partition 存取權 |
| 413 | `CONTENT_TOO_LARGE` | content_md > 5MB |
| 422 | `VALIDATION_ERROR` | 必填欄位缺失/格式錯誤 |
| 422 | `PARTITION_PROJECT_MISMATCH` | partition_id 不屬於 project_id |
| 422 | `REQUIRED_ATTRIBUTE_MISSING` | 必填屬性（is_required=true）未提供 |
| 422 | `INVALID_ATTRIBUTE_VALUE` | 屬性值型別或 ENUM 值不合法 |

---

## GET `/documents` — 列出文件（含篩選與分頁）
> FR-006 | 角色：All（Partition 限制）

**Request**:
```http
GET /api/v1/documents?project_id={uuid}&partition_id={uuid}&status=APPROVED&owner_id={uuid}&page=1&page_size=10
Authorization: Bearer <token>
```

**Query Parameters**:
| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `project_id` | UUID | ❌ | 篩選特定專案 |
| `partition_id` | UUID | ❌ | 篩選特定 Partition |
| `status` | string | ❌ | DRAFT/REVIEW/APPROVED/OBSOLETE |
| `owner_id` | UUID | ❌ | 篩選特定 Owner |
| `page` | int | ❌ | 頁碼，預設 1 |
| `page_size` | int | ❌ | 每頁筆數，預設 20，最大 100 |

**Success Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "doc-uuid",
      "title": "Software Architecture Specification",
      "version": "1.0",
      "status": "APPROVED",
      "owner_id": "user-uuid",
      "updated_at": "2025-04-30T10:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 10,
  "has_next": true,
  "has_prev": false
}
```

> **Note**: 回應中的 `items` 為 `DocumentListItem`（不含 `content_md` 和 `attributes`），節省傳輸量。

---

## GET `/documents/{id}` — 取得文件詳情
> FR-003 | 角色：All（Partition 限制）

**Request**:
```http
GET /api/v1/documents/{id}
Authorization: Bearer <token>
```

**Success Response `200 OK`**: 同 POST 成功回應格式（含 `content_md` 和 `attributes`）

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 401 | `AUTH_MISSING_TOKEN` / `AUTH_TOKEN_EXPIRED` | JWT 問題 |
| 403 | `PARTITION_ACCESS_DENIED` | 無 Partition 存取權（不洩露文件是否存在） |
| 404 | `RESOURCE_NOT_FOUND` | UUID 正確但資源不存在 |
| 422 | `VALIDATION_ERROR` | id 不是合法 UUID 格式 |

> **Security**: 無 Partition 存取權時回傳 `403`（不是 `404`），防止資訊洩露（FR User Story 1 AC-4）。

---

## PUT `/documents/{id}` — 更新文件內容
> FR-004, FR-009 | 角色：Owner/Admin（DRAFT/REVIEW 狀態）

**Request**:
```http
PUT /api/v1/documents/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "content_md": "# Overview\n\nRevised content...",
  "attributes": [
    { "attribute_id": "uuid-of-ASIL_Level", "value": "ASIL C" }
  ],
  "commit_message": "Updated ASIL level based on safety analysis review",
  "current_version_lock": 1
}
```

**Success Response `200 OK`**: 完整 DocumentRead（version 已遞增，version_lock 已更新）

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 403 | `PERMISSION_DENIED` | 非 Owner 且非 Admin |
| 403 | `PARTITION_ACCESS_DENIED` | 無 Partition 存取權 |
| 404 | `RESOURCE_NOT_FOUND` | 文件不存在 |
| 409 | `VERSION_CONFLICT` | `current_version_lock` 不符當前值（樂觀鎖） |
| 409 | `DOCUMENT_APPROVED` | 文件已為 APPROVED，需建立新版本 |
| 422 | `REQUIRED_ATTRIBUTE_MISSING` | 必填屬性未提供 |
| 422 | `INVALID_ATTRIBUTE_VALUE` | 屬性值不合法 |

> **APPROVED 文件處理**: 若 status 為 APPROVED，回傳 `409 DOCUMENT_APPROVED` 並提示「需建立新版本（Version Fork）以修改已核准文件」。Version Fork 機制（major 遞增）由前端發起確認後，以特定 query param `?fork=true` 觸發（或由獨立端點處理）。

---

## DELETE `/documents/{id}` — 刪除文件
> FR-005 | 角色：Admin

**Request**:
```http
DELETE /api/v1/documents/{id}
Authorization: Bearer <token>
```

**Success Response `204 No Content`**: (empty body)

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 403 | `PERMISSION_DENIED` | 非 Admin |
| 404 | `RESOURCE_NOT_FOUND` | 文件不存在 |
| 409 | `DOCUMENT_HAS_DEPENDENCIES` | 文件有追溯連結（`traceability_links` 中有記錄） |

---

## PATCH `/documents/{id}/status` — 狀態轉換
> FR-007, FR-008 | 角色視目標狀態而定

**Request**:
```http
PATCH /api/v1/documents/{id}/status
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "REVIEW"
}
```

**角色授權矩陣**:
| 目標狀態 | 允許角色 |
|----------|----------|
| REVIEW | Owner（PM/RD）、Admin |
| APPROVED | QA、Admin |
| OBSOLETE | Admin |
| DRAFT（退回）| Owner（PM/RD）、Admin（從 REVIEW 退回） |

**Success Response `200 OK`**:
```json
{
  "id": "doc-uuid",
  "status": "REVIEW",
  "version": "1.0",
  "updated_at": "2025-04-30T11:00:00Z",
  "audit_log_id": "audit-log-uuid"
}
```

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 403 | `PERMISSION_DENIED` | 角色無法執行此轉換 |
| 404 | `RESOURCE_NOT_FOUND` | 文件不存在 |
| 422 | `INVALID_STATUS_TRANSITION` | 非法狀態路徑（如 APPROVED → DRAFT） |

---

## GET `/documents/{id}/versions` — 版本歷程列表
> FR-013 | 角色：All（Partition 限制）

**Request**:
```http
GET /api/v1/documents/{id}/versions
Authorization: Bearer <token>
```

**Success Response `200 OK`**:
```json
{
  "document_id": "doc-uuid",
  "current_version": "1.2",
  "versions": [
    {
      "id": "version-uuid",
      "version": "1.2",
      "modified_by": "user-uuid",
      "commit_message": "Updated ASIL level",
      "created_at": "2025-04-30T11:00:00Z"
    },
    {
      "id": "version-uuid-2",
      "version": "1.1",
      "modified_by": "user-uuid",
      "commit_message": "Initial draft revision",
      "created_at": "2025-04-30T10:30:00Z"
    },
    {
      "id": "version-uuid-3",
      "version": "1.0",
      "modified_by": "user-uuid",
      "commit_message": "Document created",
      "created_at": "2025-04-30T10:00:00Z"
    }
  ]
}
```

---

## GET `/documents/{id}/versions/{version}` — 版本快照
> FR-014 | 角色：All（Partition 限制）

**Request**:
```http
GET /api/v1/documents/{id}/versions/1.1
Authorization: Bearer <token>
```

**Success Response `200 OK`**:
```json
{
  "id": "version-uuid",
  "document_id": "doc-uuid",
  "version": "1.1",
  "content_md": "# Overview\n\nThis is version 1.1 content...",
  "modified_by": "user-uuid",
  "commit_message": "Initial draft revision",
  "created_at": "2025-04-30T10:30:00Z"
}
```

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 404 | `RESOURCE_NOT_FOUND` | 文件或版本號不存在 |
