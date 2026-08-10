# 論文編輯區寬度與檢視模式對齊、表格欄寬自動校正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓論文編輯模式的內容寬度固定等於檢視模式 A4 頁面的內容區寬度（602px），並讓表格欄寬能自動偵測「跟容器實際可用寬度對不上」的情況、按原本的相對比例重新縮放對齊，一次性解決「編輯區改版導致舊表格欄寬跟容器不對齊」的問題，也讓以後版面再改都能自動校正。

**Architecture:** `PaperPage.vue` 的編輯模式 `.paper-sheet` 從 `flex: 1`（跟隨容器伸縮）改成固定 670px（602px 內容區 + 左右 padding），靠左排；`.paper-citations` 加 `margin-left: auto` 貼齊右緣，讓編輯/檢視兩模式的評分面板位置一致。`columnResizeBalance.ts` 新增一個跟現有「拖曳欄界維持總寬不變」邏輯互補、不衝突的偵測機制：每次 view 更新時比對每張表格的欄寬總和跟其 `.tableWrapper` 容器的實際渲染寬度，對不上就按比例整批重新縮放。

**Tech Stack:** Vue 3 `<script setup>`、TypeScript、`@tiptap/pm/tables`（既有依賴，不新增套件）。

## Global Constraints

- 編輯模式內容區寬度固定為 602px（跟檢視模式 A4 頁面內容區一致），卡片外框寬度 670px（602 + 左右 padding 各 34px）。
- 編輯模式的卡片靠左排，不置中；`.paper-citations` 用 `margin-left: auto` 貼齊 `.paper-body` 最右緣，編輯/檢視兩模式下評分面板位置需一致。
- 表格欄寬重新縮放時，一律維持每一欄原本的相對比例不變（不管當初是自動平分還是使用者手動拖過的比例），只整批縮放去對齊新的容器寬度。
- 重新縮放的觸發容忍誤差為 2px（容器寬度與欄寬總和相差在 2px 以內視為一致，不觸發，避免 subpixel 誤差反覆觸發）。
- 新的重新縮放邏輯不能干擾既有的「拖曳欄界，緊鄰欄互相增減、總寬不變」邏輯（`appendTransaction` 那段）——兩者觸發時機天然不同（拖曳時容器寬度不變、總寬也不變，不會觸發重新縮放），不需要互斥鎖或額外協調。
- 不改動檢視模式（`PaginatedPaperView.vue`）本身；A4 頁面內容區本來就已經是固定 602px。

---

### Task 1: 編輯區固定寬度、評分面板貼齊右緣

**Files:**
- Modify: `frontend/src/views/PaperPage.vue`（模板約第 77 行、`<style scoped>` 的 `.paper-sheet`／`.paper-citations` 規則）

**Interfaces:**
- Consumes: 無
- Produces: 無（純 CSS/模板調整，沒有其他任務依賴這裡的介面）

- [ ] **Step 1: 模板加上 `.paper-sheet--editing` 修飾類別**

把現有（用內容比對，行號可能因為之前的改動略有偏移）：

```html
        <article v-else class="paper-sheet">
```

改成：

```html
        <article v-else class="paper-sheet paper-sheet--editing">
```

- [ ] **Step 2: 新增 `.paper-sheet--editing` 樣式**

在 `.paper-sheet--paginated` 規則附近（用內容比對），新增：

```css
  .paper-sheet--editing {
    flex: none;
    width: 670px; /* 602px 內容區 + 左右 padding 各 34px，跟 A4 頁面內容區一致 */
  }
```

- [ ] **Step 3: `.paper-citations` 加上 `margin-left: auto`**

把現有：

```css
  .paper-citations {
    width: 280px;
    flex-shrink: 0;
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: calc(100vh - 150px);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
```

改成：

```css
  .paper-citations {
    width: 280px;
    flex-shrink: 0;
    margin-left: auto;
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: calc(100vh - 150px);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
```

- [ ] **Step 4: 手動驗證**

本專案前端沒有自動化測試框架，驗證方式：

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤。

```bash
docker restart datamind-frontend
```

輪詢直到就緒：

