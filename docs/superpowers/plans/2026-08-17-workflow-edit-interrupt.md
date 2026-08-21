# Workflow 編輯中斷與結果失效 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 編輯 `settings`/`dataTable`（含透過 settings 面板編輯的 `testScore` 驗證方式）節點設定時，如果有結果或 job 正在跑，彈確認 modal；確定後前端放棄該 job、清空結果、把靜態結果節點的視覺狀態重置、導向被編輯的節點；取消則面板還原。

**Architecture:** 三個獨立改動組成：(1) `useWorkflowExecution.ts` 讓 `pollJob()` 的 `setInterval` id 可以從外部取消，新增 `abandonActiveJob()`；(2) 新增一個小型確認對話框元件 `InterruptConfirmDialog.vue`；(3) `WorkflowWorkspace.vue` 把現有的 `handleUpdateConfig` 邏輯抽成 `applyConfigChange()`，前面加一層「有結果/job 在跑 + 值真的改了」的門檻檢查，符合條件就先暫存變更、彈窗，等使用者確認才真的呼叫 `applyConfigChange()` 並執行下游失效；取消則丟棄暫存、透過遞增一個 key 強制面板重新掛載回原本的值。同時修掉既有 `clearSettingsDownstream()` 只清「被移除節點」狀態、沒清 `testScore`/`featureImportance`/`confusionMatrix` 這些一直留在畫布上的節點狀態的既有 bug。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript，純前端改動，不動後端。

## Global Constraints

- 「中斷」只在前端生效：停止 `pollJob()` 的輪詢、清空 `activeJobId`，後端的模型訓練執行緒繼續跑完，但前端不再理會其結果。**不修改任何後端檔案**
- 不加畫布鏡頭平移（Vue Flow `setCenter`）。導向節點沿用既有的 `selectedNodeId` + `expandDrawer()` 慣用法
- 觸發範圍是 `settings`、`dataTable`、`testScore` 這三個 nodeId 經過 `handleUpdateConfig` 的 `update-config` 事件（`testScore` 是因為 `WorkflowOptionsPanel.vue:401` 的「驗證方式」編輯，即使是在 `settings` 節點面板上操作，emit 時用的是 `nodeId: 'testScore'`——這是既有的既定行為，不是這次要改的，這次只是要讓中斷邏輯也涵蓋到它）。透過畫布按鈕直接加/移除模型（`handleAddModel`/`handleRemoveModel`）維持既有的立即生效行為，不在這次的確認流程範圍內
- 觸發條件：`workflowResult.value !== null` 或 `activeJobId.value !== null`，**且**這次的新設定值跟節點上目前的值不同（用 `JSON.stringify` 深度比較，取代既有只用在 dataTable 的 `columnConfigEqual`）
- 取消時，暫存的編輯值要完全丟棄，面板要重新從（沒被改動過的）節點設定重繪

---

### Task 1: `useWorkflowExecution.ts` 讓輪詢可以從外部取消

**Files:**
- Modify: `frontend/src/composables/workflow/useWorkflowExecution.ts`

**Interfaces:**
- Produces: `abandonActiveJob(): void`（新的具名匯出函式，加進 composable 回傳物件）

- [ ] **Step 1: 新增 `pollIntervalId` ref**

第 47 行現有：
```typescript
  const activeJobId = ref<string | null>(null)
```
改成：
```typescript
  const activeJobId = ref<string | null>(null)
  const pollIntervalId = ref<number | null>(null)
```

- [ ] **Step 2: 讓 `pollJob()` 把 interval id 存進 ref，不要用區域變數**

