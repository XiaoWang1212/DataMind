# Data Table Panel 改動 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正 Data Table 節點面板的四個問題：重複標題、引導提示與檔名的排版、tap-hint 圈圈消失時機、drawer 展開高度。

**Architecture:** 全部改動集中在兩個既有檔案：`DataTablePanel.vue`（樣板/腳本/樣式）與 `useDrawerDrag.ts`（一個常數）。不新增元件、不新增狀態管理，維持既有 `<script setup>` + scoped CSS 的寫法。

**Tech Stack:** Vue 3 `<script setup lang="ts">`, scoped CSS，無額外套件。

## Global Constraints

- 本專案前端未設置任何自動化測試框架（無 vitest/jest，`package.json` 沒有 `test` script）。依照 `CLAUDE.md` 的慣例（後端也只有手動 curl smoke test），本計畫不新增測試框架，全部改動以「啟動 `npm run dev`、在瀏覽器手動操作驗證」取代自動化測試步驟。
- 所有使用者可見文字維持繁體中文（既有慣例）。
- 每個 Task 完成後都要能獨立在瀏覽器裡看到對應效果，不依賴後面尚未完成的 Task。
- Spec 來源：`docs/superpowers/specs/2026-07-09-data-table-panel-design.md`

---

## Task 1: 移除面板內部重複的「Data Table」標題

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:3-8`（template header 區塊）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:479-494`（`.data-table-header` / `.data-table-title` / `.data-table-file` CSS）

**Interfaces:**
- Consumes: 無（純刪除既有標題）
- Produces: `.data-table-header` 之後只剩一個條件渲染的 `.data-table-file` 子元素，且用 `margin-left: auto` 讓它固定靠右對齊——**Task 2 會在它前面插入引導文字元素**，屆時靠右對齊行為必須維持不變。

- [ ] **Step 1: 刪除重複的標題 div**

把 `DataTablePanel.vue` 目前的 header 區塊：

```html
    <div class="data-table-header">
      <div class="data-table-title">Data Table</div>
      <div v-if="fileName" class="data-table-file">
        已選檔案：{{ fileName }}
      </div>
    </div>
```

改成：

```html
    <div class="data-table-header">
      <div v-if="fileName" class="data-table-file">
        已選檔案：{{ fileName }}
      </div>
    </div>
```

- [ ] **Step 2: 調整 CSS，讓檔名在只剩單一子元素時仍靠右對齊**

把：

```css
  .data-table-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .data-table-title {
    font-weight: 700;
    font-size: 16px;
  }

  .data-table-file {
    color: #475569;
    font-size: 13px;
  }
```

改成（移除 `justify-content: space-between`、刪除不再使用的 `.data-table-title`、在 `.data-table-file` 加上 `margin-left: auto` 讓它永遠靠右）：

```css
  .data-table-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .data-table-file {
    margin-left: auto;
    color: #475569;
    font-size: 13px;
  }
```

- [ ] **Step 3: 手動驗證**

執行（若尚未啟動）：

```bash
cd frontend && npm run dev
```

在瀏覽器開啟 `http://localhost:3000/workflow`，上傳一份 CSV，點選畫布上的 Data Table 節點，確認：
- 面板抽屜裡「Data Table」文字只出現一次（來自外層 `panel-header` 的 `<h3>`）
- 「已選檔案：xxx」文字靠右對齊、垂直置中

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "fix: remove duplicate Data Table title in panel header"
```

---

## Task 2: 引導提示文字搬到跟檔名同一行

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue`（template：header 區塊 + 移除原本獨立的 guide 區塊；style：`.data-table-guide` 相關規則）

**Interfaces:**
- Consumes: Task 1 產出的 `.data-table-header`（目前只有 `.data-table-file`，且靠右對齊）、既有的 `hasTarget`、`targetColumnName`、`props.loading`、`previewColumns`（皆為既有 script 內的 computed/ref，型別不變）
- Produces: `.data-table-header` 內第一個子元素為引導文字 `.data-table-guide`，後面接 `.data-table-file`；後續 Task 不依賴此輸出。

- [ ] **Step 1: 把引導文字移進 header，並拿掉原本獨立的區塊**

先刪除目前位於 `v-else`（欄位已解析完成）區塊開頭、獨立一整行的 guide：

