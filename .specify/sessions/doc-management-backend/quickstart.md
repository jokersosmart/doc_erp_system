# Quickstart: 文件管理後端 API 開發者指南

**Feature**: `doc-management-backend`  
**Date**: 2025-04-30  
**Target**: 新加入開發者，目標在 30 分鐘內完成本地環境搭建並執行全部測試（SC-010）

---

## 前置需求

| 工具 | 最低版本 | 安裝方式 |
|------|----------|----------|
| Python | 3.11+ | [python.org](https://python.org) 或 `pyenv` |
| Docker & Docker Compose | 24+ | [docs.docker.com](https://docs.docker.com) |
| Git | 2.x | 系統預裝 |

---

## Step 1：克隆並進入目錄

```bash
git clone <repo-url>
cd doc_erp_system/backend
```

---

## Step 2：建立 Python 虛擬環境

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows PowerShell

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

**`requirements.txt` 關鍵套件**:
```
fastapi==0.111.*
uvicorn[standard]==0.29.*
sqlalchemy[asyncio]==2.0.*
asyncpg==0.29.*
alembic==1.13.*
pydantic==2.*
pydantic-settings==2.*
python-jose[cryptography]==3.3.*
passlib[bcrypt]==1.7.*
```

**`requirements-dev.txt` 關鍵套件**:
```
pytest==8.*
pytest-asyncio==0.23.*
pytest-cov==5.*
httpx==0.27.*
```

---

## Step 3：設定環境變數

```bash
cp .env.example .env
# 編輯 .env，填入必要值（開發環境使用預設值即可）
```

**`.env.example` 內容**:
```env
# Database
DATABASE_URL=postgresql+asyncpg://docerp:docerp@localhost:5432/docerp

# JWT
SECRET_KEY=change-this-to-a-secure-random-secret-key-at-least-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# App
APP_NAME=DocERP Backend API
APP_VERSION=1.0.0
DEBUG=true

# Test Database (pytest 使用)
TEST_DATABASE_URL=postgresql+asyncpg://docerp:docerp@localhost:5432/docerp_test
```

---

## Step 4：啟動 PostgreSQL（Docker）

```bash
# 從 backend/ 目錄執行
docker-compose up -d postgres

# 等待 PostgreSQL 就緒（約 5 秒）
docker-compose ps
```

**`docker-compose.yml` 服務**:
```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: docerp
      POSTGRES_PASSWORD: docerp
      POSTGRES_DB: docerp
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U docerp"]
      interval: 5s
      timeout: 5s
      retries: 5

  # 同時建立 test database
  postgres_test:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: docerp
      POSTGRES_PASSWORD: docerp
      POSTGRES_DB: docerp_test
    ports:
      - "5433:5432"

volumes:
  postgres_data:
```

---

## Step 5：執行 Alembic Migration

```bash
# 執行所有 migration（建立 schema 與 seed data）
alembic upgrade head

# 驗證 migration 成功
alembic current
```

> Migration 包含初始 schema 建立（所有表）及 Seed Data（Standards、AttributeDefinitions、預設 Partitions）。

---

## Step 6：啟動開發伺服器

```bash
uvicorn app.main:app --reload --port 8000
```

開啟瀏覽器：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## Step 7：執行測試

```bash
# 建立測試資料庫（首次）
# TEST_DATABASE_URL 已指向 postgres_test（port 5433）
docker-compose up -d postgres_test

# 執行全部測試
pytest tests/ -v --cov=app --cov-report=term-missing

# 執行特定測試模組
pytest tests/unit/ -v
pytest tests/integration/test_documents.py -v -k "test_create"

# 查看覆蓋率報告（HTML）
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

**預期測試結果**:
```
tests/unit/test_security.py                ........   8 passed
tests/unit/test_document_service.py        ..........  10 passed
tests/unit/test_attribute_service.py       .......    7 passed
tests/integration/test_auth.py             .....      5 passed
tests/integration/test_projects.py         ....       4 passed
tests/integration/test_partitions.py       ....       4 passed
tests/integration/test_documents.py        ................. 17 passed
tests/integration/test_attributes.py       ......     6 passed
tests/contract/test_openapi_schema.py      ..         2 passed

Coverage: 87% (目標 ≥ 85%)
```

---

## Step 8：快速驗證 API 流程

以下為完整 End-to-End 驗證指令（使用 `curl`）：

```bash
BASE_URL="http://localhost:8000/api/v1"

# 1. 登入取得 Token（使用 Seed Data 測試帳號）
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

echo "Token: $TOKEN"

# 2. 建立 Project
PROJECT_ID=$(curl -s -X POST "$BASE_URL/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"ADAS Platform","description":"Test project"}' | jq -r '.id')

echo "Project ID: $PROJECT_ID"

# 3. 取得 SWE Partition ID（Seed Data 已建立）
PARTITION_ID=$(curl -s "$BASE_URL/partitions?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[] | select(.name=="SWE") | .id')

echo "Partition ID: $PARTITION_ID"

# 4. 取得必填屬性定義 ID（Document_Type）
ATTR_DOC_TYPE=$(curl -s "$BASE_URL/attribute-definitions?is_required=true" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[] | select(.name=="Document_Type") | .id')

ATTR_OWNER=$(curl -s "$BASE_URL/attribute-definitions?is_required=true" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[] | select(.name=="Document_Owner") | .id')

# 5. 建立文件
DOC_ID=$(curl -s -X POST "$BASE_URL/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"$PROJECT_ID\",
    \"partition_id\": \"$PARTITION_ID\",
    \"title\": \"Software Architecture Spec\",
    \"content_md\": \"# Overview\\n\\nThis is the SWE architecture.\",
    \"attributes\": [
      {\"attribute_id\": \"$ATTR_DOC_TYPE\", \"value\": \"Spec\"},
      {\"attribute_id\": \"$ATTR_OWNER\", \"value\": \"john.doe\"}
    ]
  }" | jq -r '.id')

echo "Document ID: $DOC_ID"

# 6. 讀取文件
curl -s "$BASE_URL/documents/$DOC_ID" -H "Authorization: Bearer $TOKEN" | jq .

# 7. 推進狀態 DRAFT → REVIEW
curl -s -X PATCH "$BASE_URL/documents/$DOC_ID/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"REVIEW"}' | jq .

echo "✅ End-to-End validation complete"
```

---

## 常見問題

### Q: `alembic upgrade head` 失敗，說找不到資料庫
確認 Docker PostgreSQL 已啟動且 `.env` 中 `DATABASE_URL` 正確：
```bash
docker-compose ps       # 確認 postgres 狀態為 Up
psql postgresql://docerp:docerp@localhost:5432/docerp -c "SELECT 1;"
```

### Q: 測試報錯 `asyncpg.InvalidCatalogNameError: database "docerp_test" does not exist`
```bash
docker-compose up -d postgres_test
# 等待 5 秒後重新執行測試
```

### Q: JWT 簽名驗證失敗（`401 AUTH_INVALID_TOKEN`）
確認 `.env` 中 `SECRET_KEY` 長度至少 32 字元，且所有服務使用同一份 `.env`。

### Q: 如何新增一個新的 AttributeDefinition？
```bash
curl -s -X POST "$BASE_URL/attribute-definitions" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Review_Deadline",
    "data_type": "STRING",
    "is_required": false
  }' | jq .
```

---

## Docker 完整部署（可選）

如需完整 Docker 部署（不使用本地 Python 環境）：

```bash
# 建立並啟動所有服務
docker-compose up -d --build

# 執行 migration
docker-compose exec api alembic upgrade head

# 查看 log
docker-compose logs -f api
```

**Dockerfile** 關鍵設定：
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
