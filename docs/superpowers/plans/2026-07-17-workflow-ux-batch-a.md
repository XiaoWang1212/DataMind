# Workflow UX 批次 A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 三個互不相干的 Workflow builder UI 小修正：Settings 步驟按鈕（上一步／下一步／執行）、Settings 模型列對齊、模型節點停用點選。

**Architecture:** 純前端 Vue 3 改動。三處各自獨立、不共用狀態：Settings 面板按鈕邏輯全在 `SettingsPanel.vue` 內（父層與 workflow 狀態機不動）；模型列對齊是純 CSS；模型節點停用點選是「父層守門 + 節點旗標 + 游標樣式」三點小改。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript、Vuetify、`@vue-flow/core`、Vite。

## Global Constraints

- **無自動測試**：本 repo 沒有前端測試套件。每個 task 的驗證方式一律為 `npm run build`（vue-tsc 型別檢查）＋ `npm run lint`（eslint），再加 `npm run dev` 手動操作確認。以上指令都從 `frontend/` 執行。
- **使用者可見文字用繁體中文**（本專案慣例）。
- **不碰 workflow 狀態機**：`continueWorkflow` / `nodeStatuses` / `pausedAtNodeId` / `dataTableApplied` 一律不動——跨節點的「上一步＋下游重置」屬後續批次。
- **Commit 前必須先取得使用者明確確認**（不自動 commit）。commit 訊息一行、不加 `Co-Authored-By` trailer、不引用任何私人筆記或其編號。

---

### Task 1: Settings 步驟按鈕改為 上一步／下一步／執行

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/SettingsPanel.vue`（footer 模板 206-216 行、`<script setup>` 尾段、`<style>` footer 區）

**Interfaces:**
- Consumes: 既有 `currentStep` ref（0..3）、`props.models`、`emit('continue')`、常數 `STEPS`（長度 4）。
- Produces: 無新增對外介面。父層仍只在最後一步收到 `continue` 事件，簽章不變。

- [ ] **Step 1: 在 `<script setup>` 加入按鈕邏輯**

在 `SettingsPanel.vue` 的 `const currentStep = ref(0)`（第 245 行附近）之後、`watch(currentStep, …)` 之前，加入：

```ts
  const LAST_STEP = STEPS.length - 1

  const primaryLabel = computed(() => (currentStep.value < LAST_STEP ? '下一步' : '執行'))
  const isPrimaryDisabled = computed(() => currentStep.value === LAST_STEP && props.models.length === 0)

  function handlePrimary (): void {
    if (currentStep.value < LAST_STEP) {
      currentStep.value += 1
    } else {
      emit('continue')
    }
  }
```

（`computed` 已在第 222 行 import，不需再加 import。）

- [ ] **Step 2: 改寫 footer 模板**

把第 206-216 行的 `.settings-footer` 整塊：

```html
    <div class="settings-footer">
      <button
        class="btn-continue"
        :class="{ 'btn-continue--disabled': props.models.length === 0 }"
        :disabled="props.models.length === 0"
        type="button"
        @click="emit('continue')"
      >
        繼續
      </button>
    </div>
```

換成：

```html
    <div class="settings-footer">
      <button
        v-if="currentStep > 0"
        class="btn-back"
        type="button"
        @click="currentStep -= 1"
      >
        上一步
      </button>
      <button
        class="btn-continue"
        :class="{ 'btn-continue--disabled': isPrimaryDisabled }"
        :disabled="isPrimaryDisabled"
        type="button"
        @click="handlePrimary"
      >
        {{ primaryLabel }}
      </button>
    </div>
```

- [ ] **Step 3: 加入「上一步」按鈕樣式**

在 `<style scoped>` 的 `.btn-continue--disabled { … }`（檔尾，第 777-780 行附近）之後加入：

```css
  .btn-back {
    margin-right: auto;
    min-width: 88px;
    padding: 10px 14px;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    background: #fff;
    color: #475569;
    font-size: 13px;
    cursor: pointer;
  }

  .btn-back:hover {
    background: #f1f5f9;
  }
```

`margin-right: auto` 讓「上一步」被推到左側、主按鈕維持在右側（`.settings-footer` 仍是 `justify-content: flex-end`）；「上一步」不存在時主按鈕自然靠右。

- [ ] **Step 4: 型別檢查 + lint**

Run（從 `frontend/`）：`npm run build && npm run lint`
Expected: build 與 lint 皆通過，無新錯誤。

- [ ] **Step 5: 手動驗證**

Run：`npm run dev`，開啟 workflow → 點 Settings 節點。逐一確認：
- 第 1 步（前處理）：**沒有**「上一步」；主按鈕顯示「下一步」，按了切到第 2 步、不啟動 workflow。
- 第 2、3 步：出現「上一步」（按了往回切分頁）；主按鈕「下一步」。
- 第 4 步（信賴區間）：主按鈕顯示「執行」；無模型時 disabled（灰色不可按），有模型時按下去啟動 workflow（與改動前行為一致）。

- [ ] **Step 6: Commit（先問使用者）**

先向使用者說明將 commit `SettingsPanel.vue`、取得確認後：

```bash
git add frontend/src/components/workflow/nodePanel/SettingsPanel.vue
git commit -m "feat: Settings 步驟按鈕改為上一步/下一步/執行"
```

---

### Task 2: Settings 模型列 icon 與名稱垂直置中對齊

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/SettingsPanel.vue`（模型列模板第 166 行、`<style>` 第 538-546 行）

**Interfaces:**
- Consumes: 既有 `.item-head` / `.item-idx--dot` 樣式。
- Produces: 無。

