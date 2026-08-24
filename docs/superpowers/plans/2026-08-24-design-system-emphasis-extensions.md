# 設計系統擴充：資料強調字重、AI 按鈕、驗證方式 step Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 brainstorming 定案的三個設計系統擴充（700 字重、AI 按鈕變體、驗證方式 step 視覺）落地到程式碼與 DESIGN_SYSTEM.md。

**Architecture:** 三個題目互相獨立，各自是「改 CSS token/class + 補文件」的範圍，不涉及新資料流或新元件架構，唯一新增的共用元件邏輯是 `AppButton.vue` 的 `ai` 變體。

**Tech Stack:** Vue 3 `<script setup>`、Vuetify 4 + Tailwind 4（CSS 變數橋接）、無前端自動化測試套件（本專案現況，見下方驗證方式說明）。

**Spec:** [docs/superpowers/specs/2026-08-24-design-system-emphasis-extensions-design.md](../specs/2026-08-24-design-system-emphasis-extensions-design.md)

## Global Constraints

- 色值一律引用 token,不寫死 hex（DESIGN_SYSTEM.md §9.2）。
- hover 一律包在 `@media (hover: hover) and (pointer: fine)` 內（§9.2）。
- 動畫用 §6.1 既有的 `--dur-*`/`--ease-*` token,不自行定義新的時長/緩動數值。
- 字重只允許 400/500,例外只有兩處：AI 對話氣泡 `<strong>` 與這次新增的「資料強調」700（§3）。
- 每個檔案改完跑 `npm run type-check` 跟 `npx eslint <改動的檔案>`,兩者都要乾淨才算完成一個 task。
- **本專案前端沒有自動化測試套件**（`package.json` 沒有 vitest/jest,`CLAUDE.md` 也明講「沒有自動化測試套件」）。因此每個 task 的「測試」步驟是：type-check + lint + 啟動 dev server 用瀏覽器實際看畫面（比照 DESIGN_SYSTEM.md §9.2「改完開 `/style-guide` 看一遍,再看實際頁面」的既有驗收方式），不是傳統的 TDD 紅燈/綠燈循環。

---

## 檔案總覽

| 檔案 | 改動內容 |
|---|---|
| `docs/DESIGN_SYSTEM.md` | §3 字重表新增 700 列、補例外說明；§7.4 表頭字重改 Bold；§7.1 按鈕表新增 `ai` 變體 |
| `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue` | `.cm-header`/`.cm-insight-header` 600→700；`.cm-insight-btn` 三顆按鈕改用 `<AppButton variant="ai">` |
| `frontend/src/views/ResultsPage.vue` | `.metric-title` 700→500；`.imbalance-badge` 600→500 |
| `frontend/src/components/workflow/nodePanel/SettingsPanel.vue` | Step 3 驗證方式的 CSS 重寫（容器、自訂 radio、hover、連接線），template 不變 |
| `frontend/src/components/ui/AppButton.vue` | 新增 `ai` variant：漸層底色、固定圖示插槽行為不變、loading 改用光帶掃過（不隱藏內容） |

---

## Task 1：字重 — DESIGN_SYSTEM.md 補規範 + 修正既有違規

**Files:**
- Modify: `docs/DESIGN_SYSTEM.md:144`（AI 氣泡例外說明段落後）
- Modify: `docs/DESIGN_SYSTEM.md:146-154`（§3 字重表）
- Modify: `docs/DESIGN_SYSTEM.md:382`（§7.4 表頭描述）
- Modify: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue:635-643`（`.cm-header`）
- Modify: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue:781-785`（`.cm-insight-header`）
- Modify: `frontend/src/views/ResultsPage.vue:493-498`（`.metric-title`）
- Modify: `frontend/src/views/ResultsPage.vue:536-544`（`.imbalance-badge`）

**Interfaces:** 無（純 CSS 數值調整，不影響其他元件的 props/emit）。

- [ ] **Step 1：更新 DESIGN_SYSTEM.md §3 字重表**

把：

```markdown
| 角色 | 大小 | 字重 |
|---|---|---|
| 展示型數字 | 32px | 500 |
| 頁面標題 h1 | 22px | 500 |
| 區塊標題 h2 | 18px | 500 |
| 小標 h3 | 15–16px | 500 |
| 內文 | 14px | 400 |
| 次要/說明 | 13px | 400 |
| 標籤/徽章 | 11–12px | 400–500 |
```

改成：