```bash
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/)" = "200" ]; do sleep 1; done
```

用瀏覽器打開一篇論文頁面，切到編輯模式，用 DevTools console 執行：

```js
const editorContent = document.querySelector('.editor-content')
console.log(editorContent.getBoundingClientRect().width) // 應該是 602（容許 1px 內的 subpixel 誤差）
```

再切到檢視模式，確認 `.a4-page-content` 的寬度也是同樣的 602：

```js
document.querySelector('.a4-page-content').getBoundingClientRect().width
```

兩者應該完全一致。接著在編輯模式跟檢視模式下都檢查評分面板貼齊右緣：

```js
const citations = document.querySelector('.paper-citations')
const body = document.querySelector('.paper-body')
console.log(body.getBoundingClientRect().right - citations.getBoundingClientRect().right) // 應該接近 0
```

Expected: 上述數值都符合預期，畫面上編輯卡片靠左、評分面板靠右，沒有跑版或重疊。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "feat: fix paper editor width to match A4 view content width"
```

---

### Task 2: 表格欄寬自動偵測容器寬度變化並按比例校正

**Files:**
- Modify: `frontend/src/components/paper/columnResizeBalance.ts`（新增函式、掛進既有 `Plugin.view()` 的 `update` 回呼）

**Interfaces:**
- Consumes: Task 1 完成後編輯模式內容區固定 602px（此任務的驗證會依賴這個固定寬度，但程式碼本身不寫死 602，一律動態量測，因此技術上兩個任務順序互換也能各自運作，只是驗證時建議先做完 Task 1 再測這個任務，數字比較好核對）。
- Produces: 無（`columnResizeBalance.ts` 沒有匯出新的公開介面，`ColumnResizeBalance` 這個 Extension 本身的匯出/用法不變）。

- [ ] **Step 1: 新增容器寬度量測與比例縮放函式**

在 `frontend/src/components/paper/columnResizeBalance.ts` 的 `seedMissingColumnWidths` 函式之後（`export const ColumnResizeBalance = ...` 之前），新增：

```ts
const RESCALE_TOLERANCE_PX = 2

// 表格的 .tableWrapper 是一般 block 層級的 <div>，寬度會忠實反映容器實際可用寬度，
// 不受表格自己目前 table-layout:fixed 的欄寬總和影響（跟量測表格本身寬度不一樣）。
// prosemirror-tables 的 TableView 建立的 DOM 結構本身就是 <div class="tableWrapper">
// 包住 <table>，view.nodeDOM(tableDocPos) 對表格節點回傳的就是這個 wrapper div；
// 這裡多做一層防呆（往內找、往外找）避免版本差異或未來 NodeView 實作改變時直接量到錯的元素。
function findTableWrapperWidth (view: EditorView, tableDocPos: number): number | null {
  const dom = view.nodeDOM(tableDocPos)
  if (!(dom instanceof HTMLElement)) return null

  let wrapper: HTMLElement | null = dom
  if (!wrapper.classList.contains('tableWrapper')) {
    wrapper = wrapper.closest('.tableWrapper') ?? wrapper.querySelector('.tableWrapper')
  }

  return (wrapper ?? dom).getBoundingClientRect().width
}