現有的 `pollJob()`（第 128-173 行）：
```typescript
  function pollJob (
    jobId: string,
    modelNodeIdsOrdered: string[],
    postModelSteps: DemoStep[],
    seenInit = 0,
  ): void {
    let seen = seenInit
    const intervalId = window.setInterval(() => {
      ;(async () => {
        try {
          const job = await fetchWorkflowJob(jobId)

          if (job.completedModels.length > seen) {
            const next = new Map(nodeStatuses.value)
            for (let i = seen; i < job.completedModels.length; i += 1) {
              next.set(modelNodeIdsOrdered[i]!, 'finished')
              const nextNodeId = modelNodeIdsOrdered[i + 1]
              if (nextNodeId) {
                next.set(nextNodeId, 'running')
              }
            }
            nodeStatuses.value = next
            seen = job.completedModels.length
          }

          if (modelNodeIdsOrdered.length > 0) {
            onProgress?.(Math.round((seen / modelNodeIdsOrdered.length) * 100))
          }

          if (job.status === 'done') {
            window.clearInterval(intervalId)
            activeJobId.value = null
            workflowResult.value = job.result
            window.setTimeout(() => finishGatedSteps(postModelSteps), 200)
          } else if (job.status === 'error') {
            window.clearInterval(intervalId)
            activeJobId.value = null
            workflowError.value = job.error ?? 'Workflow 執行失敗'
            window.setTimeout(() => finishGatedSteps(postModelSteps), 200)
          }
        } catch {
          // 輪詢暫時失敗（網路抖動等），下一輪再試，不中斷整個流程
        }
      })()
    }, JOB_POLL_INTERVAL_MS)
  }
```

改成（把 `const intervalId = window.setInterval(...)` 改成寫進 `pollIntervalId.value`，內部兩處 `window.clearInterval(intervalId)` 改成清 `pollIntervalId.value` 並歸零）：

```typescript
  function pollJob (
    jobId: string,
    modelNodeIdsOrdered: string[],
    postModelSteps: DemoStep[],
    seenInit = 0,
  ): void {
    let seen = seenInit
    pollIntervalId.value = window.setInterval(() => {
      ;(async () => {
        try {
          const job = await fetchWorkflowJob(jobId)

          if (job.completedModels.length > seen) {
            const next = new Map(nodeStatuses.value)
            for (let i = seen; i < job.completedModels.length; i += 1) {
              next.set(modelNodeIdsOrdered[i]!, 'finished')
              const nextNodeId = modelNodeIdsOrdered[i + 1]
              if (nextNodeId) {
                next.set(nextNodeId, 'running')
              }
            }
            nodeStatuses.value = next
            seen = job.completedModels.length
          }

          if (modelNodeIdsOrdered.length > 0) {
            onProgress?.(Math.round((seen / modelNodeIdsOrdered.length) * 100))
          }

          if (job.status === 'done') {
            if (pollIntervalId.value !== null) window.clearInterval(pollIntervalId.value)
            pollIntervalId.value = null
            activeJobId.value = null
            workflowResult.value = job.result
            window.setTimeout(() => finishGatedSteps(postModelSteps), 200)
          } else if (job.status === 'error') {
            if (pollIntervalId.value !== null) window.clearInterval(pollIntervalId.value)
            pollIntervalId.value = null
            activeJobId.value = null
            workflowError.value = job.error ?? 'Workflow 執行失敗'
            window.setTimeout(() => finishGatedSteps(postModelSteps), 200)
          }
        } catch {
          // 輪詢暫時失敗（網路抖動等），下一輪再試，不中斷整個流程
        }
      })()
    }, JOB_POLL_INTERVAL_MS)
  }
```

`resumeJob()`（第 342-399 行）也會呼叫這個同一個 `pollJob()`（第 393 行），不需要另外改，因為它一樣會把新的 interval id 寫進同一個 `pollIntervalId` ref。

- [ ] **Step 3: 新增 `abandonActiveJob()`**

在 `resumeJob()` 函式（結尾在第 399 行）之後、`return { ... }`（第 401 行）之前，新增：

```typescript
  /** 前端放棄目前正在追蹤的 job：停止輪詢、清空 activeJobId。
   * 後端的模型訓練執行緒可能還在跑，但前端從此不再理會其結果。 */
  function abandonActiveJob (): void {
    if (pollIntervalId.value !== null) {
      window.clearInterval(pollIntervalId.value)
      pollIntervalId.value = null
    }
    activeJobId.value = null
  }
```

- [ ] **Step 4: 把 `abandonActiveJob` 加進回傳物件**

現有的回傳物件（第 401-415 行）：
```typescript
  return {
    workflowResult,
    workflowError,
    pausedAtNodeId,
    dataTableApplied,
    activeJobId,
    dataTableCanContinue,
    settingsCanContinue,
    workflowSummary,
    buildWorkflowPayload,
    runWorkflowRequest,
    executeWorkflow,
    continueWorkflow,
    resumeJob,
  }
```
改成（加一行 `abandonActiveJob,`）：
```typescript
  return {
    workflowResult,
    workflowError,
    pausedAtNodeId,
    dataTableApplied,
    activeJobId,
    dataTableCanContinue,
    settingsCanContinue,
    workflowSummary,
    buildWorkflowPayload,
    runWorkflowRequest,
    executeWorkflow,
    continueWorkflow,
    resumeJob,
    abandonActiveJob,
  }
```

