# Feature Specification: Document Management Backend API

**Feature Branch**: `doc-management-backend`  
**Created**: 2025-04-30  
**Status**: Draft  
**Priority**: P1 — 文件管理與版本控制模組 (Document Management & Version Control)  
**Related Specs**: `01_System_Specification.md`, `02_Data_Model.md`, `03_API_Specification.md`, `06_Organization_Complexity_Analysis.md`

---

## 背景與動機 (Context & Motivation)

本功能為「車用標準文件 ERP 系統」的核心基礎模組，對應 ASPICE 3.1 及 ISO-26262/ISO-21434 標準文件管理需求。系統需支援 SiliconMotion 5 層組織深度、12 個職能部門、多維文件分類（手冊/程序/規範/表單），並以 Markdown 為原生格式儲存文件。

此模組是後續所有模組（追溯追蹤、AI 規格審查、Codebeamer 整合）的資料基礎，必須優先完成並驗證穩定性。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 工程師建立與管理規格文件 (Priority: P1)

一位 R&D 工程師（軟體層）需要在指定專案下，為 SWE Partition 建立一份「Software Architecture Specification」。他輸入文件標題、Markdown 內容，並附加 ASPICE 與 ISO-26262 特定屬性（如 ASIL Level: ASIL B、Document Type: Spec）。系統回傳文件 ID、初始版本號（1.0）、及建立時間戳記。

**Why this priority**: 沒有文件建立功能，整個系統就沒有資料來源。這是所有後續功能的先決條件，且工程師每天都需要此操作。

**Independent Test**: 可透過以下步驟獨立驗證：(1) 呼叫 `POST /documents`，(2) 以回傳的 Document ID 呼叫 `GET /documents/{id}`，驗證內容與屬性完整保存，即可交付基本文件儲存功能。

**Acceptance Scenarios**:

1. **Given** 已認證的 R&D 工程師（JWT 包含 SWE Partition 存取權），**When** 提交包含必填欄位（project_id, partition_id, title, content_md）及至少一個動態屬性的建立請求，**Then** 系統回傳 `201 Created`，文件以版本 `1.0`、狀態 `DRAFT` 存入資料庫，動態屬性值正確寫入 EAV 表。
2. **Given** 已存在的文件，**When** 工程師呼叫 `GET /documents/{id}`，**Then** 系統回傳完整的 Markdown 內容、所有動態屬性值、目前版本號與狀態，回應時間小於 500 毫秒。
3. **Given** 已存在的草稿文件，**When** 工程師提交更新請求（新的 content_md 與 commit_message），**Then** 系統回傳 `200 OK`，版本號遞增（如 1.0 → 1.1），舊版本內容可透過版本歷程 API 查詢。
4. **Given** 工程師嘗試存取其 Partition 之外的文件，**When** 提交 `GET /documents/{id}` 請求，**Then** 系統回傳 `403 Forbidden`，不洩露文件存在與否。

---

### User Story 2 — QA 推進文件狀態審核流程 (Priority: P1)

一位 QA（品質保證）人員需要將已完成的草稿文件推進至 REVIEW 狀態，並在審查通過後標記為 APPROVED。一旦 APPROVED，文件版本需鎖定，任何修改必須建立新版本。

**Why this priority**: 文件狀態機是 ASPICE 合規的核心要求；若狀態流程不正確，後續追溯標記（SUSPECT 觸發）與稽核紀錄（Codebeamer）都無法運作。

**Independent Test**: 可透過 State Transition API 串聯測試：DRAFT → REVIEW → APPROVED，並驗證 APPROVED 文件拒絕直接修改，即可獨立交付狀態管理功能。

**Acceptance Scenarios**:

1. **Given** 狀態為 `DRAFT` 的文件，**When** 文件 Owner 呼叫狀態轉換端點（`PATCH /documents/{id}/status`，body: `{ "status": "REVIEW" }`），**Then** 系統回傳 `200 OK`，狀態更新為 `REVIEW`，稽核日誌記錄操作者、時間戳記與狀態變更。
2. **Given** 狀態為 `REVIEW` 的文件，**When** QA 人員呼叫狀態轉換端點（body: `{ "status": "APPROVED" }`），**Then** 系統回傳 `200 OK`，狀態更新為 `APPROVED`，版本號鎖定（minor 改為 patch-only 或完全凍結）。
3. **Given** 狀態為 `APPROVED` 的文件，**When** 任何人嘗試以 `PUT /documents/{id}` 修改內容，**Then** 系統回傳 `409 Conflict`，並提示「需建立新版本」（不阻止但需明確確認）。
4. **Given** 文件狀態已為 `APPROVED`，**When** 嘗試執行非法轉換（如 APPROVED → DRAFT），**Then** 系統回傳 `422 Unprocessable Entity`，說明允許的狀態路徑（僅 APPROVED → OBSOLETE）。
5. **Given** DRAFT 狀態文件，**When** 非 Owner 或非主管角色的使用者嘗試推進至 REVIEW，**Then** 系統回傳 `403 Forbidden`。

---

### User Story 3 — 管理員維護專案與組織 Partition 結構 (Priority: P2)

系統管理員（Admin）需要建立新專案，並為其設定對應的 Partition（如 SYS, SWE, HW, Safety, Security）。工程師在建立文件時需能選擇正確的 Partition。

**Why this priority**: Partition 結構決定了文件的組織分類與 RBAC 邊界。此功能是文件建立流程的先決條件，但因初始設置一次性較多，優先級次於日常文件操作。

**Independent Test**: 可透過建立 Project → 建立 Partition → 在該 Partition 下建立 Document 的完整鏈路驗證，並確認跨 Partition 權限隔離有效。

**Acceptance Scenarios**:

1. **Given** 已認證的 Admin 使用者，**When** 提交 `POST /projects`（name, description），**Then** 系統回傳 `201 Created`，包含新生成的 UUID。
2. **Given** 已存在的專案，**When** Admin 提交 `POST /partitions`（name: "SWE", description），**Then** 系統回傳 `201 Created`，Partition 可立即用於文件分類。
3. **Given** 非 Admin 使用者，**When** 嘗試建立或刪除 Project/Partition，**Then** 系統回傳 `403 Forbidden`。
4. **Given** 已有文件的 Project，**When** Admin 嘗試刪除該 Project，**Then** 系統回傳 `409 Conflict`，說明需先移除所有文件或封存。

---

### User Story 4 — 工程師管理文件動態屬性（EAV 模型）(Priority: P2)

一位 Safety 工程師需要為文件附加 ISO-26262 專屬屬性（如 `ASIL_Level: ASIL D`、`Safety_Goal_ID: SG-001`）。這些屬性的定義不固定，會隨標準版本或專案需求動態擴展，不可硬編碼至資料庫 Schema。

**Why this priority**: EAV 屬性系統是 ASPICE/ISO 合規記錄的載體。若沒有動態屬性，文件只是純 Markdown 文字，無法進行標準合規性追蹤。

**Independent Test**: 可透過屬性定義 API 建立新屬性定義，再透過文件 API 設定/讀取屬性值，驗證資料型別約束（STRING/INTEGER/BOOLEAN/ENUM）正確執行。

**Acceptance Scenarios**:

1. **Given** 已定義的屬性（如 `ASIL_Level`，類型 ENUM，允許值: QM/A/B/C/D），**When** 工程師在建立或更新文件時附加 `{ "attribute_id": "uuid", "value": "ASIL B" }`，**Then** 系統驗證值合法並寫入 EAV 表，`GET /documents/{id}` 回應中包含此屬性及其值。
2. **Given** 屬性定義中 `is_required: true`（如強制的 Document_Owner 欄位），**When** 工程師建立文件時未附加此屬性，**Then** 系統回傳 `422 Unprocessable Entity`，明確指出缺少哪個必填屬性。
3. **Given** ENUM 類型屬性，**When** 提交不在允許值列表中的值（如 ASIL Level 填入 "ASIL E"），**Then** 系統回傳 `422 Unprocessable Entity`，並列出合法值。
4. **Given** Admin，**When** 呼叫 `POST /attribute-definitions` 新增屬性定義，**Then** 系統回傳 `201 Created`，該屬性立即可用於所有文件。