```html
    <div v-else>
      <div
        v-if="props.loading"
        class="data-table-guide"
        :class="{ 'data-table-guide--ready': hasTarget }"
      >
        <span v-if="hasTarget">
          已選定目標變數「{{ targetColumnName }}」，按右下角「繼續」即可進入下一步。
        </span>
        <span v-else>
          請將要預測的欄位在下方「Role」欄選為 <strong>Target</strong>，再按右下角「繼續」。
        </span>
      </div>

      <div class="data-table-summary">
```

改成（移除整個 guide div，`data-table-summary` 直接接在 `v-else` 後面）：

```html
    <div v-else>
      <div class="data-table-summary">
```

接著把同樣的 guide markup 加進 header，放在 `.data-table-file` **前面**（Task 1 完成後的 header 內容）：

```html
    <div class="data-table-header">
      <div v-if="fileName" class="data-table-file">
        已選檔案：{{ fileName }}
      </div>
    </div>
```

改成：

```html
    <div class="data-table-header">
      <div
        v-if="props.loading && previewColumns.length > 0"
        class="data-table-guide"
        :class="{ 'data-table-guide--ready': hasTarget }"
      >
        <span v-if="hasTarget">
          已選定目標變數「{{ targetColumnName }}」，按右下角「繼續」即可進入下一步。
        </span>
        <span v-else>
          請將要預測的欄位在下方「Role」欄選為 <strong>Target</strong>，再按右下角「繼續」。
        </span>
      </div>
      <div v-if="fileName" class="data-table-file">
        已選檔案：{{ fileName }}
      </div>
    </div>
```

（原本 guide 只在「檔案已解析出欄位」的 `v-else` 分支裡才會出現，因為 header 現在是無條件渲染的最上層元素，所以用 `previewColumns.length > 0` 明確補回同樣的判斷條件。）

- [ ] **Step 2: 把 guide 樣式從色塊底框改成行內文字**

把：

```css
  .data-table-guide {
    padding: 12px 14px;
    margin-bottom: 12px;
    border-radius: 10px;
    border: 1px solid rgba(0, 93, 255, 0.18);
    background: rgba(0, 93, 255, 0.05);
    color: #1e293b;
    font-size: 13px;
    line-height: 1.5;
  }

  .data-table-guide strong {
    color: #005dff;
  }

  .data-table-guide--ready {
    border-color: rgba(16, 185, 129, 0.35);
    background: rgba(16, 185, 129, 0.08);
  }
```

改成：

```css
  .data-table-guide {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #005dff;
    font-size: 13px;
    line-height: 1.4;
  }

  .data-table-guide strong {
    color: #005dff;
  }

  .data-table-guide--ready {
    color: #10b981;
  }
```

並在 `.data-table-file` 加上 `flex-shrink: 0;`，確保檔名文字不會被引導文字擠壓、永遠完整顯示：

```css
  .data-table-file {
    flex-shrink: 0;
    margin-left: auto;
    color: #475569;
    font-size: 13px;
  }
```

- [ ] **Step 3: 手動驗證**

在瀏覽器（`npm run dev` 開著）操作：
- 上傳 CSV、選到 Data Table 節點、且流程處於等待設定欄位狀態（`loading` 為 true）：header 左側應顯示藍色文字「請將要預測的欄位在下方「Role」欄選為 Target，再按右下角「繼續」。」，右側顯示「已選檔案：xxx」，兩者同一行
- 把某一欄的 Role 改成 Target：左側文字應切換成綠色的「已選定目標變數「欄位名」，按右下角「繼續」即可進入下一步。」
- 把 Target 改回 Feature（取消選定）：左側文字應變回未選定的提示，不會消失

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "refactor: move target-selection guide onto the filename row"
```

---

## Task 3: Role 下拉選單 tap-hint 改成點開任一列就永久消失

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue`（script setup：新增狀態與 handler；template：role select 加事件、tap-hint 判斷條件）

**Interfaces:**
- Consumes: 既有的 `props.loading`、`columnSettings`（`ref<ColumnSetting[]>`）
- Produces: `roleSelectTouched`（`Ref<boolean>`）與 `handleRoleSelectFocus(): void`，僅本檔案內使用，不影響其他 Task。

- [ ] **Step 1: 新增「是否已點過任一列 Role 選單」的狀態**

在 script setup 裡，緊接在既有的：

```ts
  const isLoading = ref(false)
```

後面加上：

```ts
  const roleSelectTouched = ref(false)

  function handleRoleSelectFocus (): void {
    roleSelectTouched.value = true
  }
```