- [ ] **Step 5: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 這個專案目前有 50 個既有的、跟 `@tiptap/*` 套件解析失敗有關的錯誤（環境缺套件、跟本次改動無關）。用 `npm run type-check 2>&1 | grep -c "error TS"` 確認還是 50，或用 `grep -i "useWorkflowExecution"` 確認輸出裡沒有這個檔案的錯誤。

- [ ] **Step 6: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/composables/workflow/useWorkflowExecution.ts
git commit -m "feat: allow cancelling the active workflow job's polling loop"
```

---

### Task 2: 新增確認對話框元件 `InterruptConfirmDialog.vue`

**Files:**
- Create: `frontend/src/components/workflow/InterruptConfirmDialog.vue`

**Interfaces:**
- Produces: `<InterruptConfirmDialog>` 元件，props `{ visible: boolean, message: string }`，emits `confirm`/`cancel`

這個資料夾（`components/workflow/`）既有的對話框元件是 `UploadDialog.vue`——手刻的 backdrop + card div，不是 Vuetify 的 `v-dialog`。這次比照 `UploadDialog.vue` 的寫法，保持這個資料夾內的一致性。

- [ ] **Step 1: 建立元件**

```vue
<template>
  <div
    v-if="visible"
    class="interrupt-confirm-backdrop"
    @click.self="emit('cancel')"
  >
    <div class="interrupt-confirm-card">
      <h3>確定要中斷嗎？</h3>
      <p>{{ message }}</p>
      <div class="interrupt-confirm-actions">
        <button
          class="interrupt-confirm-btn interrupt-confirm-btn--secondary"
          type="button"
          @click="emit('cancel')"
        >
          取消
        </button>
        <button
          class="interrupt-confirm-btn interrupt-confirm-btn--primary"
          type="button"
          @click="emit('confirm')"
        >
          確定中斷
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  defineProps<{
    visible: boolean
    message: string
  }>()

  const emit = defineEmits<{
    confirm: []
    cancel: []
  }>()
</script>

<style scoped>
  .interrupt-confirm-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .interrupt-confirm-card {
    background: var(--color-surface);
    border-radius: 14px;
    padding: 24px;
    max-width: 380px;
    width: 90%;
    box-shadow: 0 20px 48px rgba(15, 23, 42, 0.24);
  }

  .interrupt-confirm-card h3 {
    margin: 0 0 8px;
    font-size: 17px;
    color: var(--color-ink);
  }

  .interrupt-confirm-card p {
    margin: 0 0 20px;
    font-size: 13px;
    color: var(--color-secondary);
    line-height: 1.5;
  }

  .interrupt-confirm-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }

  .interrupt-confirm-btn {
    padding: 9px 16px;
    border-radius: 8px;
    border: none;
    font-size: 13px;
    cursor: pointer;
  }

  .interrupt-confirm-btn--secondary {
    background: var(--color-primary);
    color: var(--color-ink);
    border: 1px solid color-mix(in oklab, var(--color-accent) 18%, transparent);
  }

  .interrupt-confirm-btn--primary {
    background: var(--color-accent);
    color: #fff;
  }
</style>
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 錯誤數量跟 Task 1 結束時一樣（沒有新增，不含這個新檔案的錯誤）

- [ ] **Step 3: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/InterruptConfirmDialog.vue
git commit -m "feat: add InterruptConfirmDialog component"
```

---

### Task 3: `WorkflowWorkspace.vue` 接上中斷確認流程

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`

**Interfaces:**
- Consumes: `abandonActiveJob()`（Task 1 產生，從 `useWorkflowExecution()` 解構取得）
- Consumes: `<InterruptConfirmDialog>`（Task 2 產生，props `visible`/`message`，emits `confirm`/`cancel`）

- [ ] **Step 1: import 新元件**

第 146 行現有：
```typescript
  import WorkflowOptionsPanel from './WorkflowOptionsPanel.vue'
```
改成（按字母順序插入）：
```typescript
  import InterruptConfirmDialog from './InterruptConfirmDialog.vue'
  import WorkflowOptionsPanel from './WorkflowOptionsPanel.vue'
```

