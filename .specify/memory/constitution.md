# Doc_erp_system Constitution
<!-- Document ERP System Constitution based on ASPICE and ISO standards -->

## Core Principles

### I. 規格驅動開發 (Specification-Driven Development, SDD)
<!-- 核心開發精神 -->
所有開發活動必須以規格文件為起點。任何功能實作、架構變更或資料模型調整，皆須先在對應的 Markdown 規格文件中定義並獲得核准後，方可進入程式碼實作階段。規格文件是系統行為的唯一真相來源 (Single Source of Truth)。

### II. 自動化相依性管理 (Automated Traceability)
<!-- 確保文件一致性 -->
系統必須維持雙向追溯矩陣 (Bi-directional Traceability)。當上游文件（如系統規格）發生變更時，必須自動標記受影響的下游文件（如軟體架構、測試案例）為「可疑 (SUSPECT)」狀態，並強制要求相關負責人進行審查與更新，以防止「改了 A 忘了 B」的合規性風險。

### III. AI 輔助與標準合規 (AI-Assisted Compliance)
<!-- 確保符合 ASPICE/ISO 標準 -->
規格文件的撰寫與審查應積極利用 AI Agent 進行輔助。AI 必須根據 ASPICE 3.1、ISO-26262 及 ISO-21434 等標準條文，對文件內容進行自動合規性檢查，並提供具體的修改建議與草擬內容，以降低人工審查成本並提高標準符合度。
