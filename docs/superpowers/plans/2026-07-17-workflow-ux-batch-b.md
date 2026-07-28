# Workflow UX 批次 B 實作計畫：執行前回退 + 狀態機修正

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 workflow 設定階段可跨節點回退（Settings→DataTable）並在真的改動時重置流程狀態，同時修好同一塊狀態機的暫停視覺、硬編碼 fallback、繼續按鈕誤觸發，以及 DataTable 重選 target 的行為。

**Architecture:** 純前端 Vue 3。狀態機在 `useWorkflowExecution.ts`；回退/重置與事件轉傳在 `WorkflowWorkspace.vue`（經 `WorkflowOptionsPanel.vue` 轉傳）；面板互動在 `SettingsPanel.vue` / `DataTablePanel.vue`。範圍限執行前設定階段。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript、`@vue-flow/core`、Vite。

## Global Constraints

- **無自動測試**：每個 task 的驗證為 `npm run build`（vue-tsc 型別檢查）＋ `npm run dev` 手動操作。指令都從 `frontend/` 執行。
- **使用者可見文字用繁體中文**。
- **只在執行前回退**：不碰已啟動 job 之後的回退/重跑。
- **只清流程/進度狀態**（`dataTableApplied`、`nodeStatuses` 完成標記），**保留** Settings 設定（models/preprocessing/featureEngineering/compute_ci）。
- **別動 localStorage 還原/checkpoint 啟發式**（`WorkflowWorkspace.vue:496-516`）：那段只在 `pausedAtNodeId===null`（已按執行）時跑，本批不改它。
- **Commit 前必須先取得使用者明確確認**；commit 訊息一行、英文、不加 `Co-Authored-By`、不引用私人筆記或其編號。
- 任務逐一實作、逐一 commit（同一檔案跨任務的變更用「先做先 commit」的順序處理，不要一次全改完再拆）。

---

### Task 1: 狀態機正確性 — 暫停視覺一致 + 移除硬編碼 fallback

**Files:**
- Modify: `frontend/src/composables/workflow/useWorkflowExecution.ts`（`continueWorkflow` 兩個分支、`buildWorkflowPayload`）

**Interfaces:**
- Consumes: 既有 `nodeStatuses`、`pausedAtNodeId`、`selectedTargetColumn`。
- Produces: 暫停到 settings 時 `nodeStatuses.get('settings') === 'running'`（非 `'finished'`）；按「執行」時才轉 `'finished'`。

- [ ] **Step 1: 暫停到 settings 時不要標成 finished**

`useWorkflowExecution.ts` 的 `continueWorkflow`，dataTable 分支裡把 settings 設 finished 的那行（約第 240 行）：

```ts
        next.set('settings', 'finished')
```

改為：

```ts
        next.set('settings', 'running')
```

- [ ] **Step 2: 按「執行」時把 settings 收成 finished**

同檔 `continueWorkflow` 的 settings 分支，在通過守門、重置旗標那段之後（約第 263 行 `workflowResult.value = null` 之後）插入：

```ts
      const settledSettings = new Map(nodeStatuses.value)
      settledSettings.set('settings', 'finished')
      nodeStatuses.value = settledSettings
```

- [ ] **Step 3: 移除硬編碼 target fallback**

同檔 `buildWorkflowPayload` 的 `target_col`（約第 87 行）：

```ts
      target_col: selectedTargetColumn.value?.name ?? testScoreNode?.data.config.targetCol ?? '是否跌倒',
```

改為：

```ts
      target_col: selectedTargetColumn.value?.name ?? testScoreNode?.data.config.targetCol ?? '',
```

- [ ] **Step 4: 型別檢查**

Run（從 `frontend/`）：`npm run build`
Expected: 通過。

- [ ] **Step 5: 手動驗證**

`npm run dev` → 完整走到停在 Settings：settings 節點顯示 spinner（非黃色），`settings → 下一個節點` 的連線是灰色（非黃、非流動）。按「執行」後 settings 變黃、往下跑。

- [ ] **Step 6: Commit（先問使用者）**

```bash
git add frontend/src/composables/workflow/useWorkflowExecution.ts
git commit -m "fix: keep settings node in waiting state while paused, drop hardcoded target fallback"
```

---