```markdown
| 角色 | 大小 | 字重 |
|---|---|---|
| 展示型數字 | 32px | 700 |
| 頁面標題 h1 | 22px | 500 |
| 區塊標題 h2 | 18px | 500 |
| 小標 h3 | 15–16px | 500 |
| 內文 | 14px | 400 |
| 次要/說明 | 13px | 400 |
| 標籤/徽章 | 11–12px | 400–500 |
| 表格最佳值/重點結果 | 隨內文 | 700 |
| 資料表格表頭 | 12px | 700 |
```

- [ ] **Step 2：在展示型數字說明後補一段新例外說明**

在「展示型數字…它不是標題,不要拿來放文字。」這行之後、「一律句首大寫」這行之前插入：

```markdown
- **700 是第二個合法的字重例外，限定「資料強調」**：展示型數字、資料表格裡的最佳值/重點結果、資料表格表頭。跟 AI 對話氣泡的 700 例外互相獨立——一個標示「這是重點數據」，一個標示「AI 在強調語氣」，不要合併成同一條規則。除了這兩處，字重維持 400/500。
```

- [ ] **Step 3：更新 §7.4 表頭字重描述**

把第 382 行：

```markdown
- 表頭:`--color-surface-alt` 底,`--color-ink-soft` 文字,12px,Medium。
```

改成：

```markdown
- 表頭:`--color-surface-alt` 底,`--color-ink-soft` 文字,12px,Bold(700,見 §3 資料強調例外)。
```

- [ ] **Step 4：修正 `ConfusionMatrixPanel.vue` 的 `.cm-header`**

`.cm-header` 是表格表頭,依新規範升到 700：

```css
  .cm-header {
    padding: 10px 14px;
    font-size: 12px;
    font-weight: 700;
    color: var(--color-ink-soft);
    white-space: nowrap;
    text-align: left;
    border-bottom: 1px solid var(--color-border);
  }
```

- [ ] **Step 5：修正 `ConfusionMatrixPanel.vue` 的 `.cm-insight-header`**

這是「AI 解讀」區塊的小標題，不是資料強調也不是表格表頭，不符合新規範，降回 500：

```css
  .cm-insight-header {
    font-size: 12px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }
```

- [ ] **Step 6：修正 `ResultsPage.vue` 的 `.metric-title`**

`.metric-title` 是統計卡片的小標題文字（例如「準確率」），不是數字本身，不符合新規範，降回 500：

```css
  .metric-title {
    margin: 0;
    font-size: 12px;
    font-weight: 500;
    color: var(--color-text);
  }
```

- [ ] **Step 7：修正 `ResultsPage.vue` 的 `.imbalance-badge`**

這是徽章不是資料強調，降回 500：

```css
  .imbalance-badge {
    flex-shrink: 0;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    background: var(--brand-soft);
  }
```

- [ ] **Step 8：確認其餘既有 700 用法不用改**

跑一次確認，不需要改任何東西，純粹核對：

```bash
grep -n "font-weight: 700" frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue frontend/src/views/ResultsPage.vue
```

預期只剩下：`.cm-cell--diagonal`、`.cm-row--lowest .cm-cell`（表格最佳值）、`.cm-header`（表頭，Step 4 剛改的）、`.metric-value`、`.insight-title`（展示型數字）、`.result-table th`（表頭）、`.model-name`、`.score-best`（表格強調值）。這些全部符合新規範，不需要動。

- [ ] **Step 9：驗證**

```bash
cd frontend
npm run type-check
npx eslint src/components/workflow/nodePanel/ConfusionMatrixPanel.vue src/views/ResultsPage.vue
```

兩個指令都要沒有新增的錯誤（既有跟這次改動無關的 lint 錯誤不用管，見 spec 背景說明）。接著啟動 dev server（`npm run dev`），打開一個有 workflow 執行結果的專案，看 Confusion Matrix 的表頭跟 Results Page 的統計卡標題/不平衡徽章字重看起來正常（表頭偏粗、卡片小標題偏細）。

- [ ] **Step 10：Commit**

```bash
git add docs/DESIGN_SYSTEM.md frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue frontend/src/views/ResultsPage.vue
git commit -m "style: promote 700 to a documented data-emphasis font weight"
```

---

