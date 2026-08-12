# 欄位對齊下拉選單 UX 修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正欄位對齊頁（`FieldMappingView.vue`）的下拉選單體驗：已被其他變數占用的欄位選項要在選單裡弱化顯示（仍可點擊選取），以及修正過長文字（論文變數名稱、已選欄位名稱）撐開表格、擠壓右側狀態欄的版面問題。

**Architecture:** `CustomSelect.vue` 的 `Option` 型別新增 `muted?: boolean` 旗標，選項標籤在 `muted` 為真時套灰階樣式（跟現有 `is-disabled` 共用色號，但保持可點擊）。`FieldMappingView.vue` 在 `optionsFor()` 組選項時，對「已被別的論文變數占用」的欄位同時給 `hint` 和 `muted: true`。表格版面問題的根因是 `.mapping-table` 沒有 `table-layout: fixed`，auto layout 下瀏覽器會用儲存格內文字的完整換算寬度去撐開欄位；改成 `table-layout: fixed` 並把兩個側欄的固定 px 寬度換成「比例寬 + px 下限」即可鎖死欄寬，同時維持隨視窗縮放的能力。左側論文變數名稱目前是行內排列、沒有截斷邏輯，需要包一層 flex 容器（比照既有 `.status-cell` 的寫法）讓 `.var-name` 能吃到明確寬度並套用 `text-overflow: ellipsis`。

**Tech Stack:** Vue 3 `<script setup>`、TypeScript、原生 CSS（無 CSS framework，`--color-*` 是專案自訂 CSS variables）。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-13-field-mapping-select-ux-design.md`
- `CustomSelect.vue` 是共用元件，同時被 `DataTablePanel.vue`、`SettingsPanel.vue`、`FeatureImportancePanel.vue` 使用，那些呼叫端目前都沒有傳 `hint`／`muted`——新增欄位一律選填，預設不啟用，不能影響那三個頁面現有行為
- 不動 `applySelection`/`optionsFor` 既有的搶欄位、鎖定等資料邏輯，只加一個新旗標
- 本專案前端沒有 vitest，一律用 `npm run type-check` + 人工瀏覽器驗證
- 每個 task 完成後都要跑 `npm run type-check` 確認沒有型別錯誤才能進下一步

---

### Task 1: CustomSelect — 新增選項弱化顯示能力

**Files:**
- Modify: `frontend/src/components/common/CustomSelect.vue:65`（`Option` 介面）
- Modify: `frontend/src/components/common/CustomSelect.vue:37-55`（選項 template）
- Modify: `frontend/src/components/common/CustomSelect.vue:413-416`（style，`.cs-option.is-disabled` 附近）

**Interfaces:**
- Consumes: 無（本 task 只改共用元件本身）
- Produces: `Option` 介面新增 `muted?: boolean`；選項傳入 `muted: true` 時，`<li class="cs-option">` 會帶上 `is-muted` class，供 Task 2 使用

- [ ] **Step 1: `Option` 介面加 `muted`**

找到 `frontend/src/components/common/CustomSelect.vue` 的（第 65 行）：

```ts
  interface Option { value: string, label: string, hint?: string, disabled?: boolean }
```

改成：

```ts
  interface Option { value: string, label: string, hint?: string, disabled?: boolean, muted?: boolean }
```

- [ ] **Step 2: 選項 template 加上 `is-muted` class binding**

找到（第 37-55 行）：

```html
        <li
          v-for="(opt, i) in options"
          :id="`${uid}-opt-${i}`"
          :key="opt.value"
          class="cs-option"
          :class="{
            'is-active': i === activeIndex,
            'is-selected': opt.value === modelValue,
            'is-disabled': opt.disabled,
          }"
          role="option"
          :aria-selected="opt.value === modelValue"
          :aria-disabled="opt.disabled || undefined"
          @mouseenter="activeIndex = i"
          @click="selectOption(opt)"
        >
          <span class="cs-option-label">{{ opt.label }}</span>
          <span v-if="opt.hint" class="cs-option-hint">{{ opt.hint }}</span>
        </li>