---

### User Story 5 — PM 查詢文件列表與版本歷程 (Priority: P2)

一位 PM 需要查看特定專案、特定 Partition 下的所有文件清單，並能夠篩選狀態（如只看 APPROVED 的文件）。同時，PM 需要查看某份文件的完整修改歷程（每次更新的版本號、修改者、commit message）。

**Why this priority**: 列表查詢與版本歷程是日常管理和稽核的基本需求，稽核人員尤其依賴此功能進行 ASPICE 評審。

**Independent Test**: 可透過建立多筆測試文件並執行不同篩選條件的列表查詢，驗證分頁、篩選、排序行為；再透過多次更新文件後查詢版本歷程 API，驗證歷程完整性。

**Acceptance Scenarios**:

1. **Given** 某專案下有 20 份文件，**When** PM 呼叫 `GET /documents?project_id={id}&partition_id={id}&status=APPROVED&page=1&page_size=10`，**Then** 回傳第一頁 10 筆 APPROVED 文件，包含總數（20 中符合條件者）、分頁 metadata。
2. **Given** 已更新 3 次的文件（版本 1.0, 1.1, 1.2），**When** PM 呼叫 `GET /documents/{id}/versions`，**Then** 回傳所有版本的列表，每項包含版本號、修改者 ID、commit_message、timestamp；時間由新至舊排序。
3. **Given** PM 呼叫 `GET /documents/{id}/versions/{version}`，**Then** 回傳該版本的完整 Markdown 內容快照，可與目前版本內容進行對比。

---

### User Story 6 — 系統透過 JWT 執行身份驗證與 RBAC 授權 (Priority: P1)

所有 API 請求必須攜帶有效的 JWT Token。Token 中包含使用者 ID、角色（PM/RD/QA/Admin）及可存取的 Partition 清單。系統根據角色與 Partition 決定每個操作的授權。

**Why this priority**: 安全性是車用系統的基本要求；未授權存取可能導致機密規格外洩。此功能必須與 P1 文件 CRUD 同步實作，不可分離。

**Independent Test**: 可透過測試以下情境獨立驗證：(1) 無 Token → 401，(2) 過期 Token → 401，(3) 合法 Token 但無 Partition 存取權 → 403，(4) 合法 Token 且有存取權 → 200。

**Acceptance Scenarios**:

1. **Given** 未攜帶 `Authorization: Bearer <token>` Header 的請求，**When** 呼叫任何受保護端點，**Then** 系統回傳 `401 Unauthorized`。
2. **Given** JWT Token 已過期，**When** 呼叫受保護端點，**Then** 系統回傳 `401 Unauthorized`，回應 body 包含 `"detail": "Token expired"`。
3. **Given** 角色為 `RD` 的使用者（JWT 包含 `partition_access: ["SWE"]`），**When** 嘗試存取 `SYS` Partition 的文件，**Then** 系統回傳 `403 Forbidden`。
4. **Given** 角色為 `QA` 的使用者，**When** 嘗試刪除任何文件，**Then** 系統回傳 `403 Forbidden`（刪除操作僅限 Admin 或 Owner）。
5. **Given** 角色為 `Admin` 的使用者，**When** 呼叫任何端點，**Then** 不受 Partition 限制，可存取所有資源。

---

### Edge Cases