- [ ] **Step 2: 在每一列的 Role `<select>` 加上 focus 事件**

找到 role select 的 template（`role-select-wrap` 內）：

```html
                    <select
                      v-model="column.role"
                      class="role-select"
                      :class="{
                        'role-select--attention': props.loading && !hasTarget,
                      }"
                    >
```

改成（加上 `@focus`）：

```html
                    <select
                      v-model="column.role"
                      class="role-select"
                      :class="{
                        'role-select--attention': props.loading && !hasTarget,
                      }"
                      @focus="handleRoleSelectFocus"
                    >
```

- [ ] **Step 3: 把 tap-hint 的顯示條件從「是否已選 Target」改成「是否已點過任一列 Role 選單」**

找到：

```html
                    <span
                      v-if="props.loading && !hasTarget && index === 0"
                      aria-hidden="true"
                      class="tap-hint"
                    >
```

改成：

```html
                    <span
                      v-if="props.loading && !roleSelectTouched && index === 0"
                      aria-hidden="true"
                      class="tap-hint"
                    >
```

- [ ] **Step 4: 手動驗證**

在瀏覽器操作：
- 上傳 CSV、選到 Data Table 節點、流程處於等待設定欄位狀態、且尚未選 Target：第一列 Role 欄應該看得到動畫圈圈（tap-hint）
- 點開（focus）**任一列**（不一定要第一列）的 Role 下拉選單，即使沒有選擇 Target 這個選項：圈圈應立刻消失，且之後都不再出現
- （不需要測試「重新上傳新檔案」情境——此面板不支援換檔案，設計文件已明確排除這個情境）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "fix: dismiss role-select tap-hint once any row is focused"
```

---

## Task 4: Drawer 第三段展開高度 54vh → 90vh

**Files:**
- Modify: `frontend/src/composables/useDrawerDrag.ts:1-15`

**Interfaces:**
- Consumes: 無（純常數調整）
- Produces: `getExpandedPx()` 回傳值改為視窗高度的 90%，供既有的 `expandedPx`、`heightPx`、`style`、`resolveTarget` 使用，型別與呼叫方式都不變。

- [ ] **Step 1: 更新頂部說明註解與 `getExpandedPx()` 的比例**

把：

```ts
/**
 * 抽屜有三個段落喔
 *   peeked (100px)    → 關閉的時候沒有完全關閉，還看得到title
 *   collapsed (280px) → 預設打開的高度，剛好能看到大部分的欄位
 *   expanded (54vh)   → 內容比較多時（e.g. dataTable）可以往上拉到更大
 */

// ─── 各段高度（px）──────────────────────────────────────────────
const PEEKED_PX = 100;
const COLLAPSED_PX = 280;
function getExpandedPx(): number {
  return Math.round(window.innerHeight * 0.54);
}
```

改成：

```ts
/**
 * 抽屜有三個段落喔
 *   peeked (100px)    → 關閉的時候沒有完全關閉，還看得到title
 *   collapsed (280px) → 預設打開的高度，剛好能看到大部分的欄位
 *   expanded (90vh)   → 內容比較多時（e.g. dataTable）可以往上拉到接近整頁
 */

// ─── 各段高度（px）──────────────────────────────────────────────
const PEEKED_PX = 100;
const COLLAPSED_PX = 280;
function getExpandedPx(): number {
  return Math.round(window.innerHeight * 0.9);
}
```

- [ ] **Step 2: 手動驗證**

在瀏覽器操作：
- 開啟 workflow 畫面，點選任一節點讓抽屜打開
- 把抽屜手把往上拖到底（或點擊手把讓它跳到最大段），確認高度接近整個視窗高度（約 90%，頂部留一點點空隙，不會整個貼齊螢幕最上緣）
- 確認拖曳到中間放開時，仍然會吸附回 peeked / collapsed / expanded 三段之一（原本的吸附邏輯不受影響）

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useDrawerDrag.ts
git commit -m "feat: expand drawer's third stage to 90vh"
```

## 實際實作差異

Task 4 實際做完的結果跟本節原始計畫差異很大，記錄如下。

### 1. 哪裡跟原計畫不一樣

