# API Contract: Authentication

**Base Path**: `/api/v1/auth`  
**Auth Required**: ❌ (除 `/auth/refresh` 驗證 refresh_token 外)  
**Spec FR**: FR-018, FR-019, FR-021

---

## POST `/auth/login`

登入並取得 JWT Access Token + Refresh Token。

**Request**:
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "john.doe",
  "password": "securepassword"
}
```

**Success Response `200 OK`**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "a3f4b2c1-d5e6-7890-abcd-ef1234567890",
  "token_type": "bearer",
  "expires_in": 900
}
```

**JWT Access Token Payload**:
```json
{
  "sub": "user-uuid-here",
  "role": "RD",
  "partition_access": ["partition-uuid-1", "partition-uuid-2"],
  "exp": 1735689600,
  "iat": 1735688700,
  "type": "access"
}
```

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 422 | `VALIDATION_ERROR` | 缺少 username 或 password |
| 401 | `AUTH_INVALID_TOKEN` | 帳號或密碼錯誤（統一回傳，不區分） |

---

## POST `/auth/refresh`

使用 Refresh Token 取得新的 Access Token（Rotation：舊 Refresh Token 同時失效）。

**Request**:
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "a3f4b2c1-d5e6-7890-abcd-ef1234567890"
}
```

**Success Response `200 OK`**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "new-refresh-token-uuid",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Error Responses**:
| Status | code | 條件 |
|--------|------|------|
| 401 | `AUTH_INVALID_TOKEN` | Refresh Token 無效或已被 rotation |
| 401 | `AUTH_TOKEN_EXPIRED` | Refresh Token 已過期（7 天） |

---

## GET `/health`

健康檢查端點，不需 Auth，用於 Railway/Docker 容器監控。

**Request**:
```http
GET /health
```

**Success Response `200 OK`**:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

**Degraded Response `503 Service Unavailable`**:
```json
{
  "status": "unhealthy",
  "database": "disconnected",
  "detail": "Database connection failed"
}
```