- [ ] **Step 1: 模型列改用置中的 `.item-head`**

把模型列的第 166 行：

```html
          <div class="item-head item-head--top">
```

改為（移除 `item-head--top` modifier）：

```html
          <div class="item-head">
```

（同一 `item-row` 內第 167 行的 `<span class="item-idx item-idx--dot" />` 維持不動。）

- [ ] **Step 2: 刪除只服務 `item-head--top` 的 CSS**

刪掉 `<style scoped>` 中第 538-546 行這兩塊（含註解）：

```css
  /* 模型卡片：名稱換行時，圓圈與叉叉維持在最上面一行對齊 */
  .item-head--top {
    align-items: flex-start;
  }

  /* 圓圈(18px)與叉叉(22px)高度不同，微調上緣讓兩者中線對齊名稱首行 */
  .item-head--top .item-idx {
    margin-top: 2px;
  }
```

刪除後 `.item-head`（`align-items: center`，第 532-536 行）會同時套用到前處理／特徵工程／模型三種列。

- [ ] **Step 3: 型別檢查 + lint**

Run（從 `frontend/`）：`npm run build && npm run lint`
Expected: 皆通過。並確認全檔已無 `item-head--top` 殘留：`grep -n "item-head--top" frontend/src/components/workflow/nodePanel/SettingsPanel.vue` 應無輸出。

- [ ] **Step 4: 手動驗證**

`npm run dev` → Settings 第 3 步（模型），新增一個模型。確認圓點與模型名稱在單行時垂直置中（不再偏低）。

- [ ] **Step 5: Commit（先問使用者）**

取得確認後：

```bash
git add frontend/src/components/workflow/nodePanel/SettingsPanel.vue
git commit -m "fix: Settings 模型列 icon 與名稱垂直置中對齊"
```

---

### Task 3: 模型節點停用點選（不開面板、游標非可互動）

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue:255-262`（`handleSelectNode`）
- Modify: `frontend/src/composables/workflow/useWorkflowNodes.ts:58-74`（`canvasNodes` computed 的 data 注入）
- Modify: `frontend/src/components/workflow/IconNode.vue`（模板 wrap class、`<script setup>` computed、`<style>`）

**Interfaces:**
- Consumes: 既有 `selectedNodeId`、`closeMenu()`、`expandDrawer()`（WorkflowWorkspace）；`node.id`（useWorkflowNodes）；`props.data`（IconNode）。
- Produces: 節點 `data` 新增布林欄位 `nonInteractive`，由 `IconNode.vue` 讀取。

- [ ] **Step 1: 父層守門 — 模型節點點擊不開面板**

`WorkflowWorkspace.vue` 的 `handleSelectNode`（第 255 行）改為在最前面加守門：

```ts
  function handleSelectNode (nodeId: string): void {
    if (nodeId.startsWith('model-')) return
    if (selectedNodeId.value === nodeId) {
      closeMenu()
      return
    }
    selectedNodeId.value = nodeId
    expandDrawer()
  }
```

- [ ] **Step 2: 節點 data 注入 `nonInteractive`**

`useWorkflowNodes.ts` 的 `canvasNodes` computed（第 58-74 行），在回傳物件的 `data` 內（`flashType` 那行之後）加一欄：

```ts
      return {
        ...node,
        class: '',
        data: {
          ...node.data,
          status,
          colorClass: status === 'finished' ? 'node-yellow' : node.data.colorClass,
          highlighted,
          highlightColor: highlighted ? color : null,
          isSelected: node.id === selectedNodeId.value,
          flashType: nodeFlash.value.get(node.id) ?? null,
          nonInteractive: node.id.startsWith('model-'),
        },
      }
```

- [ ] **Step 3: IconNode 讀旗標並套用游標**

`IconNode.vue` 的 `<script setup>` 尾端（`flashType` computed，第 78 行之後）加：

```ts
  // 模型節點停用互動：游標不顯示可點暗示
  const nonInteractive = computed(() => Boolean(props.data?.nonInteractive))
```

模板最外層 `.icon-node-wrap`（第 3-9 行）加上條件 class：

```html
  <div
    class="icon-node-wrap"
    :class="{ 'is-non-interactive': nonInteractive }"
    :style="{
      '--node-accent': accentColor,
      ...(highlightColor ? { '--highlight-color': highlightColor } : {}),
    }"
  >
```

`<style scoped>` 加（放在 `.icon-node-wrap { … }` 規則之後即可）：

```css
  .is-non-interactive {
    cursor: default;
  }
```

- [ ] **Step 4: 型別檢查 + lint**

Run（從 `frontend/`）：`npm run build && npm run lint`
Expected: 皆通過。

- [ ] **Step 5: 手動驗證**

`npm run dev` → 有模型節點的 workflow：
- 點任一模型節點：**不**開啟面板（抽屜不展開）。
- 滑鼠移到模型節點上：游標為預設箭頭（非手指／非可點暗示）。
- 點其他節點（file / dataTable / settings / testScore 等）：面板照常開啟，行為不變。

- [ ] **Step 6: Commit（先問使用者）**

取得確認後：

```bash
git add frontend/src/components/workflow/WorkflowWorkspace.vue frontend/src/composables/workflow/useWorkflowNodes.ts frontend/src/components/workflow/IconNode.vue
git commit -m "feat: 模型節點停用點選，不開面板且游標非可互動"
```

---

## 完成後

三個 task 都完成、`npm run build` 與 `npm run lint` 全綠、手動驗證通過後，批次 A 收工。批次 B（跨節點上一步＋下游重置）另開 spec → plan。
