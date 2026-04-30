# API Contract: Projects

**Base Path**: `/api/v1/projects`  
**Auth Required**: ✅ Bearer JWT  
**Spec FR**: FR-016

---

## POST `/projects` — 建立專案
> 角色：Admin

**Request**:
```http
POST /api/v1/projects
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "ADAS Platform v2",
  "description": "Advanced Driver Assistance System Platform"
}
```

**Success Response `201 Created`**:
```json
{
  "id": "project-uuid",
  "name": "ADAS Platform v2",
  "description": "Advanced Driver Assistance System Platform",
  "created_at": "2025-04-30T10:00:00Z",
  "updated_at": "2025-04-30T10:00:00Z"
}
```

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 403 | `PERMISSION_DENIED` | 非 Admin |
| 422 | `VALIDATION_ERROR` | `name` 缺失或超過 255 字元 |

---

## GET `/projects` — 列出所有專案
> 角色：All

**Request**:
```http
GET /api/v1/projects
Authorization: Bearer <token>
```

**Success Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "project-uuid",
      "name": "ADAS Platform v2",
      "description": "Advanced Driver Assistance System Platform",
      "created_at": "2025-04-30T10:00:00Z",
      "updated_at": "2025-04-30T10:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "has_next": false,
  "has_prev": false
}
```

---

## GET `/projects/{id}` — 取得專案詳情
> 角色：All

**Request**:
```http
GET /api/v1/projects/{id}
Authorization: Bearer <token>
```

**Success Response `200 OK`**: 同單筆 Project 物件格式。

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 404 | `RESOURCE_NOT_FOUND` | 專案不存在 |
| 422 | `VALIDATION_ERROR` | id 不是合法 UUID 格式 |