```

改成（`:class` 物件多一行 `'is-muted': opt.muted`，其餘不變）：

```html
        <li
          v-for="(opt, i) in options"
          :id="`${uid}-opt-${i}`"
          :key="opt.value"
          class="cs-option"
          :class="{
            'is-active': i === activeIndex,
            'is-selected': opt.value === modelValue,
            'is-disabled': opt.disabled,
            'is-muted': opt.muted,
          }"
          role="option"
          :aria-selected="opt.value === modelValue"
          :aria-disabled="opt.disabled || undefined"
          @mouseenter="activeIndex = i"
          @click="selectOption(opt)"
        >
          <span class="cs-option-label">{{ opt.label }}</span>
          <span v-if="opt.hint" class="cs-option-hint">{{ opt.hint }}</span>
        </li>
```

- [ ] **Step 3: 新增 `.is-muted` 樣式**

找到（第 413-416 行）：

```css
  .cs-option.is-disabled {
    color: #cbd5e1;
    cursor: not-allowed;
  }
```

改成（在後面新增 `.is-muted` 規則；不加 `cursor: not-allowed`，因為這個狀態仍然可以點擊選取）：

```css
  .cs-option.is-disabled {
    color: #cbd5e1;
    cursor: not-allowed;
  }

  /* 已被別的欄位占用，但仍可點擊選取（會把它搶過來）；跟 is-disabled 共用色號，語氣是「弱化」不是「不能用」 */
  .cs-option.is-muted .cs-option-label {
    color: #94a3b8;
  }
```

- [ ] **Step 4: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/common/CustomSelect.vue
git commit -m "feat: support muted option styling in CustomSelect"
```

---

### Task 2: FieldMappingView — 已占用欄位套用 muted

**Files:**
- Modify: `frontend/src/views/hub/FieldMappingView.vue:375-392`（`optionsFor`）

**Interfaces:**
- Consumes: Task 1 的 `Option.muted?: boolean`
- Produces: `optionsFor()` 回傳的每個選項在對應欄位「已被別的論文變數占用」時帶 `muted: true`，供畫面渲染時套用 Task 1 的樣式

- [ ] **Step 1: `optionsFor` 加上 `muted`**

找到 `frontend/src/views/hub/FieldMappingView.vue` 的（第 375-392 行）：

```ts
  function optionsFor (item: MappingItem) {
    const taken = new Map<string, string>()
    for (const other of items.value) {
      if (other.paper_variable !== item.paper_variable && other.matched_user_column) {
        taken.set(other.matched_user_column, other.paper_variable)
      }
    }
    const options = userColumns.value.map(column => ({
      value: column.name,
      label: column.name,
      hint: taken.has(column.name) ? `已對應至 ${taken.get(column.name)}` : undefined,
    }))
    // target 一定要有對應欄位，不提供「沒有這個變數」的選項
    if (!isTarget(item)) {
      options.push({ value: SKIP_VALUE, label: '資料表中沒有此變數', hint: undefined })
    }
    return options
  }
```

改成（`options` 的 map 多一個 `muted` 欄位；後面 `push` 的物件也要補上 `muted: false`，否則型別跟 map 出來的元素對不上）：

```ts
  function optionsFor (item: MappingItem) {
    const taken = new Map<string, string>()
    for (const other of items.value) {
      if (other.paper_variable !== item.paper_variable && other.matched_user_column) {
        taken.set(other.matched_user_column, other.paper_variable)
      }
    }
    const options = userColumns.value.map(column => ({
      value: column.name,
      label: column.name,
      hint: taken.has(column.name) ? `已對應至 ${taken.get(column.name)}` : undefined,
      muted: taken.has(column.name),
    }))
    // target 一定要有對應欄位，不提供「沒有這個變數」的選項
    if (!isTarget(item)) {
      options.push({ value: SKIP_VALUE, label: '資料表中沒有此變數', hint: undefined, muted: false })
    }
    return options
  }
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 3: 人工瀏覽器驗證**

開發模式啟動前端（若尚未啟動：`cd frontend && npm run dev`），走到任一專案的欄位對齊頁（`/hub/projects/:id/mapping`）。

Expected:
- 先把某個使用者欄位選給論文變數 A（該列變成「已確認」）
- 打開論文變數 B 的下拉選單，確認欄位 A 占用的那個選項文字變灰、下方仍看得到「已對應至 A」提示
- 點擊那個灰色選項，確認可以正常選取（選取後論文變數 A 那一列會變回「未對應」並閃一下，這是既有行為，不應被這次改動影響）
- 其餘沒被占用的選項顏色維持正常（黑色），選單本身目前選中的那項維持既有的琥珀色

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/hub/FieldMappingView.vue
git commit -m "feat: mute already-taken column options in field-mapping select"
```

---

