# 論文檢視模式分頁功能 Design

## 背景與目標

`PaperPage.vue` 目前的檢視/編輯畫面是一張連續捲動的卡片（`.paper-sheet`），內容多長卡片就多長，沒有「頁」的概念。目標是讓**檢視模式**（`mode === 'view'`）以 A4 紙張比例呈現內容，內容滿一頁後自動接續到下一頁，視覺上接近印出來的多頁文件。編輯模式維持現狀，不做任何改動。

## 範圍

- **只影響檢視模式。** 編輯模式（`mode === 'edit'`）的 `PaperEditor.vue` 連續捲動行為完全不變——這是刻意的取捨：即時、逐字的分頁重排屬於 Word/Google Docs 等級的工程量（量測游標所在區塊高度、跨頁游標行為、表格/圖片跨頁分割等），效益／成本比太低，故排除在此次範圍外。
- 參考文獻（`ReferencesSection.vue` 現在顯示的內容）併入同一套分頁流程，跟正文一起排版、一起分頁。
- 每頁下方顯示「第 X 頁」頁碼。

## 架構

### 新檔案：`frontend/src/components/paper/paperExtensions.ts`

抽出 `PaperEditor.vue` 目前內嵌在 `useEditor()` 呼叫中、會影響 schema／渲染輸出的 Tiptap 擴充清單，做成共用工廠函式：

```ts
export function buildPaperContentExtensions (citationIndex: Record<string, number>) {
  return [
    StarterKit.configure({ heading: { levels: [1, 2, 3] }, link: false }),
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Link.configure({ openOnClick: false, autolink: true }),
    Superscript,
    Subscript,
    Table.configure({ resizable: true }),
    TableRow,
    ColoredTableHeader,
    ColoredTableCell,
    AlignableImage.configure({ inline: false }),
    CitationMark.configure({ citationIndex }),
  ]
}
```

`PaperEditor.vue` 改用這個函式，並在回傳的陣列後面自行追加只有互動編輯才需要的擴充（`CharacterCount`、`ColumnResizeBalance`）——這兩個只影響互動行為，不影響 HTML 輸出，所以不需要放進共用清單。這樣兩邊的排版/渲染規則保證一致，不會日後悄悄跑掉。

### 新檔案：`frontend/src/components/paper/PaginatedPaperView.vue`

唯讀元件，取代檢視模式下的 `<PaperEditor>` + `<ReferencesSection>`。

**Props：**
```ts
{
  content: JSONContent
  citations: Citation[]
  citationStyle: CitationStyle
}
```

**Emits：**
```ts
(e: 'citation-click', payload: { citationId: string, target: HTMLElement }): void
```
（跟 `PaperEditor.vue` 現有的 `citation-click` 事件簽章完全一致，`PaperPage.vue` 的 `onCitationClick` 不用改。）

**渲染流程：**
1. 用 `generateHTML(content, buildPaperContentExtensions(citationIndex))`（`generateHTML` 從 `@tiptap/core` 匯入，已是專案既有依賴，無需新增套件）把論文正文轉成靜態 HTML 字串。
2. 用跟 `ReferencesSection.vue` 相同的規則，把 `citations` 依 `citationStyle` 組成一段參考文獻 HTML（標題 `<h3>參考文獻</h3>` + `<ol>`/`<ul>` 清單項目），接在正文 HTML 之後。
3. 把組合後的 HTML 字串解析成 DOM 節點（用一個畫面外、`position:fixed; left:-99999px; visibility:hidden` 且寬度等於 A4 內容區寬度的容器），逐一量測每個**頂層區塊**（`p`、`h1~h3`、`ul`/`ol`、`table`、`blockquote`、圖片外層 `p` 等）的 `getBoundingClientRect().height`。
4. 貪婪分頁演算法：依序把區塊累加進目前頁面，累加高度超過每頁內容區可用高度（931px）時，開新的一頁，該區塊放到新頁面開頭。參考文獻的標題區塊有孤兒控制：若「標題＋緊接的第一個項目」放不進當頁剩餘空間，兩者一起換到下一頁（避免標題單獨留在頁尾）。
5. 依分頁結果，把每頁對應的區塊 `outerHTML` 組成字串陣列 `pages: string[]`，用 `v-html` 個別渲染進 `.a4-page` 卡片。
6. 在最外層容器上做一次點擊事件代理（比照 `PaperEditor.vue` 的 `editorProps.handleClick` 邏輯：`event.target.closest('[data-citation-id]')`），命中就 emit `citation-click`。

**重新計算時機：** `onMounted` 執行一次；並 `watch([() => props.content, () => props.citations, () => props.citationStyle])` 觸發重新分頁。編輯模式不會用到這個元件，所以不會有逐字重排的效能問題。

**已知限制：** 分頁只切在區塊之間，不切區塊內部。若單一表格或清單本身比一整頁還高，會整個放在自己的一頁、允許視覺上超出頁面高度，不會攔腰截斷內容。真正的「表格跨頁接續＋重複表頭」不在此次範圍內。

## 頁面規格

- 單頁尺寸：794×1123px（A4 210mm×297mm，96dpi 換算）。
- 四邊留白 96px（比照 Word 預設 1 吋邊界），內容區約 602×931px。
- 多頁之間留視覺間距、直向堆疊、水平置中；沿用現有 `.paper-body { overflow: auto }` 處理捲動，不需改動外層容器。
- 每頁下方置中顯示「第 X 頁」。

## 資料流與整合點

`PaperPage.vue` 是唯一使用 `PaperEditor.vue` / `ReferencesSection.vue` 的地方。改動：

```html
<article class="paper-sheet" :class="{ 'paper-sheet--paginated': mode === 'view' }">
  <PaginatedPaperView
    v-if="mode === 'view'"
    :citation-style="report.citationStyle"
    :citations="report.citations"
    :content="report.content"
    @citation-click="onCitationClick"
  />
  <PaperEditor
    v-else
    v-model="report.content"
    :citations="report.citations"
    :editable="true"
    :project-id="projectId"
    @citation-click="onCitationClick"
  />
</article>
```

檢視模式下 `.paper-sheet` 本身不再需要卡片樣式（改由內部多張 `.a4-page` 呈現卡片感），編輯模式維持現有 `.paper-sheet` 樣式不變。

## 測試

- 元件層：給 `PaginatedPaperView` 短內容（確認只產生 1 頁）與人工建構的長內容（大量段落，確認正確產生多頁、頁碼遞增）。
- 引註點擊：渲染含 `citation-mark` 的內容，模擬點擊，斷言 emit 的 `citation-click` payload 正確。
- 參考文獻併入分頁：citations 陣列夠長時，確認參考文獻標題與項目正確接續在正文區塊之後、能跨頁。
- 手動驗證：在瀏覽器切換檢視/編輯模式，確認編輯模式排版與行為完全未變。