- **並發寫入衝突**：當兩位工程師同時更新同一份文件時，系統應以樂觀鎖（版本號比對）拒絕較晚的提交，回傳 `409 Conflict` 並提示當前版本號。
- **超大 Markdown 文件**：單份文件 content_md 超過 10MB 時（如完整 ISO-26262 標準），系統應回傳 `413 Request Entity Too Large`，並建議使用 MECE 分割為子文件。
- **刪除有追溯連結的文件**：若文件已被其他文件引用為追溯來源，直接刪除應回傳 `409 Conflict`，提示先解除所有追溯連結，或改為 `OBSOLETE` 狀態。
- **空 Markdown 內容**：content_md 為空字串或僅含空白字元時，系統應回傳 `422 Unprocessable Entity`。
- **重複 attribute_id**：同一文件的屬性提交中含重複 attribute_id 時，系統應合併（後者覆蓋前者）或拒絕請求並說明問題。
- **UUID 格式錯誤**：路徑參數或請求體中的 ID 欄位不符合 UUID v4 格式時，系統應回傳 `422 Unprocessable Entity`，而非 `500 Internal Server Error`。
- **Partition 不屬於指定 Project**：建立文件時，若 partition_id 與 project_id 不對應，系統應回傳 `422 Unprocessable Entity`。

---

## Requirements *(mandatory)*

### Functional Requirements

#### 文件 CRUD

- **FR-001**: 系統必須允許已認證使用者透過 `POST /documents` 建立文件，必填欄位為 `project_id`、`partition_id`、`title`、`content_md`；選填欄位為 `attributes`（動態屬性清單）。
- **FR-002**: 系統必須在建立文件時自動生成 UUID、設定初始版本號為 `1.0`、設定初始狀態為 `DRAFT`，並記錄 `created_at` 與 `updated_at` 時間戳記。
- **FR-003**: 系統必須透過 `GET /documents/{id}` 回傳文件的完整資訊，包含 Markdown 內容、所有 EAV 動態屬性值、版本號、狀態、Owner ID。
- **FR-004**: 系統必須透過 `PUT /documents/{id}` 允許更新文件的 `content_md` 及動態屬性，並要求提供 `commit_message`，版本號需遞增（minor version bump）。
- **FR-005**: 系統必須透過 `DELETE /documents/{id}` 支援文件刪除，但僅限無追溯連結的文件；有連結的文件刪除嘗試應回傳 `409 Conflict`。
- **FR-006**: 系統必須透過 `GET /documents` 支援列表查詢，並允許以 `project_id`、`partition_id`、`status`、`owner_id` 篩選，支援分頁（`page`、`page_size`，預設 20 筆）及按 `updated_at` 排序。

#### 狀態機管理

- **FR-007**: 系統必須透過 `PATCH /documents/{id}/status` 執行文件狀態轉換，合法路徑為：`DRAFT → REVIEW → APPROVED → OBSOLETE`，所有其他轉換均應被拒絕（`422`）。
- **FR-008**: 系統必須在文件狀態轉換時記錄稽核日誌（audit log），包含操作者 ID、舊狀態、新狀態、時間戳記。
- **FR-009**: 系統必須在文件進入 `APPROVED` 狀態後，阻止直接修改 `content_md`；若需修改，需建立新版本（Version Fork），原版本保持 `APPROVED` 不變。

#### EAV 動態屬性

- **FR-010**: 系統必須支援 `POST /attribute-definitions` 新增屬性定義，欄位包含 `name`、`data_type`（STRING / INTEGER / BOOLEAN / ENUM）、`allowed_values`（ENUM 時必填）、`is_required`、可選的 `standard_id`。
- **FR-011**: 系統必須在寫入文件屬性值時驗證資料型別正確性及 ENUM 值合法性，不符合則回傳 `422 Unprocessable Entity`。
- **FR-012**: 系統必須在建立或更新文件時，檢查所有 `is_required: true` 的屬性定義均已提供值，否則回傳 `422 Unprocessable Entity`。

#### 版本歷程

- **FR-013**: 系統必須透過 `GET /documents/{id}/versions` 回傳該文件的所有歷史版本清單，每筆記錄包含版本號、修改者 ID、`commit_message`、`updated_at`，由新至舊排序。
- **FR-014**: 系統必須透過 `GET /documents/{id}/versions/{version}` 回傳指定版本的完整 Markdown 內容快照。
- **FR-015**: 系統必須保留文件的所有歷史版本，不得因更新而覆蓋舊版本資料。

#### 專案與 Partition 管理