## Task 2：驗證方式 step 視覺重寫

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/SettingsPanel.vue:750-776`（CSS only，template 不變）

**Interfaces:** 無（純 CSS，template 結構、`method.value`/`localValidation` 等既有邏輯完全不動）。

- [ ] **Step 1：確認 template 現狀不用改**

`SettingsPanel.vue` Step 3 的 template（第 205-260 行左右）用的 class 名稱是 `.validation-methods`、`.validation-method`、`.validation-method__radio`、`.validation-method__params`，這些 class 名稱在這個 task 裡維持不變，只重寫對應的 CSS。確認一下目前這幾個 class 確實存在：

```bash
grep -n "validation-method" frontend/src/components/workflow/nodePanel/SettingsPanel.vue
```

- [ ] **Step 2：改寫 `.validation-methods`，加上容器樣式**

找到（約第 750 行）：

```css
  .validation-methods {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
```

改成：

```css
  .validation-methods {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 6px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }
```

- [ ] **Step 3：`.validation-method` 加上 hover 回饋**

找到（約第 756 行）：

```css
  .validation-method {
    padding: 8px 10px;
    border-radius: var(--radius-sm);
  }
```

改成：

```css
  .validation-method {
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    transition: background var(--dur-fast);
  }

  @media (hover: hover) and (pointer: fine) {
    .validation-method:hover {
      background: var(--color-surface-alt);
    }
  }
```

- [ ] **Step 4：`.validation-method__radio` 新增自訂 radio 樣式**

找到（約第 761 行）：

```css
  .validation-method__radio {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--color-ink);
    cursor: pointer;
  }
```

在它後面（保留原本這段不動）新增：

```css
  .validation-method__radio input[type="radio"] {
    appearance: none;
    width: 15px;
    height: 15px;
    margin: 0;
    flex-shrink: 0;
    border-radius: 50%;
    border: 1.5px solid var(--color-border-strong);
    position: relative;
    cursor: pointer;
    transition: border-color var(--dur-fast);
  }

  .validation-method__radio input[type="radio"]:checked {
    border-color: var(--step-color);
  }

  .validation-method__radio input[type="radio"]:checked::after {
    content: "";
    position: absolute;
    inset: 3px;
    border-radius: 50%;
    background: var(--step-color);
  }
```

`--step-color` 已經由 template 的 `:style="{ '--step-color': ... }"` 掛在 `.step-body` 上（Step 3 對應 `var(--color-node-evaluate)`），這裡直接用不用另外定義。

- [ ] **Step 5：`.validation-method__params` 改成連接線樣式**

找到（約第 770 行）：

```css
  .validation-method__params {
    margin-top: 8px;
    margin-left: 24px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
```

改成：

```css
  .validation-method__params {
    margin: 8px 0 4px 33px;
    padding-left: 16px;
    border-left: 1.5px solid color-mix(in oklab, var(--step-color) 35%, transparent);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
```

`33px` 是對齊選項文字左緣算出來的值（容器 padding 6px + row padding-left 10px + radio 寬度 15px + radio 與文字的 gap 8px 之類的累加值，是這次 brainstorming 反覆比較「對齊圓點」跟「對齊文字」後，選中的「對齊文字」版本）。

- [ ] **Step 6：驗證**

```bash
cd frontend
npm run type-check
npx eslint src/components/workflow/nodePanel/SettingsPanel.vue
```

啟動 dev server，開一個 workflow，進到 Settings 節點的 Step 3（驗證方式）：確認容器有邊框跟圓角、滑過每個選項有淺灰底、選中的選項圓點變成玫瑰色（evaluate 分類色）、選中「Cross validation」時下方參數區有一條細線接住上面那行文字的左緣。

- [ ] **Step 7：Commit**

```bash
git add frontend/src/components/workflow/nodePanel/SettingsPanel.vue
git commit -m "style: give the validation method step a designed radio list"
```

---

## Task 3：`AppButton` 新增 `ai` 變體

**Files:**
- Modify: `frontend/src/components/ui/AppButton.vue`
- Modify: `docs/DESIGN_SYSTEM.md:345-350`（§7.1 按鈕表）

**Interfaces:**
- Produces: `AppButton` 的 `variant` prop 新增合法值 `'ai'`（型別 `'primary' | 'secondary' | 'ghost' | 'danger' | 'ai'`）。既有的 `loading`、`disabled`、`iconOnly`、`type` prop 行為不變；`variant="ai"` 搭配 `loading` 時，內容**不會**被隱藏（跟其他變體的 loading 行為不同，見下）。Task 4 會消費這個新 variant。

- [ ] **Step 1：更新 `variant` prop 型別**

修改 `<script setup>` 區塊：

```typescript
  withDefaults(defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'ai'
    type?: 'button' | 'submit' | 'reset'
    disabled?: boolean
    loading?: boolean
    iconOnly?: boolean
  }>(), {
    variant: 'primary',
    type: 'button',
    disabled: false,
    loading: false,
    iconOnly: false,
  })
```

- [ ] **Step 2：調整 template，讓 `ai` 變體的 loading 不隱藏內容**

把：

```html
<template>
  <button
    ref="root"
    class="app-btn"
    :class="[`app-btn--${variant}`, { 'app-btn--icon-only': iconOnly }]"
    :disabled="disabled || loading"
    :type="type"
  >
    <span v-if="loading" aria-hidden="true" class="app-btn-spinner" />
    <span class="app-btn-body" :class="{ 'app-btn-body--loading': loading }">
      <slot />
    </span>
  </button>
</template>
```

改成：

```html
<template>
  <button
    ref="root"
    class="app-btn"
    :class="[
      `app-btn--${variant}`,
      {
        'app-btn--icon-only': iconOnly,
        'app-btn--ai-loading': loading && variant === 'ai',
      },
    ]"
    :disabled="disabled || loading"
    :type="type"
  >
    <span v-if="loading && variant !== 'ai'" aria-hidden="true" class="app-btn-spinner" />
    <span class="app-btn-body" :class="{ 'app-btn-body--loading': loading && variant !== 'ai' }">
      <slot />
    </span>
  </button>
