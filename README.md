# 車用標準文件 ERP 系統 (Document ERP System)

本專案旨在建立一個符合 ASPICE 3.1 及 ISO-26262/ISO-21434 標準的「文件 ERP 系統」。系統以規格驅動開發 (Specification-Driven Development, SDD) 為核心精神，提供自動化的文件管理、相依性追蹤、AI 規格檢查，並無縫整合至 Codebeamer 進行最終稽核。

## 專案目錄結構

- `01_System_Specification.md`: 系統規格文件，定義核心功能與架構。
- `02_Data_Model.md`: 資料模型，包含 EAV 動態屬性設計與資料庫 Schema。
- `03_API_Specification.md`: API 規格，定義前後端互動介面。
- `04_Post_SDD_Tool_Workflow.md`: 規格驅動開發完成後的工具流程指南。

## 開發流程與工具建議

本專案建議採用以下工具組合進行開發與部署：

1. **VS Code + Spec-kit**: 進行規格驅動開發 (SDD)，生成基礎代碼。
2. **Warp**: 作為 AI 終端機，進行本地高效除錯與 Git 操作。
3. **Factory**: 實現自動化代碼審查與 CI/CD 流程。
4. **Railway**: 進行無縫雲端部署與預覽環境託管。
5. **Mobbin + Magic Patterns**: 持續優化前端 UI/UX 體驗。
6. **PostHog**: 收集使用者行為數據，進行產品分析與監控。

## 作者

*Author: Joker*