- **FR-016**: 系統必須支援 `POST /projects` 與 `GET /projects`、`GET /projects/{id}`，允許 Admin 建立與查詢專案。
- **FR-017**: 系統必須支援 `POST /partitions` 與 `GET /partitions`，允許 Admin 建立與查詢 Partition（預定義值包含 SYS, HW, SWE, Safety, Security）。

#### 認證與授權

- **FR-018**: 所有 API 端點（除健康檢查 `/health` 外）必須驗證 `Authorization: Bearer <JWT>` Header，無效或缺失的 Token 應回傳 `401 Unauthorized`。
- **FR-019**: JWT Payload 必須包含 `user_id`、`role`（PM / RD / QA / Admin）、`partition_access`（可存取的 Partition ID 清單）、`exp`（過期時間）。
- **FR-020**: 系統必須根據 JWT 中的 `role` 和 `partition_access` 執行 RBAC，確保使用者只能存取其被授權的 Partition 下的文件。
- **FR-021**: 系統必須支援 `POST /auth/login`（接受 `username`/`password`）並回傳 JWT Token 及 Refresh Token；支援 `POST /auth/refresh` 刷新 Access Token。

#### 非功能性 API 行為

- **FR-022**: 所有 API 必須在請求處理失敗時回傳結構化 JSON 錯誤回應，格式為 `{ "detail": "<message>", "code": "<error_code>" }`。
- **FR-023**: 系統必須提供 `/health` 端點，回傳服務狀態與資料庫連線狀態（用於 Railway 等雲端平台的健康檢查）。
- **FR-024**: 系統必須在 `/docs` 提供 OpenAPI 3.0 互動式 API 文件（FastAPI 內建 Swagger UI）。

---

### Key Entities *(include if feature involves data)*

- **Project（專案）**: 代表一個完整的開發專案。屬性：UUID、名稱、描述、建立時間。一個 Project 包含多個 Document，並關聯多個 Partition。
- **Partition（組織分層）**: 對應組織層級，如 SYS、SWE、HW、Safety、Security。屬性：UUID、名稱（縮寫）、描述。決定文件的歸屬層級與使用者存取邊界。
- **Document（文件）**: 系統核心實體。屬性：UUID、project_id、partition_id、title、content_md（Markdown 正文）、version（語意版本）、status（狀態機）、owner_id、建立/更新時間戳記。
- **DocumentVersion（文件版本快照）**: 記錄每次文件更新的歷史狀態。屬性：UUID、document_id、版本號、content_md 快照、修改者 ID、commit_message、時間戳記。
- **AttributeDefinition（屬性定義）**: EAV 模型的「E」。屬性：UUID、name、data_type（STRING / INTEGER / BOOLEAN / ENUM）、allowed_values（ENUM 允許值列表）、is_required、standard_id（選填，對應標準）。
- **DocumentAttributeValue（文件屬性值）**: EAV 模型的「V」。屬性：UUID、document_id、attribute_id、實際值（依 data_type 分欄儲存）。每對 (document_id, attribute_id) 唯一。
- **Standard（標準）**: 參考標準定義。屬性：UUID、name（如 "ASPICE 3.1"）、version。用於屬性定義的標準關聯。
- **AuditLog（稽核日誌）**: 記錄狀態轉換歷程（用於 ASPICE/ISO 合規稽核）。屬性：UUID、document_id、操作者 ID、操作類型、舊狀態、新狀態、時間戳記。
- **User（使用者）**: JWT 解碼後的身份資訊載體。屬性（邏輯）：user_id、role（PM / RD / QA / Admin）、partition_access（Partition UUID 清單）。本功能範疇內以 JWT 驗證為主，不含完整使用者管理 CRUD。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 文件建立操作（`POST /documents`）在正常負載下，90% 的請求在 500 毫秒內完成回應（不含網路延遲）。
- **SC-002**: 文件讀取操作（`GET /documents/{id}`）在正常負載下，99% 的請求在 200 毫秒內完成回應。
- **SC-003**: 系統在 50 個並發使用者同時操作（混合讀/寫 70:30）的情況下，不出現資料不一致或服務降級。
- **SC-004**: 所有文件狀態轉換操作皆有完整的稽核日誌記錄，日誌遺失率為 0%（在系統正常運作時）。
- **SC-005**: EAV 屬性驗證（必填屬性、ENUM 值範圍）的覆蓋率達到 100%，無合法漏洞可繞過驗證寫入非法屬性值。
- **SC-006**: JWT 授權錯誤（無效 Token、過期 Token、無 Partition 存取權）在各情境下均能正確回傳 `401` 或 `403`，跨 Partition 資料洩露為 0 件。
- **SC-007**: 所有 API 端點的自動化測試覆蓋率達到 85% 以上，包含正向情境與負向情境（邊界條件、錯誤輸入）。
- **SC-008**: 資料庫 Schema 變更透過 Alembic Migration 管理，所有 Migration 可在全新環境中執行無錯誤，並支援回滾（downgrade）。
- **SC-009**: API 文件（OpenAPI 3.0 / Swagger UI）自動生成，且所有端點均有清晰的描述、請求/回應範例，無須手動額外維護。
- **SC-010**: 新加入的開發人員可在 30 分鐘內完成本地開發環境搭建，並成功執行所有測試（依賴本地 PostgreSQL 或 Docker Compose）。