- [ ] **Step 2: 從 `useWorkflowExecution()` 多解構 `abandonActiveJob`**

第 213-222 行現有：
```typescript
  const {
    workflowResult,
    workflowError,
    pausedAtNodeId,
    dataTableApplied,
    activeJobId,
    workflowSummary,
    executeWorkflow,
    continueWorkflow,
    resumeJob,
  } = useWorkflowExecution({
```
改成（加 `abandonActiveJob,`）：
```typescript
  const {
    workflowResult,
    workflowError,
    pausedAtNodeId,
    dataTableApplied,
    activeJobId,
    workflowSummary,
    executeWorkflow,
    continueWorkflow,
    resumeJob,
    abandonActiveJob,
  } = useWorkflowExecution({
```

- [ ] **Step 3: 新增中斷確認流程用的 refs**

第 163 行現有：
```typescript
  const nodeFlash = ref<Map<string, 'add' | 'remove'>>(new Map())
```
改成（在它之後新增三個 ref）：
```typescript
  const nodeFlash = ref<Map<string, 'add' | 'remove'>>(new Map())
  const pendingConfigChange = ref<{ nodeId: string, config: Record<string, ConfigValue> } | null>(null)
  const showInterruptConfirm = ref(false)
  const panelResetKey = ref(0)
```

- [ ] **Step 4: 新增 `interruptMessage` computed**

在 `availableModelOptions` computed（第 275-277 行）之後新增：
```typescript
  const interruptMessage = computed(() =>
    activeJobId.value !== null
      ? '目前有 Workflow 正在執行中，更改此設定將會中斷執行並清除結果，確定要繼續嗎？'
      : '更改此設定將會清除目前的執行結果，確定要繼續嗎？',
  )
```

- [ ] **Step 5: 新增通用深度比對函式，取代 `columnConfigEqual`**

現有的 `columnConfigEqual`（第 389-400 行）：
```typescript
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
整段刪除，改成一個通用版本（放在同樣位置）：
```typescript
  // 通用深度比對：取代原本只比對 columnConfig 陣列的 columnConfigEqual，
  // 這次也要拿來比對 settings/testScore 的各種設定值（陣列、布林、巢狀物件都要能比）
  function configValuesEqual (a: unknown, b: unknown): boolean {
    return JSON.stringify(a) === JSON.stringify(b)
  }