### Task 2: DataTable 重選 target 自動 demote 舊 target

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue`（Role 下拉、`onRoleChange`、移除 `hasOtherTarget`）

**Interfaces:**
- Consumes: 既有 `columnSettings` ref、`roleOptions`。
- Produces: 任一欄可被選為 target；設為 target 時其他 target 自動變 feature。

- [ ] **Step 1: 移除 target 選項的 disabled**

`DataTablePanel.vue` 的 Role `<option>`（約第 91-102 行）：

```html
                      <option
                        v-for="role in roleOptions"
                        :key="role"
                        :disabled="
                          role === 'target' &&
                            hasOtherTarget(index) &&
                            column.role !== 'target'
                        "
                        :value="role"
                      >
                        {{ roleLabels[role] }}
                      </option>
```

改為：

```html
                      <option
                        v-for="role in roleOptions"
                        :key="role"
                        :value="role"
                      >
                        {{ roleLabels[role] }}
                      </option>
```

- [ ] **Step 2: Role 下拉加 `@change`**

同檔 Role `<select>`（約第 83-90 行）加上 `@change="onRoleChange(index)"`：

```html
                    <select
                      v-model="column.role"
                      class="role-select"
                      :class="{
                        'role-select--attention': props.loading && !hasTarget && !roleSelectTouched,
                      }"
                      @change="onRoleChange(index)"
                      @focus="handleRoleSelectFocus"
                    >
```

- [ ] **Step 3: 新增 `onRoleChange`、移除不再使用的 `hasOtherTarget`**

在 `<script setup>` 把 `hasOtherTarget`（約第 250-254 行）整個刪除：

```ts
  function hasOtherTarget (index: number): boolean {
    return columnSettings.value.some(
      (item, itemIndex) => itemIndex !== index && item.role === 'target',
    )
  }
```

並在 `applyColumnSettings`（約第 289-291 行）之後新增：

```ts
  function onRoleChange (index: number): void {
    if (columnSettings.value[index]?.role !== 'target') return
    columnSettings.value.forEach((col, i) => {
      if (i !== index && col.role === 'target') {
        col.role = 'feature'
      }
    })
  }
```

- [ ] **Step 4: 型別檢查**

Run：`npm run build`
Expected: 通過（確認沒有 `hasOtherTarget is declared but never read` 之類殘留）。

- [ ] **Step 5: 手動驗證**

`npm run dev` → DataTable：先把 A 欄設 target，再把 B 欄設 target → A 欄自動變回 Feature，永遠只有一個 target。

- [ ] **Step 6: Commit（先問使用者）**

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "feat: re-selecting a target demotes the previous target to feature"
```

---

### Task 3: DataTable「繼續」加暫停感知

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue`（繼續按鈕 disable 條件）
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`（`handleApplyColumnConfig` 防呆）

**Interfaces:**
- Consumes: DataTablePanel 既有 `props.loading`（＝`pausedNodeId === 'dataTable'`）；WorkflowWorkspace 既有 `pausedAtNodeId`。
- Produces: 流程不在 dataTable 這步時，繼續按鈕不可按、`handleApplyColumnConfig` 直接 return。

- [ ] **Step 1: 繼續按鈕 disable 加 `!props.loading`**

`DataTablePanel.vue` 的 apply 按鈕（約第 135-143 行）：

```html
          <button
            class="btn-apply"
            :class="{ 'btn-apply--disabled': !hasTarget }"
            :disabled="!hasTarget"
            type="button"
            @click="applyColumnSettings"
          >
            繼續
          </button>
```

改為：

```html
          <button
            class="btn-apply"
            :class="{ 'btn-apply--disabled': !hasTarget || !props.loading }"
            :disabled="!hasTarget || !props.loading"
            type="button"
            @click="applyColumnSettings"
          >
            繼續
          </button>
```

- [ ] **Step 2: `handleApplyColumnConfig` 加防呆**

`WorkflowWorkspace.vue` 的 `handleApplyColumnConfig`（約第 286 行）開頭加守門：

```ts
  function handleApplyColumnConfig (): void {
    if (pausedAtNodeId.value !== 'dataTable') return
    dataTableApplied.value = true
    workflowError.value = null
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }
```

- [ ] **Step 3: 型別檢查**

