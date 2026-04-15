# 規格驅動開發 (SDD) 完成後的工具流程指南

當您在 VS Code IDE 中使用 Spec-kit 完成了「規格驅動開發 (SDD)」後，您的系統已經具備了基礎的程式碼結構和測試案例。接下來，我們將使用您兌換的工具組合，將這個系統推向生產環境。

## 1. 核心工具組合 (您的兌換清單)

1. **Warp** - AI 終端機 (開發與除錯)
2. **Factory** - 軟體開發自動化 (CI/CD 與自動化開發)
3. **Railway** - 雲端部署 (環境託管)
4. **PostHog** - 產品分析 (使用者行為與效能監控)
5. **Magic Patterns** & **Mobbin** - UI/UX 設計 (前端優化)

## 2. 端到端執行流程 (Post-SDD Workflow)

### 階段一：本地開發與除錯 (使用 Warp)
當您在 VS Code 中寫完 Spec 並生成初步代碼後：
1. **啟動 Warp 終端機**：取代傳統的終端機。
2. **AI 輔助除錯**：當 Spec-kit 生成的測試失敗時，直接在 Warp 中選取錯誤訊息，使用 Warp AI 詢問「如何修復這個測試錯誤？」。
3. **快速 Git 操作**：使用 Warp 的自然語言轉指令功能（例如輸入「提交所有更改並推送到 main 分支」），快速將代碼同步到 GitHub。

### 階段二：自動化開發與 CI/CD (使用 Factory)
代碼推送到 GitHub 後：
1. **觸發 Factory 工作流**：Factory 會監聽您的 GitHub 倉庫。
2. **自動化代碼審查**：Factory 的 AI Agent 會根據您的 Spec 文件，自動審查新提交的代碼是否符合規格要求。
3. **自動生成文件**：Factory 可以根據代碼變更，自動更新 API 文件或內部開發者指南。

### 階段三：雲端部署與託管 (使用 Railway)
當代碼通過 Factory 的審查後：
1. **連接 Railway 與 GitHub**：在 Railway 儀表板中，將您的 `doc_erp_system` 倉庫連接到 Railway 專案。
2. **自動建置與部署**：每次推送到 `main` 分支，Railway 會自動拉取最新代碼、安裝依賴、建置並部署您的應用程式。
3. **配置環境變數**：在 Railway 中設定資料庫連線字串 (PostgreSQL)、JWT 密鑰等環境變數。
4. **提供預覽環境 (Preview Environments)**：對於每個 Pull Request，Railway 會自動生成一個獨立的預覽 URL，讓您在合併前測試新功能。

### 階段四：前端 UI/UX 優化 (使用 Mobbin & Magic Patterns)
當後端 API 在 Railway 上運行後，您需要優化前端介面：
1. **尋找靈感 (Mobbin)**：在 Mobbin 上搜尋「Document Management」、「ERP」、「Diff Viewer」等關鍵字，參考業界最佳實踐。
2. **快速原型 (Magic Patterns)**：將 Mobbin 上的靈感輸入 Magic Patterns，快速生成 React/Vue 的前端組件代碼。
3. **整合至專案**：將生成的 UI 組件整合到您的前端代碼中，並連接 Railway 上的 API。

### 階段五：產品分析與監控 (使用 PostHog)
系統上線供內部使用者（PM, RD, QA）測試後：
1. **整合 PostHog SDK**：在您的前端應用程式中加入 PostHog 的追蹤代碼。
2. **設定自定義事件**：追蹤關鍵操作，例如「建立文件」、「觸發 AI 審查」、「接受 AI 建議 (Accept Diff)」、「匯出至 Codebeamer」。
3. **分析使用者行為**：
   - **漏斗分析 (Funnels)**：觀察使用者從「建立文件」到「完成審查」的轉化率，找出流程瓶頸。
   - **會話錄影 (Session Replays)**：觀看使用者如何與「Cursor-like Diff 視圖」互動，了解 UI 是否直觀。
   - **功能標記 (Feature Flags)**：如果您想先讓部分 PM 測試新功能，可以使用 PostHog 的 Feature Flags 進行灰度發布。

## 3. 總結：工具協作的閉環

1. **VS Code + Spec-kit**：定義規格並生成基礎代碼。
2. **Warp**：本地高效除錯與 Git 操作。
3. **Factory**：自動化審查與 CI/CD。
4. **Railway**：無縫雲端部署與預覽。
5. **Mobbin + Magic Patterns**：持續優化前端體驗。
6. **PostHog**：收集數據回饋，產生新的規格需求（回到步驟 1）。

---
*Author: Joker*
