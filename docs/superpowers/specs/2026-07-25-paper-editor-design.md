# 論文可編輯化設計（PaperPage word 化）

## 背景

`/paper`（`PaperPage.vue`）目前是純唯讀渲染：後端 `generate-paper` / `arxiv/generate` 用 Gemini 產生 markdown 論文，前端 `transformArxivResultToPaperReport` 把 markdown 轉成 `sections/paragraphs/segments` 結構，`PaperSection.vue` 逐段渲染，引用文字用 `<mark>` 高亮、點擊可在右側 `CitationPanel` 顯示對應文獻。

這份資料完全是一次性的：`paperStore.generatedReport` 讀一次就清空，沒有任何後端持久化，使用者離開頁面或重新整理就會遺失，也完全無法修改內容。

本次目標：讓使用者可以像 Word 一樣編輯生成的論文（格式化文字、表格等），並把編輯結果存到後端，下次回來還能看到，同時不遺失「這段文字引用自哪篇文獻」的資訊。

## 範圍

**做：**
- 新增可編輯模式（Word 式工具列：粗體/斜體/底線/刪除線/標題/清單/引言/對齊/表格/復原重做）
- 檢視／編輯雙模式切換，檢視模式保留現有的引用點擊高亮互動
- 引用歸屬用 Tiptap mark 保存在文件內容裡，編輯不會讓引用資訊消失
- 後端新增 JSON 檔案持久化（`report_bp`），以 `project_id` 為 key 存/讀
- `PaperSourcesView.vue` 導頁到 `/paper` 時帶上 `project` query，讓存檔/讀檔能對應到專案

**不做（out of scope）：**
- 多人協作／版本歷史／衝突處理（單人使用，後存覆蓋先存，跟現有系統一致）
- 匯出成真正的 `.docx` / PDF 檔案
- 引用文獻清單本身的編輯（新增/刪除/重排 `citations`）——只有正文可編輯
- 自動存檔（本次為手動點「儲存」）
- 帳號權限／`project_id` 不存在時的資料庫層驗證（沿用現有「project 只是前端字串 id」的假設）

## 架構總覽