Run：`npm run build`
Expected: 通過。

- [ ] **Step 4: 手動驗證**

`npm run dev` → 選 target → 繼續（推進到 Settings）→ 回點 dataTable 節點：面板的「繼續」是灰色不可按；不會跳出「請至少新增一個模型」。

- [ ] **Step 5: Commit（先問使用者）**

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "fix: gate Data Table continue button on the flow actually being at that step"
```

---

### Task 4: 只有真的改了才重置（columnConfig 深比對）

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`（新增 `columnConfigEqual`、改寫 `handleUpdateConfig` 的 dataTable columnConfig 區塊）

**Interfaces:**
- Consumes: 既有 `dataTableApplied`、`nodes`、`saveState`。
- Produces: dataTable columnConfig 真的變動且原本已 Apply 時才 `dataTableApplied = false`。

- [ ] **Step 1: 新增 `columnConfigEqual` 輔助函式**

`WorkflowWorkspace.vue` 的 `<script setup>` 內、`handleUpdateConfig` 之前，新增：

```ts
  function columnConfigEqual (a: unknown, b: unknown): boolean {
    if (!Array.isArray(a) || !Array.isArray(b)) return a === b
    if (a.length !== b.length) return false
    return a.every((col, i) => {
      const cur = col as { name?: unknown, type?: unknown, role?: unknown }
      const other = b[i] as { name?: unknown, type?: unknown, role?: unknown } | undefined
      return other !== undefined
        && cur.name === other.name
        && cur.type === other.type
        && cur.role === other.role
    })
  }
```

- [ ] **Step 2: 改寫 dataTable columnConfig 區塊**

`handleUpdateConfig` 尾段（約第 386-401 行）：

```ts
    nodes.value = nodes.value.map(node => {
      if (node.id !== payload.nodeId) return node
      return { ...node, data: { ...node.data, config: { ...node.data.config, ...payload.config } } }
    })
    if (payload.nodeId === 'settings' && 'compute_ci' in payload.config) {
      syncComputeCiNode()
    }
    if (payload.nodeId === 'dataTable' && 'columnConfig' in payload.config) {
      const columnConfig = payload.config.columnConfig
      const hasTarget = Array.isArray(columnConfig)
        && columnConfig.some(col => (col as { role?: string })?.role === 'target')
      if (!hasTarget) {
        dataTableApplied.value = false
      }
    }
    saveState()
```

改為（在 map 之前先擷取舊值，再深比對）：

```ts
    const prevColumnConfig = payload.nodeId === 'dataTable' && 'columnConfig' in payload.config
      ? nodes.value.find(n => n.id === 'dataTable')?.data.config.columnConfig
      : undefined

    nodes.value = nodes.value.map(node => {
      if (node.id !== payload.nodeId) return node
      return { ...node, data: { ...node.data, config: { ...node.data.config, ...payload.config } } }
    })
    if (payload.nodeId === 'settings' && 'compute_ci' in payload.config) {
      syncComputeCiNode()
    }
    if (payload.nodeId === 'dataTable' && 'columnConfig' in payload.config) {
      // 只有真的改了（且原本已 Apply）才翻回旗標；面板重掛 emit 相同設定不算改動
      if (dataTableApplied.value && !columnConfigEqual(prevColumnConfig, payload.config.columnConfig)) {
        dataTableApplied.value = false
      }
    }
    saveState()
```

- [ ] **Step 3: 型別檢查**

Run：`npm run build`
Expected: 通過。

- [ ] **Step 4: 手動驗證**

`npm run dev`：
- 選 target → 繼續 → Settings 加一個模型 → 回點 dataTable，**不改任何東西** → 再選 settings 節點按繼續能直接前進、模型還在。
- 選 target → 繼續 → 回 dataTable，**改 target 或欄位型別** → dataTable「繼續」需重按（改動後才 apply 得了）。

- [ ] **Step 5: Commit（先問使用者）**

```bash
git add frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "fix: only reset applied flag when the column config actually changed"
```

---

### Task 5: 跨節點「← 回 Data Table」控件

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/SettingsPanel.vue`（新增 `back-node` emit、頂部 back 按鈕、樣式）
- Modify: `frontend/src/components/workflow/WorkflowOptionsPanel.vue`（`back-node` emit 定義 + SettingsPanel 轉傳）
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`（`@back-node` 綁定 + `handleBackToDataTable`）

