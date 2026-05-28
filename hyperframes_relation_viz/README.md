# HyperFrames 檔案關係可視化 (MVP)

這個子專案提供最小可用流程，讓你快速把 Doc ERP 的檔案關係渲染成影片。

## 你會得到什麼

- 自動掃描專案內主要檔案（`.py`, `.md`, `.yaml`, `.yml`, `.csv`）
- 從 Python import 建立基礎依賴連線
- 從 Markdown link / heading / traceability JSON 建立跨文件關係
- 依 git 變更自動輸出 `SUSPECT` 候選清單（impact report）
- 在 HyperFrames composition 預覽關係圖
- 渲染成 MP4 影片，方便對使用者說明架構

## 需求

- Node.js 22+
- FFmpeg（HyperFrames render 需要）

## 快速開始

1. 進入目錄

```powershell
Set-Location .\hyperframes_relation_viz
```

2. 產生關係資料

```powershell
npm run build:data
```

3. 預覽

```powershell
npm run preview
```

4. 渲染影片

```powershell
npm run render
```

## 變更衝擊分析（SUSPECT 候選）

```powershell
npm run analyze:impact
```

輸出：`data/impact-report.json`

- `changed`: 直接改到的節點
- `suspect_paragraph`: 受影響段落候選
- `suspect_trace`: 受影響追溯 ID 候選
- `suspect_clause`: 受影響條文候選
- `suspect_checklist`: 受影響 checklist 候選
- `suspect_document`: 受影響文件候選

補充：

- 會優先使用 `git diff --unified=0` 的 hunk 行號定位 markdown 變更段落
- 每個衝擊項目都帶 `navigation.from / navigation.to / navigation.returnTo`

手動指定變更檔：

```powershell
node .\scripts\analyze-impact.mjs --changed specs/002-doce-erp-dms/spec.md,backend/app/services/dependency_engine.py --depth 2
```

## 檔案說明

- `index.html`: HyperFrames composition，顯示節點和連線
- `scripts/build-relations.mjs`: 掃描專案並輸出關係資料
- `data/relations.json`: 關係資料 (JSON)
- `data/relations.js`: 給前端 composition 直接讀取的資料

## MVP 限制

- 目前只做「專案檔案 + Python import」基礎視覺化
- 尚未解析跨語言 API 呼叫與規格語意連結
- 圖上節點顯示上限為 14，超過的節點仍在資料檔中

## 下一步可擴充

- 加入 API 規格 (`03_API_Specification.md`) 語意關聯
- 讓前端元件與後端路由關聯自動化
- 加入章節敘事與語音旁白，產生更完整導覽影片
- 依 git hunk 精準定位「變更段落」而非僅檔案層級
- 將稽核條文與 checklist 也納入圖譜節點
- 追加 AI 批次修正提案輸出（逐項 reviewer approve/reject）