用 [Tiptap](https://tiptap.dev/)（Vue 3 官方整合、MIT、headless）做單一編輯器元件，取代現在的唯讀 `PaperSection.vue` 渲染。檢視與編輯共用同一份 Tiptap 文件內容，差異只在於 `editable` 開關與是否綁定引用點擊事件：

- **檢視模式**（`editable=false`）：唯讀渲染，引用標記文字可點擊，觸發 `citation-click`，行為與現況一致
- **編輯模式**（`editable=true`）：可編輯、顯示工具列；引用標記文字仍可見，但不綁點擊事件（避免打字時誤觸）

引用歸屬用自訂的 **Citation mark**（概念上跟 Bold/Italic 一樣是附著在文字上的標記，多帶一個 `citationId` 屬性）。ProseMirror 的 mark 機制會讓這個標記跟著它所附著的文字走——使用者在段落中插字、加粗、搬動段落，citation 歸屬不會遺失。這代表不需要額外保留一份原始結構化資料當備份；檢視與編輯共用同一份「文件 + citation mark」。

## 資料模型

`frontend/src/constants/reportData.ts` 的 `PaperReport` 型別改為：

```ts
export interface Citation {
  id: string
  title: string
  authors: string
  journal: string
  year: number
  snippet: string
}

export interface PaperReport {
  title: string
  content: JSONContent   // Tiptap/ProseMirror 文件（@tiptap/core 的 JSONContent），含 citation mark
  citations: Citation[]  // 參考文獻清單，結構不變
}
```

原本的 `PaperSection` / `PaperSegment` 型別與 `citationIdsOf` 相關邏輯移除，改由 Tiptap 文件內的 citation mark 承載。

## 後端持久化

沒有資料庫，沿用 `services/rag/vector_store.py` 的 JSON 檔案持久化模式（`_load`/`_save`、`Path.write_text(json.dumps(...))`），以 `project_id` 當檔名 key：

- `backend/services/report/report_store.py`
  - `ReportStore(index_dir)`，預設目錄 `artifacts/paper_reports/`（同 `paper_rag.py` 用 `RAG_INDEX_DIR` 環境變數的模式，可用 `REPORT_STORE_DIR`）
  - `save(project_id: str, data: dict) -> dict`：寫入 `<project_id>.json`，補上 `updated_at`（ISO timestamp），回傳完整記錄
  - `load(project_id: str) -> dict | None`：讀檔，檔案不存在回 `None`
  - 模組層級 singleton：`get_report_store()`（沿用 `get_paper_rag_service()` 的寫法）

- `backend/routes/report.py`（`report_bp = Blueprint("report", __name__)`）
  - `POST /api/report/<project_id>`
    - JSON body：`{ title, content, citations }`
    - 呼叫 `store.save(project_id, data)`，回傳 `{ success: true, result: {...} }`
    - `content`/`title` 缺漏回 400
  - `GET /api/report/<project_id>`
    - 有資料回 `{ success: true, result: {...} }`
    - 查無資料回 404 `{ success: false, error: "not found" }`

- `backend/apps/__init__.py` 新增：
  ```python
  from routes.report import report_bp
  ...
  app.register_blueprint(report_bp, url_prefix="/api/report")
  ```

- `frontend/src/api/report.ts` 新增 `saveReport(projectId, payload)` / `getReport(projectId)`，比照 `frontend/src/api/arxiv.ts` 現有的 fetch 封裝寫法。

## 前端元件

### `components/paper/PaperEditor.vue`（新增）

包一個 `@tiptap/vue-3` 的 `Editor` 實例：

- Extensions：`StarterKit`（含 Bold/Italic/Strike/Heading/BulletList/OrderedList/Blockquote/History）+ `Underline` + `TextAlign` + `Table`/`TableRow`/`TableCell`/`TableHeader` + 自訂 `Citation` mark extension（`citationId` attribute，渲染成 `<span data-citation-id="...">`）
- 沿用現有慣例（`mockPaperReport` 註解：「引用編號 `[n]` 由 UI 依 citations 順序推導,不要寫進 text」）：可見的 `[n]` 數字**不**是文字內容的一部分，而是 Citation mark 用 CSS `::after` 依 `citations` 陣列順序（同現有 `citationIndex` 算法）動態算出來附加顯示。這樣使用者編輯文字時不會誤刪/誤改到引用編號本身
- Props：`modelValue: JSONContent`、`editable: boolean`、`citations: Citation[]`、`activeCitationId: string | null`
- Emits：`update:modelValue`（內容變更）、`citation-click`（僅 `editable=false` 時，點擊 citation mark 觸發）
- 工具列：僅 `editable=true` 時顯示，Vuetify icon button 綁定對應 Tiptap chain command（`toggleBold`、`toggleHeading`、`insertTable` 等）

### `views/PaperPage.vue`（改寫）

- 移除 `PaperSection.vue` 引用，改用 `PaperEditor.vue`
- 新增 `mode: Ref<'view' | 'edit'>`，預設 `'view'`
- 工具列按鈕：
  - 檢視模式：顯示「編輯」按鈕 → 切到 `'edit'`
  - 編輯模式：顯示「儲存」「取消」
    - 「儲存」：呼叫 `saveReport(projectId, { title, content: editor.getJSON(), citations })`，成功後切回 `'view'`；失敗顯示錯誤訊息、停留在編輯模式，編輯器內容不清空
    - 「取消」：捨棄目前變更（重新載入上次已存/生成的 `content` 進編輯器），切回 `'view'`
- 內容來源優先序（`onMounted`）：
  1. `paperStore.generatedReport`（剛從 `PaperSourcesView` 生成，優先顯示）
  2. 若有 `route.query.project`，呼叫 `getReport(projectId)` 讀已存檔版本
  3. 都沒有 → fallback `mockPaperReport`
- 若 `route.query.project` 不存在：停用「儲存」按鈕，顯示提示「此論文尚未關聯專案，無法儲存」；編輯功能本身仍可使用

### `utils/paperTransform.ts`（改寫）

`transformArxivResultToPaperReport` 改成直接輸出 Tiptap `JSONContent` 文件：
- markdown 的 `## 標題` 轉成 `heading` node
- 段落轉成 `paragraph` node
- 段落內的 `[n]` 引用標記（沿用原 `parseParagraph` 的 regex 解析邏輯）轉成套用 `Citation` mark（`citationId: cite-n`）的 text node；`[n]` 這個 token 本身被消耗掉、不寫進 text node 內容，可見編號由 `PaperEditor` 渲染時動態算出（見上）

### `views/PaperSourcesView.vue`（小改動）

`handleGenerate` 的 `router.push('/paper')` 改成 `router.push(\`/paper?project=${projectId.value}\`)`，讓存檔/讀檔能對應到專案。

## 錯誤處理

- **存檔失敗**（連線錯誤/後端 500）：顯示錯誤訊息，停留在編輯模式，編輯器內容不動，可重試
- **讀檔 404**（該 `project_id` 從未存過）：視為全新論文，走內容來源優先序的第 1/3 順位
- **沒有 `project_id`**：「儲存」按鈕停用並提示，編輯功能不受影響
- **單人使用**：不處理併發衝突，後存覆蓋先存

## 測試

專案目前前後端皆無自動化測試框架，維持現有慣例，手動驗證：

1. 啟動前後端 dev server
2. `/results` → 選文獻 → 生成論文 → 確認進入 `/paper?project=<id>` 為檢視模式，引用文字可點擊、右側面板正確高亮對應文獻
3. 點「編輯」→ 測試工具列（粗體、標題、清單、表格、對齊、復原/重做）→ 確認引用文字仍顯示但點擊無反應
4. 點「儲存」→ 確認切回檢視模式、`artifacts/paper_reports/<project_id>.json` 有寫入且內容正確
5. 重新整理頁面（保留 `?project=<id>`）→ 確認能讀回剛存的內容，且引用點擊互動恢復正常
6. 編輯模式下點「取消」→ 確認變更被捨棄、回到上次已存內容
7. 不帶 `project` query 直接開 `/paper` → 確認「儲存」按鈕停用並顯示提示，編輯功能仍可操作