### Task 3: FieldMappingView — 表格欄寬鎖定（table-layout: fixed + 比例寬）

**Files:**
- Modify: `frontend/src/views/hub/FieldMappingView.vue:989-1017`（style，`.mapping-table`、`.col-status`、`.col-col`）

**Interfaces:**
- Consumes: 無
- Produces: `.mapping-table` 的三欄欄寬被鎖死（`.col-col`／`.col-status` 比例寬+下限，`.col-var` 吃剩餘空間），供 Task 4 的文字截斷邏輯生效

- [ ] **Step 1: `.mapping-table` 加 `table-layout: fixed`**

找到（第 989-994 行）：

```css
  .mapping-table {
    width: 100%;
    min-width: 520px;
    border-collapse: collapse;
    font-size: 13px;
  }
```

改成：

```css
  .mapping-table {
    width: 100%;
    min-width: 520px;
    table-layout: fixed;
    border-collapse: collapse;
    font-size: 13px;
  }
```

- [ ] **Step 2: `.col-status`／`.col-col` 改成比例寬 + px 下限**

找到（第 1010-1017 行）：

```css
  /* 要放得下「待確認」標籤 + 勾勾按鈕，不然標籤會被擠到換行 */
  .col-status {
    width: 124px;
  }

  .col-col {
    width: 260px;
  }
```

改成（`min-width` 沿用原本的 px 值當下限，視窗夠寬時改用比例縮放；`.col-var` 不用另外設定，`table-layout: fixed` 底下沒宣告寬度的欄位會自動吃掉剩餘空間）：

```css
  /* 要放得下「待確認」標籤 + 勾勾按鈕，不然標籤會被擠到換行；
     比例寬讓視窗變寬時能跟著縮放，min-width 是原本的固定值，縮太窄時觸發 .mapping-scroll 的水平捲動 */
  .col-status {
    width: 18%;
    min-width: 124px;
  }

  .col-col {
    width: 38%;
    min-width: 260px;
  }
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤（純 CSS 改動，這步主要是確認沒有連帶弄壞 `<script>` 區塊）

- [ ] **Step 4: 人工瀏覽器驗證**

走到欄位對齊頁，瀏覽器開發者工具切換不同視窗寬度（或直接拖拉瀏覽器視窗）。

Expected:
- 視窗變寬時，「你的欄位」「狀態」兩欄會跟著等比例放大，不會停在原本的固定 px 大小
- 視窗縮到很窄時（小於三欄 min-width 總和），整張表出現水平捲動（`.mapping-scroll` 的 `overflow-x: auto`），文字不會被硬擠壓變形
- 狀態欄的「已確認」／「待確認」等標籤在任何寬度下都維持單行（`.status-chip` 本來就有 `white-space: nowrap`），不會被擠到換行

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/hub/FieldMappingView.vue
git commit -m "fix: lock field-mapping table column widths to stop text from squeezing status column"
```

---

### Task 4: FieldMappingView — 論文變數名稱截斷

**Files:**
- Modify: `frontend/src/views/hub/FieldMappingView.vue:56-81`（`col-var` 儲存格 template）
- Modify: `frontend/src/views/hub/FieldMappingView.vue:1019-1041`（style，`.target-badge`、`.var-name`、`.var-info-icon`、`.var-type`）

**Interfaces:**
- Consumes: Task 3 鎖死的欄寬（`.col-var` 的實際可用寬度）
- Produces: 無（UI 端末端行為，本 task 之後沒有其他 task 依賴它）

- [ ] **Step 1: `col-var` 儲存格包一層 flex 容器**

找到（第 56-81 行）：

```html
              <td class="col-var">
                <span
                  v-if="isTarget(item)"
                  aria-label="預測目標"
                  class="target-badge"
                  role="img"
                >★</span>
                <span class="var-name">{{ item.paper_variable }}</span>
                <v-tooltip
                  v-if="item.definition"
                  content-class="status-tooltip"
                  location="bottom"
                  max-width="240"
                  :text="item.definition"
                >
                  <template #activator="{ props }">
                    <v-icon
                      v-bind="props"
                      class="var-info-icon"
                      icon="mdi-information-outline"
                      size="14"
                    />
                  </template>
                </v-tooltip>
                <span class="var-type">{{ item.required_type || '型態未指定' }}</span>
              </td>
```

改成（`★` 徽章、變數名稱、info icon 包進 `.var-name-row`；`.var-name` 加原生 `title` 屬性顯示完整名稱；`.var-type` 維持在容器外、原本的獨立一行）：

