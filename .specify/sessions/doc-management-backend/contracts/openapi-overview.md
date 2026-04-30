# API Contracts Overview: 文件管理後端 API

**Feature**: `doc-management-backend`  
**Base URL**: `/api/v1`  
**Auth**: `Authorization: Bearer <JWT>` (除 `/auth/login`, `/health` 外，所有端點必填)  
**Date**: 2025-04-30

---

## API 端點總覽

| 方法 | 路徑 | 說明 | 角色要求 | Spec FR |
|------|------|------|----------|---------|
| POST | `/auth/login` | 登入，取得 JWT | Public | FR-021 |
| POST | `/auth/refresh` | 刷新 Access Token | Public (帶 refresh_token) | FR-021 |
| GET | `/health` | 服務健康檢查 | Public | FR-023 |
| POST | `/projects` | 建立專案 | Admin | FR-016 |
| GET | `/projects` | 列出所有專案 | All | FR-016 |
| GET | `/projects/{id}` | 取得專案詳情 | All | FR-016 |
| POST | `/partitions` | 建立 Partition | Admin | FR-017 |
| GET | `/partitions` | 列出 Partition | All | FR-017 |
| POST | `/documents` | 建立文件 | PM/RD/Admin（所在 Partition） | FR-001 |
| GET | `/documents` | 列出文件（含篩選分頁） | All（Partition 限制） | FR-006 |
| GET | `/documents/{id}` | 取得文件詳情 | All（Partition 限制） | FR-003 |
| PUT | `/documents/{id}` | 更新文件內容 | Owner/Admin | FR-004 |
| DELETE | `/documents/{id}` | 刪除文件 | Admin | FR-005 |
| PATCH | `/documents/{id}/status` | 狀態轉換 | 角色視目標狀態而定 | FR-007 |
| GET | `/documents/{id}/versions` | 版本歷程列表 | All（Partition 限制） | FR-013 |
| GET | `/documents/{id}/versions/{version}` | 取得特定版本快照 | All（Partition 限制） | FR-014 |
| POST | `/attribute-definitions` | 建立屬性定義 | Admin | FR-010 |
| GET | `/attribute-definitions` | 列出屬性定義 | All | FR-010 |

---

## 統一回應格式

### 成功回應
```json
// 201 Created (POST)
{ "id": "uuid", ...resource_fields }

// 200 OK (GET/PUT/PATCH)
{ ...resource_fields }

// 204 No Content (DELETE)
// (empty body)
```

### 錯誤回應（所有 4xx/5xx）
```json
{
  "detail": "人類可讀的錯誤說明",
  "code": "MACHINE_READABLE_CODE"
}
```

### 分頁回應格式（列表端點）
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "has_next": true,
  "has_prev": false
}
```

---

## 錯誤代碼一覽

| HTTP Status | code | 說明 |
|-------------|------|------|
| 401 | `AUTH_MISSING_TOKEN` | 缺少 Authorization header |
| 401 | `AUTH_TOKEN_EXPIRED` | JWT 已過期 |
| 401 | `AUTH_INVALID_TOKEN` | JWT 格式/簽名無效 |
| 403 | `PERMISSION_DENIED` | 角色不足（如非 Admin 嘗試刪除） |
| 403 | `PARTITION_ACCESS_DENIED` | 無此 Partition 存取權 |
| 404 | `RESOURCE_NOT_FOUND` | 資源不存在（UUID 正確但資料庫無此記錄） |
| 409 | `VERSION_CONFLICT` | 樂觀鎖版本衝突（current_version_lock 不符） |
| 409 | `DOCUMENT_HAS_DEPENDENCIES` | 文件有追溯連結，無法刪除 |
| 409 | `PROJECT_NOT_EMPTY` | Project 有文件，無法刪除 |
| 413 | `CONTENT_TOO_LARGE` | content_md 超過 5MB |
| 422 | `VALIDATION_ERROR` | 請求體欄位驗證失敗 |
| 422 | `INVALID_STATUS_TRANSITION` | 狀態轉換路徑非法 |
| 422 | `REQUIRED_ATTRIBUTE_MISSING` | 必填 EAV 屬性未提供 |
| 422 | `INVALID_ATTRIBUTE_VALUE` | EAV 屬性值型別/ENUM 不合法 |
| 422 | `PARTITION_PROJECT_MISMATCH` | partition_id 不屬於 project_id |
| 422 | `INVALID_UUID` | 路徑/Body 中 UUID 格式錯誤（FastAPI 自動） |
| 500 | `INTERNAL_SERVER_ERROR` | 非預期錯誤 |

---

## 詳細合約文件索引

| 資源模組 | 合約文件 |
|----------|----------|
| 認證 | [`contracts/auth.md`](auth.md) |
| 專案管理 | [`contracts/projects.md`](projects.md) |
| 文件管理 | [`contracts/documents.md`](documents.md) |
| Partition 管理 | [`contracts/partitions.md`](partitions.md) |
| 屬性定義 | [`contracts/attribute-definitions.md`](attribute-definitions.md) |