```

第 475 行現有的呼叫處：
```typescript
      if (dataTableApplied.value && !columnConfigEqual(prevColumnConfig, payload.config.columnConfig)) {
```
改成：
```typescript
      if (dataTableApplied.value && !configValuesEqual(prevColumnConfig, payload.config.columnConfig)) {
```

- [ ] **Step 6: 新增 `resetDownstreamResultNodeStatuses()`，並讓 `clearSettingsDownstream()` 呼叫它**

現有的 `clearSettingsDownstream()`（第 345-361 行）：
```typescript
  // 改了欄位設定就把下游清空：清 Settings 設定、移除 model / pipeline / CI 節點
  function clearSettingsDownstream (): void {
    nodes.value = nodes.value
      .filter(n => !n.id.startsWith('model-') && n.id !== 'computeCi')
      .map(n => n.id === 'settings'
        ? { ...n, data: { ...n.data, config: { ...n.data.config, preprocessing: [], featureEngineering: [], models: [], compute_ci: false } } }
        : n)
    syncPipelineCanvasNodes()
    // 清掉已被移除節點的殘留狀態，免得之後重加同 id 的節點誤顯示成已完成
    const validIds = new Set(nodes.value.map(n => n.id))
    nodeStatuses.value = new Map(
      [...nodeStatuses.value].filter(([id]) => validIds.has(id)),
    )
    // 舊的執行結果也失效
    workflowResult.value = null
    isDemoFinished.value = false
  }
```

在它**之前**新增一個共用函式，並在它內部呼叫：

```typescript
  // testScore/featureImportance/confusionMatrix 是一直留在畫布上的靜態節點，
  // 光靠「篩掉已從 nodes.value 移除的節點」清不到它們——結果失效時要另外明確重置，
  // 不然它們會一直卡在 nodeStatuses 的 'finished'（對應 useWorkflowNodes.ts 的 node-yellow 顏色）
  function resetDownstreamResultNodeStatuses (): void {
    const staleStaticIds = new Set(['testScore', 'featureImportance', 'confusionMatrix'])
    const next = new Map(nodeStatuses.value)
    for (const id of [...next.keys()]) {
      if (staleStaticIds.has(id) || id.startsWith('model-')) {
        next.delete(id)
      }
    }
    nodeStatuses.value = next
  }

  // 改了欄位設定就把下游清空：清 Settings 設定、移除 model / pipeline / CI 節點
  function clearSettingsDownstream (): void {
    nodes.value = nodes.value
      .filter(n => !n.id.startsWith('model-') && n.id !== 'computeCi')
      .map(n => n.id === 'settings'
        ? { ...n, data: { ...n.data, config: { ...n.data.config, preprocessing: [], featureEngineering: [], models: [], compute_ci: false } } }
        : n)
    syncPipelineCanvasNodes()
    // 清掉已被移除節點的殘留狀態，免得之後重加同 id 的節點誤顯示成已完成
    const validIds = new Set(nodes.value.map(n => n.id))
    nodeStatuses.value = new Map(
      [...nodeStatuses.value].filter(([id]) => validIds.has(id)),
    )
    // 一直留在畫布上的靜態結果節點也要重置，不然顏色不會退回預設
    resetDownstreamResultNodeStatuses()
    // 舊的執行結果也失效
    workflowResult.value = null
    isDemoFinished.value = false
  }
```

- [ ] **Step 7: 把 `handleUpdateConfig` 的邏輯抽成 `applyConfigChange`，前面加門檻檢查**

現有的 `handleUpdateConfig`（第 402-483 行，完整內容）：
```typescript
  function handleUpdateConfig (payload: { nodeId: string, config: Record<string, ConfigValue> }): void {
    if (payload.nodeId === 'settings' && ('preprocessing' in payload.config || 'featureEngineering' in payload.config)) {
      const settingsNode = nodes.value.find(n => n.id === 'settings')

      let prevPreLen = 0
      if (Array.isArray(settingsNode?.data.config.preprocessing)) {
        prevPreLen = (settingsNode.data.config.preprocessing as unknown[]).length
      }
      let newPreLen = prevPreLen
      if (Array.isArray(payload.config.preprocessing)) {
        newPreLen = (payload.config.preprocessing as unknown[]).length
      }
      let prevFeLen = 0
      if (Array.isArray(settingsNode?.data.config.featureEngineering)) {
        prevFeLen = (settingsNode.data.config.featureEngineering as unknown[]).length
      }
      let newFeLen = prevFeLen
      if (Array.isArray(payload.config.featureEngineering)) {
        newFeLen = (payload.config.featureEngineering as unknown[]).length
      }

      let pipelineFlashId: string | null = null
      let pipelineFlashType: 'add' | 'remove' | null = null
      if (newPreLen !== prevPreLen) {
        pipelineFlashId = 'preprocessor'
        pipelineFlashType = newPreLen > prevPreLen ? 'add' : 'remove'
      } else if (newFeLen !== prevFeLen) {
        pipelineFlashId = 'featureEngineering'
        pipelineFlashType = newFeLen > prevFeLen ? 'add' : 'remove'
      }

      let needsDelay = false
      if (pipelineFlashType === 'remove' && nodes.value.some(n => n.id === pipelineFlashId)) {
        needsDelay = pipelineFlashId === 'preprocessor' ? newPreLen === 0 : newFeLen === 0
      }

      nodes.value = nodes.value.map(node => {
        if (node.id !== payload.nodeId) return node
        return { ...node, data: { ...node.data, config: { ...node.data.config, ...payload.config } } }
      })
      if ('compute_ci' in payload.config) {
        syncComputeCiNode()
      }

      if (needsDelay && pipelineFlashId && pipelineFlashType) {
        flashNode(pipelineFlashId, pipelineFlashType)
        window.setTimeout(() => {
          syncPipelineCanvasNodes()
          saveState()
        }, 450)
        return
      }
      syncPipelineCanvasNodes()
      if (pipelineFlashId && pipelineFlashType) {
        flashNode(pipelineFlashId, pipelineFlashType)
      }
      saveState()
      return
    }

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
      // 真的改了才重置（面板重掛送出相同設定不算改）
      if (dataTableApplied.value && !columnConfigEqual(prevColumnConfig, payload.config.columnConfig)) {
        dataTableApplied.value = false
        clearSettingsDownstream()
        // 改了就把流程拉回 dataTable，讓「繼續」可以再按
        snapFlowToDataTable()
      }
    }
    saveState()
  }
```

整段改成（函式改名為 `applyConfigChange`，內容除了 Step 5 提到的 `columnConfigEqual` → `configValuesEqual` 之外**完全不變**，然後在它之前新增門檻檢查與確認/取消處理函式）：

```typescript
  const GATED_NODE_IDS = new Set(['settings', 'dataTable', 'testScore'])

  function hasResultsToProtect (): boolean {
    return workflowResult.value !== null || activeJobId.value !== null
  }

  function configChangeIsNoOp (nodeId: string, config: Record<string, ConfigValue>): boolean {
    const current = nodes.value.find(n => n.id === nodeId)?.data.config ?? {}
    return Object.keys(config).every(key => configValuesEqual(current[key], config[key]))
  }

  function handleUpdateConfig (payload: { nodeId: string, config: Record<string, ConfigValue> }): void {
    if (
      GATED_NODE_IDS.has(payload.nodeId)
      && hasResultsToProtect()
      && !configChangeIsNoOp(payload.nodeId, payload.config)
    ) {
      pendingConfigChange.value = payload
      showInterruptConfirm.value = true
      return
    }
    applyConfigChange(payload)
  }

  function confirmInterrupt (): void {
    const payload = pendingConfigChange.value
    pendingConfigChange.value = null
    showInterruptConfirm.value = false
    if (!payload) return

    resetDownstreamResultNodeStatuses()
    workflowResult.value = null
    isDemoFinished.value = false
    if (activeJobId.value !== null) {
      abandonActiveJob()
    }

    applyConfigChange(payload)

    // testScore 的驗證方式是在 settings 節點的面板上編輯的（emit 時 nodeId 是 'testScore'，
    // 見 WorkflowOptionsPanel.vue 的 handleSettingsValidationUpdate），所以要導回 'settings'
    // 節點的面板，而不是跳到唯讀的 testScore 節點面板
    selectedNodeId.value = payload.nodeId === 'testScore' ? 'settings' : payload.nodeId
    expandDrawer()
    saveState()
  }

  function cancelInterrupt (): void {
    pendingConfigChange.value = null
    showInterruptConfirm.value = false
    panelResetKey.value += 1
  }

  function applyConfigChange (payload: { nodeId: string, config: Record<string, ConfigValue> }): void {
    if (payload.nodeId === 'settings' && ('preprocessing' in payload.config || 'featureEngineering' in payload.config)) {
      const settingsNode = nodes.value.find(n => n.id === 'settings')

      let prevPreLen = 0
      if (Array.isArray(settingsNode?.data.config.preprocessing)) {
        prevPreLen = (settingsNode.data.config.preprocessing as unknown[]).length
      }
      let newPreLen = prevPreLen
      if (Array.isArray(payload.config.preprocessing)) {
        newPreLen = (payload.config.preprocessing as unknown[]).length
      }
      let prevFeLen = 0
      if (Array.isArray(settingsNode?.data.config.featureEngineering)) {
        prevFeLen = (settingsNode.data.config.featureEngineering as unknown[]).length
      }
      let newFeLen = prevFeLen
      if (Array.isArray(payload.config.featureEngineering)) {
        newFeLen = (payload.config.featureEngineering as unknown[]).length
      }

      let pipelineFlashId: string | null = null
      let pipelineFlashType: 'add' | 'remove' | null = null
      if (newPreLen !== prevPreLen) {
        pipelineFlashId = 'preprocessor'
        pipelineFlashType = newPreLen > prevPreLen ? 'add' : 'remove'
      } else if (newFeLen !== prevFeLen) {
        pipelineFlashId = 'featureEngineering'
        pipelineFlashType = newFeLen > prevFeLen ? 'add' : 'remove'
      }

      let needsDelay = false
      if (pipelineFlashType === 'remove' && nodes.value.some(n => n.id === pipelineFlashId)) {
        needsDelay = pipelineFlashId === 'preprocessor' ? newPreLen === 0 : newFeLen === 0
      }

      nodes.value = nodes.value.map(node => {
        if (node.id !== payload.nodeId) return node
        return { ...node, data: { ...node.data, config: { ...node.data.config, ...payload.config } } }
      })
      if ('compute_ci' in payload.config) {
        syncComputeCiNode()
      }

      if (needsDelay && pipelineFlashId && pipelineFlashType) {
        flashNode(pipelineFlashId, pipelineFlashType)
        window.setTimeout(() => {
          syncPipelineCanvasNodes()
          saveState()
        }, 450)
        return
      }
      syncPipelineCanvasNodes()
      if (pipelineFlashId && pipelineFlashType) {
        flashNode(pipelineFlashId, pipelineFlashType)
      }
      saveState()
      return
    }

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
      // 真的改了才重置（面板重掛送出相同設定不算改）
      if (dataTableApplied.value && !configValuesEqual(prevColumnConfig, payload.config.columnConfig)) {
        dataTableApplied.value = false
        clearSettingsDownstream()
        // 改了就把流程拉回 dataTable，讓「繼續」可以再按
        snapFlowToDataTable()
      }
    }
    saveState()
  }