</template>
```

- [ ] **Step 3：新增 `.app-btn--ai` 底色**

在 `.app-btn--danger` 規則後面新增：

```css
  .app-btn--ai {
    background: linear-gradient(100deg, var(--color-ink-vivid) 0%, var(--color-ink-strong) 100%);
    color: var(--color-inverted);
  }
```

- [ ] **Step 4：新增 `ai` 的 hover，放進既有 hover media block**

在 `@media (hover: hover) and (pointer: fine)` 區塊裡、`.app-btn--danger:hover` 規則後面新增：

```css
    .app-btn--ai:hover:not(:disabled) {
      background: linear-gradient(
        100deg,
        color-mix(in oklab, var(--color-ink-vivid) 88%, white) 0%,
        color-mix(in oklab, var(--color-ink-strong) 88%, white) 100%
      );
    }
```

- [ ] **Step 5：新增 loading 光帶動畫**

在 `.app-btn-spinner` 規則跟它的 `@keyframes app-btn-spin` 之間或之後（不要刪掉既有的 spinner，其他變體還在用），新增：

```css
  .app-btn--ai-loading {
    position: relative;
    overflow: hidden;
  }

  .app-btn--ai-loading::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
      100deg,
      transparent 20%,
      color-mix(in oklab, var(--color-inverted) 16%, transparent) 50%,
      transparent 80%
    );
    background-size: 260% 100%;
    animation: app-btn-ai-sweep 2.4s linear infinite;
  }

  @keyframes app-btn-ai-sweep {
    from { background-position: 140% 0; }
    to { background-position: -140% 0; }
  }
```

- [ ] **Step 6：更新 DESIGN_SYSTEM.md §7.1 按鈕表**

把：

```markdown
| 變體 | 底色 | 文字 | 用途 |
|---|---|---|---|
| primary | `--color-ink` | 白 | 主要動作(每個畫面最多一個) |
| secondary | `--color-surface` + `--color-border` inset 邊 | `--color-ink` | 次要動作 |
| ghost | 透明 | `--color-ink-soft` | 輕量動作(略過、取消) |
| danger | `--color-error-bg` | `--color-error-text` | 破壞性動作(移除對應) |
```

改成：

```markdown
| 變體 | 底色 | 文字 | 用途 |
|---|---|---|---|
| primary | `--color-ink` | 白 | 主要動作(每個畫面最多一個) |
| secondary | `--color-surface` + `--color-border` inset 邊 | `--color-ink` | 次要動作 |
| ghost | 透明 | `--color-ink-soft` | 輕量動作(略過、取消) |
| danger | `--color-error-bg` | `--color-error-text` | 破壞性動作(移除對應) |
| ai | `linear-gradient(100deg, --color-ink-vivid, --color-ink-strong)` | `--color-inverted` | 觸發 AI 運算的動作,固定帶 `mdi-shimmer` 圖示。只用在明確的 AI 觸發點,不要為了好看套用在一般按鈕上 |
```

在表格後面（`- **主次關係會隨流程階段改變。**` 那段之後）新增一段：

```markdown
- **`ai` 變體的 loading 不隱藏內容。** 其餘變體 loading 時內容 `visibility: hidden`、置中疊一個圓圈 spinner；`ai` 變體反過來，圖示跟文字維持可見，改成一道低透明度（16%）的光帶斜向掃過底色（2.4s，寬版、慢速）——AI 按鈕的圖示本身是「這是 AI 操作」的語意信號，loading 時蓋掉會失去意義。這個決定是反覆比較過旋轉邊框、公轉光點、脈動光暈、色輪旋轉等做法後定案的,不要回頭嘗試那些方向（見對應 spec 的完整比較過程）。
```

- [ ] **Step 7：驗證**

```bash
cd frontend
npm run type-check
npx eslint src/components/ui/AppButton.vue
```

啟動 dev server，開 `/style-guide`（dev 模式路由），暫時加一個 `<AppButton variant="ai">AI 解讀</AppButton>` 跟 `<AppButton variant="ai" loading>AI 解讀</AppButton>` 看外觀跟 loading 動畫是否符合預期，看完把暫時加的測試片段移除（`/style-guide` 正式收錄新按鈕變體不在這次範圍內）。

- [ ] **Step 8：Commit**

```bash
git add frontend/src/components/ui/AppButton.vue docs/DESIGN_SYSTEM.md
git commit -m "feat(ui): add ai variant to AppButton"
```

---

## Task 4：`ConfusionMatrixPanel.vue` 換用 `AppButton variant="ai"`

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`