**Interfaces:**
- Consumes: WorkflowWorkspace 既有 `pausedAtNodeId`、`nodeStatuses`、`selectedNodeId`、`expandDrawer`、`saveState`。
- Produces: `SettingsPanel` emit `back-node` → `WorkflowOptionsPanel` re-emit `back-node` → `WorkflowWorkspace.handleBackToDataTable()`。

- [ ] **Step 1: SettingsPanel 新增 `back-node` emit**

`SettingsPanel.vue` 的 `defineEmits`（約第 236-242 行）加一行：

```ts
  const emit = defineEmits<{
    (e: 'add-model' | 'remove-model', name: string): void
    (e: 'update-preprocessing' | 'update-feature-engineering', steps: Array<Record<string, unknown>>): void
    (e: 'update-compute-ci', value: boolean): void
    (e: 'continue'): void
    (e: 'back-node'): void
    (e: 'step-change', step: number): void
  }>()
```

- [ ] **Step 2: SettingsPanel 頂部加 back 按鈕**

模板最外層 `<section class="settings-wizard">` 之後、`<!-- ── 步驟頁籤 ── -->` 之前插入：

```html
    <button class="back-to-datatable" type="button" @click="emit('back-node')">
      <span aria-hidden="true">←</span> 回 Data Table
    </button>
```

- [ ] **Step 3: back 按鈕樣式**

`<style scoped>` 內 `.settings-wizard { … }` 規則之後新增：

```css
  .back-to-datatable {
    flex-shrink: 0;
    align-self: flex-start;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 4px;
    border: none;
    background: none;
    color: #005dff;
    font-size: 12px;
    cursor: pointer;
  }

  .back-to-datatable:hover {
    text-decoration: underline;
  }
```

- [ ] **Step 4: WorkflowOptionsPanel 轉傳 `back-node`**

`WorkflowOptionsPanel.vue` 的 `defineEmits`（約第 272-277 行）把 `back-node` 加入字串 union：

```ts
    (e: 'open-upload' | 'apply-column-config' | 'continue-settings' | 'back-node'): void
```

並在 `<SettingsPanel … />` 使用處（約第 73-88 行）加上轉傳：

```html
            @back-node="emit('back-node')"
```

- [ ] **Step 5: WorkflowWorkspace 綁定並實作 handler**

`WorkflowWorkspace.vue` 的 `<WorkflowOptionsPanel … />`（約第 84-91 行事件區）加上：

```html
                @back-node="handleBackToDataTable"
```

並在 `<script setup>`（`handleContinueSettings` 附近，約第 294 行之後）新增：

```ts
  function handleBackToDataTable (): void {
    pausedAtNodeId.value = 'dataTable'
    const next = new Map(nodeStatuses.value)
    next.set('dataTable', 'running')
    next.delete('settings')
    nodeStatuses.value = next
    selectedNodeId.value = 'dataTable'
    expandDrawer()
    saveState()
  }
```

- [ ] **Step 6: 型別檢查**

Run：`npm run build`
Expected: 通過。

- [ ] **Step 7: 手動驗證**

`npm run dev`：
- 走到 Settings（任一 tab）→ 面板頂部有「← 回 Data Table」→ 點它回到 DataTable、dataTable 顯示等待中、settings 不再是完成態。
- 沒改東西 → 回 Settings 前進順暢、設定都在（配合 Task 4）。
- 「← 回 Data Table」在四個 tab 都看得到，且樣式明顯有別於 footer 的上一步/下一步/執行。

- [ ] **Step 8: Commit（先問使用者）**

```bash
git add frontend/src/components/workflow/nodePanel/SettingsPanel.vue frontend/src/components/workflow/WorkflowOptionsPanel.vue frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "feat: add back-to-Data-Table control to Settings panel"
```

---

## 完成後

五個 task 完成、`npm run build` 通過、手動走完整流程與各回退/改動情境後，批次 B 收工。`npm run lint` 為既有壞基線，本批照現有檔案風格撰寫、不引入新種類問題。批次 C（Feature Engineering panel 重做、Feature Importance 下拉 + 自製下拉元件）另開 spec → plan。
