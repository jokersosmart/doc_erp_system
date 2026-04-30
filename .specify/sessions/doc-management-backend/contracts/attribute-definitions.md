# API Contract: Attribute Definitions

**Base Path**: `/api/v1/attribute-definitions`  
**Auth Required**: ✅ Bearer JWT  
**Spec FR**: FR-010, FR-011, FR-012

---

## POST `/attribute-definitions` — 建立屬性定義
> 角色：Admin | FR-010

**Request**:
```http
POST /api/v1/attribute-definitions
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "ASIL_Level",
  "data_type": "ENUM",
  "allowed_values": ["QM", "A", "B", "C", "D"],
  "is_required": false,
  "standard_id": "uuid-of-ISO-26262"
}
```

**Field Constraints**:
| 欄位 | 必填 | 規則 |
|------|------|------|
| `name` | ✅ | 1~100 字元，同一 standard 下唯一 |
| `data_type` | ✅ | `STRING` \| `INTEGER` \| `BOOLEAN` \| `ENUM` |
| `allowed_values` | ✅ (ENUM 時) | 非空陣列，每個值為字串 |
| `is_required` | ❌ | 預設 `false` |
| `standard_id` | ❌ | 有效的 Standard UUID |

**Success Response `201 Created`**:
```json
{
  "id": "attr-def-uuid",
  "name": "ASIL_Level",
  "data_type": "ENUM",
  "allowed_values": ["QM", "A", "B", "C", "D"],
  "is_required": false,
  "standard_id": "uuid-of-ISO-26262",
  "standard_name": "ISO-26262",
  "created_at": "2025-04-30T10:00:00Z"
}
```

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 403 | `PERMISSION_DENIED` | 非 Admin |
| 404 | `RESOURCE_NOT_FOUND` | `standard_id` 不存在 |
| 422 | `VALIDATION_ERROR` | 欄位格式錯誤，如 ENUM 但未提供 `allowed_values` |

---

## GET `/attribute-definitions` — 列出屬性定義
> 角色：All | 可選 `standard_id` 或 `is_required` 篩選

**Request**:
```http
GET /api/v1/attribute-definitions?standard_id={uuid}&is_required=true
Authorization: Bearer <token>
```

**Query Parameters**:
| 參數 | 型別 | 說明 |
|------|------|------|
| `standard_id` | UUID | 篩選特定標準的屬性 |
| `is_required` | bool | 篩選必填屬性 |

**Success Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "attr-def-uuid",
      "name": "ASIL_Level",
      "data_type": "ENUM",
      "allowed_values": ["QM", "A", "B", "C", "D"],
      "is_required": false,
      "standard_id": "uuid-of-ISO-26262",
      "standard_name": "ISO-26262",
      "created_at": "2025-04-30T10:00:00Z"
    },
    {
      "id": "attr-def-uuid-2",
      "name": "Document_Type",
      "data_type": "ENUM",
      "allowed_values": ["Spec", "Design", "Test", "Procedure"],
      "is_required": true,
      "standard_id": "uuid-of-ASPICE",
      "standard_name": "ASPICE 3.1",
      "created_at": "2025-04-30T09:00:00Z"
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20,
  "has_next": false,
  "has_prev": false
}
```

---

## EAV 屬性值驗證規則（FR-011, FR-012）

### 型別驗證
| data_type | 合法值範例 | 非法值範例 | 錯誤 code |
|-----------|-----------|-----------|-----------|
| STRING | `"SG-001"` | `123`（若非字串型別）| `INVALID_ATTRIBUTE_VALUE` |
| INTEGER | `42` | `"forty-two"` | `INVALID_ATTRIBUTE_VALUE` |
| BOOLEAN | `true` / `false` | `"yes"` | `INVALID_ATTRIBUTE_VALUE` |
| ENUM | `"ASIL B"`（在允許值中）| `"ASIL E"` | `INVALID_ATTRIBUTE_VALUE` |

### 必填屬性驗證（FR-012）
建立或更新文件時，系統查詢所有 `is_required = true` 的 `AttributeDefinition`，驗證請求的 `attributes` 陣列中均有對應記錄。

```
缺少必填屬性 → 422 REQUIRED_ATTRIBUTE_MISSING
{
  "detail": "Required attribute 'Document_Owner' (uuid) is missing",
  "code": "REQUIRED_ATTRIBUTE_MISSING"
}
```

### 重複 attribute_id 處理
同一文件的 `attributes` 陣列中含重複 `attribute_id` 時，**後者覆蓋前者**（合併策略，Edge Case spec 選項 1）。

> **Seed Data**: 
> - `ASIL_Level` (ENUM: QM/A/B/C/D, is_required: false, standard: ISO-26262)
> - `Document_Type` (ENUM: Spec/Design/Test/Procedure, is_required: true, standard: ASPICE 3.1)
> - `Document_Owner` (STRING, is_required: true, standard: ASPICE 3.1)
> - `Safety_Goal_ID` (STRING, is_required: false, standard: ISO-26262)
> - `Threat_ID` (STRING, is_required: false, standard: ISO-21434)