- **原計畫**：把既有的 `expanded` 段從 54vh 直接改成 90vh（單純替換一個常數），只動 `useDrawerDrag.ts` 一個檔案。
- **實際結果**：drawer 變成四段式 —— `peeked`（100px）→ `collapsed`（280px）→ `expanded`（**保留 54vh，不變**）→ `full`（**新增，90vh**）。使用者可以從 `expanded` 繼續往上拖到 `full`；點擊 handle 在 `full` 時會縮回 `expanded`（54vh），而不是直接關到 `peeked`。
- 另外還動了計畫完全沒提到的 `frontend/src/components/workflow/WorkflowWorkspace.vue`：
  - 拿掉原本各自獨立、寫死在兩個 CSS class 裡的 `max-height`（`.options-drawer--expanded: 54vh` / `.options-drawer--full: 90vh`），改成單一固定的 `max-height: 90vh` 安全上限，直接寫在 `.options-drawer` 上，不再依 stage 切換 class。
  - 因此 `isExpanded` / `isFull` / `isDragging` 這幾個原本只為了驅動這兩個 class 存在的狀態，最後從 `useDrawerDrag()` 的回傳值裡整個移除。
- 過程中還連帶修正了 Task 2 / Task 3 完成後在 `DataTablePanel.vue` 裡新發現的問題（詳見「對其他 task 有沒有影響」）。

### 2. 為什麼要改

- **需求理解錯誤**：brainstorming 階段設計文件與本計畫都寫成「把 expanded 從 54vh 換成 90vh」，但套用後在瀏覽器實測時，使用者澄清實際想要的是「保留 54vh，額外新增一段可以繼續往上拉的 90vh」，而不是取代。
- **計畫疏漏（技術限制被漏看）**：第一次只照原計畫改 `useDrawerDrag.ts` 的比例並 commit 後，使用者實測回報「拉不到 90，且收合時會先跳到 90vh 才收起」。追查後發現 `WorkflowWorkspace.vue` 有一個計畫完全沒發現的第二個高度上限來源（獨立寫死的 CSS `max-height: 54vh`），跟 `useDrawerDrag.ts` 的 JS 高度計算是兩個各自維護、沒有同步的常數。這個 commit（`feat: expand drawer's third stage to 90vh` 的第一版）因此被 `git reset --hard` 撤銷重做。
- **後續執行 `/code-review` 又抓到新 bug**：改成四段式之後，`stage` 這個值只在放開手（`endDrag` 的 `requestAnimationFrame`）才更新，但拖曳中即時高度已經可以拉到 90vh，造成「CSS class 還沒切換、拖曳中途卡在 54vh 直到放開才彈到真正高度」的視覺 bug。第一輪修法是拖曳中強制套用 `full` 的 90vh 上限；後來使用者又要求新增「90vh 時點擊 handle 縮回 54vh」的互動，這個新收合動畫又會因為「目標值剛好等於新的 class 上限」而被瞬間夾住、失去平滑動畫——**發現更好的做法**：既然實際高度本來就完全由 JS 精確控制，兩段式 CSS 上限本身就是不必要的重複來源，於是直接合併成一個固定的 90vh 安全上限，從根本消除這整類「CSS 上限與 JS 高度不同步」的 bug，而不是繼續針對個別觸發情境打補丁。

### 3. 對其他 task 有沒有影響

- Task 1–3 都在 `DataTablePanel.vue`，Task 4 的核心改動在 `useDrawerDrag.ts` / `WorkflowWorkspace.vue`，檔案上沒有直接衝突。
- 但 Task 4 做完後跑 `/code-review`，在既有的 `DataTablePanel.vue`（Task 2、Task 3 的成果）裡額外抓到幾個問題並一併修掉，屬於「review 期間發現、回頭補強」而非重新變更 Task 2/3 的原始需求：
  - Task 3 新增的 tap-hint 判斷式補回 `!hasTarget`，修掉「已選 Target 但點擊提示圈圈又重新出現」的矛盾。
  - `role-select--attention` 灰邊框也補上 `!roleSelectTouched`，讓它跟提示圈圈重新綁在一起消失/出現。
  - Task 2 新增的 header 引導文字判斷式（`previewColumns.length > 0`）改用跟下方空狀態共用的 `columnsReady` computed，避免同一個條件兩處各寫一次。
- 過程中還額外發現一個**跟本計畫無關的既有問題**：Role/Target 選擇在使用者按下「繼續」之前只存在元件本地狀態，若在按繼續前切去別的節點，選擇會遺失。這個問題在本次計畫執行前就存在，使用者確認後明確排除在本次範圍外，已記錄到專案 memory，留待之後另外處理，不影響本計畫四個 task 的完成度。
