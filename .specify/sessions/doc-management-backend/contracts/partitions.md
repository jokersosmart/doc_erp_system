# API Contract: Partitions

**Base Path**: `/api/v1/partitions`  
**Auth Required**: ✅ Bearer JWT  
**Spec FR**: FR-017

---

## POST `/partitions` — 建立 Partition
> 角色：Admin

**Request**:
```http
POST /api/v1/partitions
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "SWE",
  "description": "Software Engineering",
  "project_id": "project-uuid"
}
```

**Success Response `201 Created`**:
```json
{
  "id": "partition-uuid",
  "name": "SWE",
  "description": "Software Engineering",
  "project_id": "project-uuid",
  "created_at": "2025-04-30T10:00:00Z"
}
```

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 403 | `PERMISSION_DENIED` | 非 Admin |
| 404 | `RESOURCE_NOT_FOUND` | project_id 不存在 |
| 422 | `VALIDATION_ERROR` | `name` 缺失、格式錯誤或重複 |

---

## GET `/partitions` — 列出 Partition
> 角色：All | 可選 `project_id` 篩選

**Request**:
```http
GET /api/v1/partitions?project_id={uuid}
Authorization: Bearer <token>
```

**Success Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "partition-uuid",
      "name": "SWE",
      "description": "Software Engineering",
      "project_id": "project-uuid",
      "created_at": "2025-04-30T10:00:00Z"
    },
    {
      "id": "partition-uuid-2",
      "name": "SYS",
      "description": "System",
      "project_id": "project-uuid",
      "created_at": "2025-04-30T09:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "has_next": false,
  "has_prev": false
}
```

> **Seed Data**: 每個 Project 預設包含 SYS、SWE、HW、Safety、Security 五個 Partition（由 Seed Data 載入，Spec A-07）。