// 欄寬是「建立當下」量測凍結的固定像素值，之後容器寬度如果變了（例如編輯區版面改版），
// 欄寬不會自動跟著調整，會出現表格比容器窄（或寬）一截的狀況。這裡在每次 view 更新時，
// 比對每張表格「目前欄寬總和」跟「容器實際可用寬度」，對不上（超過 RESCALE_TOLERANCE_PX）
// 就按原本的相對比例整批重新縮放，讓表格一律填滿容器寬度。
//
// 跟拖曳欄界（下面的 appendTransaction）不會互相干擾：拖曳過程中容器寬度沒變、欄寬總和
// 也刻意維持不變，不會被這裡判定為「對不上」而觸發重新縮放。
function rescaleMismatchedColumnWidths (view: EditorView): void {
  const { state } = view
  let tr: Transaction | null = null

  state.doc.descendants((node, pos) => {
    if (node.type.name !== 'table') return true
    const map = TableMap.get(node)

    const cols: { col: number, width: number }[] = []
    let totalWidth = 0
    for (let col = 0; col < map.width; col++) {
      const cellPos = representativeCellPos(map, col)
      if (cellPos === -1) return false
      const cellNode = node.nodeAt(cellPos)
      const width = cellNode?.attrs.colwidth?.[0]
      if (width == null) return false // 還沒被 seedMissingColumnWidths 處理過，這輪先跳過
      cols.push({ col, width })
      totalWidth += width
    }

    const availableWidth = findTableWrapperWidth(view, pos)
    if (availableWidth == null) return false
    if (Math.abs(availableWidth - totalWidth) <= RESCALE_TOLERANCE_PX) return false

    const scale = availableWidth / totalWidth
    for (const { col, width } of cols) {
      const newWidth = Math.round(width * scale)
      if (newWidth === width) continue
      if (!tr) tr = state.tr
      setColumnWidth(tr, pos + 1, map, col, newWidth)
    }

    return false
  })

  if (tr) view.dispatch(tr)
}
```

- [ ] **Step 2: 把新函式掛進既有的 view 更新回呼**

把現有第 85-96 行（`addProseMirrorPlugins` 裡的 `view` 定義）：

```ts
      new Plugin({
        key: new PluginKey('columnResizeBalance'),
        view (editorView) {
          seedMissingColumnWidths(editorView)
          return {
            update (view) {
              seedMissingColumnWidths(view)
            },
          }
        },
```

改成：

```ts
      new Plugin({
        key: new PluginKey('columnResizeBalance'),
        view (editorView) {
          seedMissingColumnWidths(editorView)
          rescaleMismatchedColumnWidths(editorView)
          return {
            update (view) {
              seedMissingColumnWidths(view)
              rescaleMismatchedColumnWidths(view)
            },
          }
        },
```

- [ ] **Step 3: 手動驗證——新表格與拖曳欄界行為不受影響**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤。

```bash
docker restart datamind-frontend
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/)" = "200" ]; do sleep 1; done
```

用瀏覽器打開一篇論文頁面、切到編輯模式（此時內容區應該已經是 Task 1 修好的 602px）：

1. 插入一張新表格，確認欄寬平分填滿整個內容區寬度（沒有右側留白）。
2. 用滑鼠拖曳調整某一欄的欄界，確認行為跟改動前一致——被拖曳欄變寬/變窄，緊鄰欄互補，表格總寬度不變（不會因為新加的重新縮放邏輯而在拖曳過程中被打斷或跳動）。

- [ ] **Step 4: 手動驗證——模擬舊表格欄寬跟新容器對不上，確認自動校正**

在同一個瀏覽器 session，選取剛剛拖曳調整過、有明確不同欄寬比例的那張表格，用 DevTools console 直接讀取並記錄目前各欄比例，然後人工製造一個「欄寬跟容器對不上」的情境（模擬舊資料）：

```js
// 找到表格的所有 th/td，代表欄的第一格，讀出目前的 colwidth 屬性值
const table = document.querySelector('.editor-content table')
const cells = Array.from(table.rows[0].cells)
console.log('修改前欄寬:', cells.map(c => c.style.width))
```

用瀏覽器 DevTools 的 Elements 面板，手動把其中一個 `<td>`/`<th>` 的 `style="width: Npx"` 改成明顯不同的數值（例如乘以 0.5），模擬「這張表格是照舊的、比較窄的編輯區寬度凍結下來的」。改完後隨便在編輯器裡打一個字元、再刪掉（觸發一次 view 更新），然後用 console 確認表格的欄寬已經被自動校正回填滿容器寬度、且各欄之間的相對比例跟「修改前欄寬」記錄的比例一致（允許 `Math.round` 帶來的 1-2px 誤差）。

Expected: 欄寬自動被重新縮放到填滿容器（各欄寬度總和約等於容器寬度，誤差在 `RESCALE_TOLERANCE_PX` 內），且各欄之間的相對比例跟修改前一致。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/paper/columnResizeBalance.ts
git commit -m "feat: auto-rescale table column widths when container width no longer matches"
```