---

## Assumptions

### 技術假設

- **A-01**: 系統採用 Python FastAPI 作為 Web 框架，PostgreSQL 作為主資料庫，SQLAlchemy 作為 ORM，Alembic 管理 Schema Migration，Pydantic v2 作為資料驗證與序列化工具，`python-jose` 處理 JWT 簽發與驗證。
- **A-02**: JWT Token 由本系統自行簽發（`POST /auth/login`），使用對稱式密鑰（HS256），密鑰透過環境變數注入。本功能範疇不包含整合外部 SSO/OAuth2 Provider（此為後續擴展項目）。
- **A-03**: 本模組不實作完整的使用者管理系統（不包含 `POST /users`、使用者個人資料 CRUD 等）；使用者帳號以 Seed Data 或手動方式預先載入，供開發與測試使用。
- **A-04**: 文件 Markdown 內容以全文本（TEXT 欄位）儲存於 PostgreSQL；本功能範疇不包含 Git 版本控制整合（如 GitLab/GitHub 作為版本後端），版本歷程以資料庫快照方式管理。
- **A-05**: `content_md` 單份文件大小上限假設為 5MB（一般規格文件），超過限制時建議使用 MECE 文件分割策略。

### 範疇假設

- **A-06**: 本規格範疇內**不包含**以下功能（計劃於後續 Spec 中定義）：
  - 追溯連結管理（Traceability API）
  - AI 規格審查（AI Advisor API）
  - Codebeamer 整合匯出
  - 即時通知（WebSocket / Webhook 推送）
  - 前端 UI 實作
- **A-07**: Partition 的初始值（SYS, HW, SWE, Safety, Security）以 Seed Data 預先建立；Admin 可透過 API 新增自訂 Partition，但不支援刪除已有文件的 Partition。
- **A-08**: RBAC 角色定義（PM, RD, QA, Admin）固定，不支援自訂角色（動態角色管理為後續版本功能）。
- **A-09**: 多租戶（Multi-tenancy）架構在本版本中不支援，所有資料共享同一資料庫 Schema；企業內部部署環境下無需隔離。

### 環境假設

- **A-10**: 開發環境使用 Docker Compose 統一管理 PostgreSQL 與 FastAPI 服務；生產環境部署於 Railway（雲端驗證）或地端 On-Premise（正式生產），環境差異僅限環境變數配置。
- **A-11**: 所有敏感配置（JWT 密鑰、資料庫連線字串）均透過環境變數注入，不硬編碼於原始碼中。
- **A-12**: 標準定義（ASPICE 3.1, ISO-26262, ISO-21434）的 `Standard` 記錄與對應的 `AttributeDefinition` 以 Seed Data 預先載入，不透過本功能 API 自動建立。