**Interfaces:**
- Consumes: Task 3 產出的 `AppButton` `variant="ai"`（`<AppButton variant="ai" :disabled="...">`，不接 `:loading`，理由見 Step 3）。

- [ ] **Step 1：確認 `AppButton` 已經被引入**

```bash
grep -n "AppButton" frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
```

如果沒有 import,在 `<script setup>` 裡加：

```typescript
import AppButton from '@/components/ui/AppButton.vue'
```

- [ ] **Step 2：找到三顆自刻按鈕**

```bash
grep -n "cm-insight-btn" frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
```

會看到三處（重試 / 重新生成 / AI 解讀），大致長這樣：

```html
<button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">重試</button>
```

```html
<button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">重新生成</button>
```

```html
<button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">AI 解讀</button>
```

- [ ] **Step 3：三顆都換成 `AppButton`，並加上 spec 規定的固定圖示**

spec 規定 `ai` 變體「固定帶 `mdi-shimmer` 圖示」，`AppButton` 本身不內建圖示（圖示由呼叫端透過 slot 傳入，比照 `ProjectsView.vue` 的 `<AppButton variant="primary"><v-icon icon="mdi-folder-plus-outline" size="17" />新專案</AppButton>` 這種既有寫法），所以這裡要在文字前面加 `<v-icon icon="mdi-shimmer" size="14" />`。分別改成：

```html
<AppButton :disabled="!props.projectId" variant="ai" @click="generateTabInsight">
  <v-icon icon="mdi-shimmer" size="14" />
  重試
</AppButton>
```

```html
<AppButton :disabled="!props.projectId" variant="ai" @click="generateTabInsight">
  <v-icon icon="mdi-shimmer" size="14" />
  重新生成
</AppButton>
```

```html
<AppButton :disabled="!props.projectId" variant="ai" @click="generateTabInsight">
  <v-icon icon="mdi-shimmer" size="14" />
  AI 解讀
</AppButton>
```

不用補 `:loading` prop。元件裡確實有 `isCurrentTabInsightLoading` 這個 ref，但目前的 template 結構是「生成中用 `v-if="isCurrentTabInsightLoading"` 顯示一段純文字『生成中...』，三顆按鈕分別在 `v-else-if`/`v-else` 分支裡」——生成中的時候三顆按鈕本來就都不會被渲染出來，不會跟 loading 狀態同時出現，所以沒有需要接 `:loading` 的情境。把「生成中」改成讓按鈕本身用 `loading` 狀態呈現（而不是換成一段文字）是另一個題目，不在這次範圍內，這裡只做 Step 3 的變體替換。

- [ ] **Step 4：移除不再使用的 `.cm-insight-btn` CSS**

找到並整段刪除（約在 `.cm-insight-error` 之後）：

```css
  .cm-insight-btn {
    align-self: flex-start;
    padding: 7px 14px;
    border-radius: var(--radius-sm);
    border: 1px solid color-mix(in oklab, var(--color-ink) 35%, transparent);
    background: var(--color-ink);
    color: var(--color-inverted);
    font-size: 13px;
    cursor: pointer;
  }
```

- [ ] **Step 5：驗證**

```bash
cd frontend
npm run type-check
npx eslint src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
```

啟動 dev server，開一個有結果的 workflow，切到 Confusion Matrix 分頁，確認「重試」「重新生成」「AI 解讀」三顆按鈕都變成 F 漸層底色 + shimmer 圖示的樣子。光帶 loading 動畫目前沒有觸發點（見 Step 3 說明），這裡不用驗證動畫本身，Task 3 的 Step 7 已經在 `/style-guide` 驗證過。

- [ ] **Step 6：Commit**

```bash
git add frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
git commit -m "refactor: swap ConfusionMatrixPanel insight buttons to AppButton ai variant"
```