```

**注意**：`applyConfigChange` 函式體本身（除了那一行 `columnConfigEqual` → `configValuesEqual` 的改動）要跟原本的 `handleUpdateConfig` 逐字一致，不要順手精簡或調整既有的閃爍動畫時序邏輯——那不是這次的範圍。

- [ ] **Step 8: Template — 在抽屜的 `:key` 加上 `panelResetKey`，並掛上確認對話框**

現有（第 76-108 行附近）：
```html
        <div class="options-drawer__scroll">
          <Transition mode="out-in" name="drawer-content">
            <div
              :key="selectedNode?.id ?? 'no-node'"
              class="drawer-content-wrapper"
            >
```
改成：
```html
        <div class="options-drawer__scroll">
          <Transition mode="out-in" name="drawer-content">
            <div
              :key="`${selectedNode?.id ?? 'no-node'}-${panelResetKey}`"
              class="drawer-content-wrapper"
            >
```

在 `</section>`（模板結尾，第 110 行）**之前**新增：
```html
    <InterruptConfirmDialog
      :message="interruptMessage"
      :visible="showInterruptConfirm"
      @cancel="cancelInterrupt"
      @confirm="confirmInterrupt"
    />
```

- [ ] **Step 9: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 錯誤數量跟 Task 2 結束時一樣（沒有新增，不含 `WorkflowWorkspace.vue` 的錯誤）

- [ ] **Step 10: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "feat: confirm before interrupting a running/completed workflow on settings edit"
```