```html
              <td class="col-var">
                <div class="var-name-row">
                  <span
                    v-if="isTarget(item)"
                    aria-label="預測目標"
                    class="target-badge"
                    role="img"
                  >★</span>
                  <span class="var-name" :title="item.paper_variable">{{ item.paper_variable }}</span>
                  <v-tooltip
                    v-if="item.definition"
                    content-class="status-tooltip"
                    location="bottom"
                    max-width="240"
                    :text="item.definition"
                  >
                    <template #activator="{ props }">
                      <v-icon
                        v-bind="props"
                        class="var-info-icon"
                        icon="mdi-information-outline"
                        size="14"
                      />
                    </template>
                  </v-tooltip>
                </div>
                <span class="var-type">{{ item.required_type || '型態未指定' }}</span>
              </td>
```

- [ ] **Step 2: 新增 `.var-name-row`，`.var-name` 加截斷樣式**

找到（第 1019-1041 行）：

```css
  .target-badge {
    color: #d97706;
    margin-right: 4px;
  }

  .var-name {
    font-weight: 600;
    color: var(--color-ink);
  }

  .var-info-icon {
    margin-left: 4px;
    color: #94a3b8;
    cursor: help;
    vertical-align: middle;
  }

  .var-type {
    display: block;
    margin-top: 2px;
    font-size: 11px;
    color: #94a3b8;
  }
```

改成（新增 `.var-name-row` 用 `gap` 統一控制間距，`.target-badge`／`.var-info-icon` 原本各自的 `margin` 移除、避免跟 `gap` 重複疊加；`.var-name` 加 `flex` 相關屬性讓它能吃到明確寬度並截斷）：

```css
  .var-name-row {
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
  }

  .target-badge {
    color: #d97706;
  }

  .var-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 600;
    color: var(--color-ink);
  }

  .var-info-icon {
    flex-shrink: 0;
    color: #94a3b8;
    cursor: help;
    vertical-align: middle;
  }

  .var-type {
    display: block;
    margin-top: 2px;
    font-size: 11px;
    color: #94a3b8;
  }
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 4: 人工瀏覽器驗證**

用一個論文變數名稱很長（例如超過 25 個字元，可以先手動把某個框架的 `workflow_json.features[].name` 改長，或找一個原本名稱就很長的框架）的專案，走到欄位對齊頁。

Expected:
- 過長的論文變數名稱顯示成「...」結尾，沒有把該列撐開、右側狀態欄維持正常寬度不換行
- 滑鼠移到被截斷的變數名稱上，看得到瀏覽器原生 tooltip 顯示完整名稱
- 有 `★` 徽章的目標變數（target）一樣正確截斷，徽章、文字、info icon（若有定義）三者間距看起來正常，沒有明顯過寬或黏在一起
- 有 `item.definition` 的變數，info icon 仍然照舊顯示、hover 後跳出定義 tooltip，功能不受影響

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/hub/FieldMappingView.vue
git commit -m "fix: truncate long paper variable names instead of squeezing the status column"
```

---

### Task 5: 綜合回歸驗證

**Files:** 無（本 task 不改程式碼，純驗證 Task 1-4 合起來的完整行為）

**Interfaces:**
- Consumes: Task 1-4 的全部改動

- [ ] **Step 1: 完整情境人工測試**

在欄位對齊頁上，依序操作並確認：

1. 用一個變數名稱長、資料集欄位名稱也長的專案，確認左側變數名稱跟右側下拉選單收合狀態的已選欄位名稱都正確截斷（各自顯示「...」），狀態欄全程維持正常寬度、標籤不換行
2. 把某欄位選給變數 A，再打開變數 B 的下拉選單：該欄位選項文字變灰但仍可點擊；點下去後變數 A 那一列變回「未對應」並閃黃色（既有行為）
3. 縮放瀏覽器視窗寬度，確認「你的欄位」「狀態」兩欄比例縮放、縮到很窄時整張表水平捲動
4. 完整跑一次既有流程確認沒有回歸：自動配對載入 → 用下拉選單手動改幾個對應 → 點「全部確認」→ AI 對話框送一句修正訊息 → 按「確認並執行」進到下一步（`/workflow?project=...`）

Expected: 以上四點全部符合預期，且過程中 console 沒有跳出新的錯誤或警告

- [ ] **Step 2: 最終型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

（本 task 無程式碼變更，不需要 commit）