---

## 完成後的人工驗證

三個 task 都完成、commit 之後，在瀏覽器 `http://localhost:5173` 上驗證（後端/前端 dev server 都已在跑，直接測，不需要另開 worktree 連結）：

1. 執行一次 workflow 到完成，編輯 dataTable 欄位設定（改動一個欄位的 role 或 type）→ 應彈出確認 modal；按「確定中斷」→ 結果清空、`testScore`/`featureImportance`/`confusionMatrix` 節點顏色退回預設（不再黃）、畫面跳到 dataTable 節點設定面板
2. 執行一次 workflow 到完成後，切到 settings 節點，切換一個前處理選項 → 應彈出確認 modal（措辭應該是「更改此設定將會清除目前的執行結果」，因為沒有 job 在跑）；確定後同樣正確失效並跳到 settings 節點
3. 執行一次 workflow 到完成後，切換「驗證方式」（例如 k_fold 的折數）→ 應彈出確認 modal；確定後跳回 settings 節點（不是 testScore）
4. 執行中（job 正在跑、還沒完成）時編輯任一設定 → 應彈窗（措辭應該是「目前有 Workflow 正在執行中」）；確定後畫面不再顯示訓練進度動畫、`activeJobId` 清空（可用瀏覽器開發者工具的 Vue devtools 或 Network 分頁確認 `/api/models/workflow/jobs/<job_id>` 不再被輪詢）
5. 彈窗出現時按「取消」→ 面板上的欄位值回到編輯前的樣子，畫面上其他東西（結果、節點顏色、選取狀態）都不變
6. 全新的 project（沒有結果、沒有 job 在跑）時編輯任何設定 → 完全不彈窗，跟這次改動之前行為一樣
