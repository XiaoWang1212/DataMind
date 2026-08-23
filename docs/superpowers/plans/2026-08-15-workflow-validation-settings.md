# Workflow 驗證方式設定 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `SettingsPanel.vue` 新增「驗證方式」分頁，讓使用者能設定後端已支援的 5 種驗證方式（k_fold、group_k_fold、random_sampling、leave_one_out、test_on_test/test_on_train），並讓論文萃取的範例 schema 補上 `n_repeats`/`group_column` 兩個欄位。

**Architecture:** `SettingsPanel.vue` 新增第 5 個分頁，radio 選方式、選中展開對應子參數（互動模式參考 Orange Test & Score widget，視覺沿用 DataMind 現有面板樣式）。這個分頁讀寫的資料實際存在 `testScore` 節點（不是 `settings` 節點自己），`WorkflowWorkspace.vue` 負責把 `testScore` 節點的 `validation` 設定和 `dataTable` 節點的欄位清單往下傳，寫回時沿用既有的 `update-config` 事件機制指定 `nodeId: 'testScore'`。後端萃取 prompt 範例補兩個欄位讓論文萃取也能填出這些新參數。

**Tech Stack:** Vue 3 `<script setup>`、TypeScript、Python 3.11（prompt 字串調整）。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-15-workflow-validation-settings-design.md`
- **不**動 `backend/services/workflow/workflow_service.py` 的驗證邏輯（已經完整支援 5 種方式，不需要改）
- **不**動 `TestScorePanel.vue`（維持唯讀結果表格）
- `validation` 設定寫回時一律指定 `nodeId: 'testScore'`，不是 `settings` 節點自己（既有的 `handleUpdateConfig` 已經支援任意 `nodeId`，不需要改 `WorkflowWorkspace.vue` 的這個函式本身）
- 論文萃取（`useWorkflowImport.ts:94`）已經會把 `workflow_json.validation` 寫進 `testScore` 節點的 `config.validation`，不需要額外接線
- 本專案沒有單元測試框架，前端用 `npm run type-check` + 人工瀏覽器驗證，後端 prompt 調整無法自動化測試

---

### Task 1: 後端 — 萃取範例 schema 補 n_repeats/group_column

**Files:**
- Modify: `backend/services/gemini_service.py:35-72`（`_WORKFLOW_EXAMPLE`）

**Interfaces:** 無（獨立任務，不被其他任務消費，也不消費其他任務）

- [ ] **Step 1: 在 `_WORKFLOW_EXAMPLE` 的 `validation` 區塊補兩個欄位**

找到 `backend/services/gemini_service.py` 的（第 49-54 行）：

```python
  "validation": {
    "method": "k_fold",
    "n_splits": 10,
    "stratified": true,
    "train_size": 0.8
  },
```

改成（新增 `n_repeats`、`group_column` 兩個欄位，值用 null/預設值表示「這個範例用 k_fold 不需要它們，但欄位存在」）：

```python
  "validation": {
    "method": "k_fold",
    "n_splits": 10,
    "stratified": true,
    "train_size": 0.8,
    "n_repeats": 1,
    "group_column": null
  },
```

- [ ] **Step 2: 在填寫原則的 validation 規則後面補一句欄位用途說明**

找到 `backend/services/gemini_service.py` 的（第 96-105 行，「填寫原則」段落）：

```python
填寫原則：
- models：依論文列出的模型，name 必須完全符合可用模型名稱清單
- preprocessing：依論文資料處理方式，若未提及則用 fill_na+standardize
- featureEngineering：依論文特徵選擇方式，若未提及則用 select_relevant_features k=10
- validation：依論文驗證方式，若未提及則用 k_fold n_splits=10
- metrics：依論文評估指標，至少包含 balanced_accuracy 和 auc
```

改成（只在 `validation` 那一行後面加一句說明，其餘不動）：

```python
填寫原則：
- models：依論文列出的模型，name 必須完全符合可用模型名稱清單
- preprocessing：依論文資料處理方式，若未提及則用 fill_na+standardize
- featureEngineering：依論文特徵選擇方式，若未提及則用 select_relevant_features k=10
- validation：依論文驗證方式，若未提及則用 k_fold n_splits=10；method 為 random_sampling 時 n_repeats 填重複抽樣次數，method 為 group_k_fold 時 group_column 填分組依據的欄位名稱，其餘情況這兩個欄位可省略或填 null
- metrics：依論文評估指標，至少包含 balanced_accuracy 和 auc
```

- [ ] **Step 3: 語法檢查**

Run: `docker exec datamind-backend sh -lc "cd /app && .venv/bin/python -m py_compile services/gemini_service.py && echo OK"`
Expected: 印出 `OK`，無語法錯誤

- [ ] **Step 4: Commit**

```bash
git add backend/services/gemini_service.py
git commit -m "feat: teach extraction prompt about n_repeats and group_column validation fields"
```

---

### Task 2: 前端 — SettingsPanel 新增「驗證方式」分頁

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/SettingsPanel.vue`

**Interfaces:**
- Consumes: 無（這個任務先讓元件本身型別檢查通過，實際資料串接在 Task 3）
- Produces: `SettingsPanel.vue` 新增 prop `validation: Record<string, unknown>`、`datasetColumns: Array<{name: string, type: string, role: string}>`；新增 emit `update-validation`，payload 為完整的 `Record<string, unknown>`（新的 validation 物件）。供 Task 3 的 `WorkflowOptionsPanel.vue` 使用

- [ ] **Step 1: 新增 props 與 emit 型別**

找到（第 246-263 行）：

```ts
  const props = defineProps<{
    preprocessing: Array<Record<string, unknown>>
    featureEngineering: Array<Record<string, unknown>>
    models: Array<ModelEntry>
    computeCi: boolean
    availableModels: string[]
    usedModelNames: string[]
    modelOptionsLoading?: boolean
  }>()

  const emit = defineEmits<{
    (e: 'add-model' | 'remove-model', name: string): void
    (e: 'update-preprocessing' | 'update-feature-engineering', steps: Array<Record<string, unknown>>): void
    (e: 'update-compute-ci', value: boolean): void
    (e: 'continue'): void
    (e: 'back-node'): void
    (e: 'step-change', step: number): void
  }>()
```

改成：

```ts
  const props = defineProps<{
    preprocessing: Array<Record<string, unknown>>
    featureEngineering: Array<Record<string, unknown>>
    models: Array<ModelEntry>
    computeCi: boolean
    availableModels: string[]
    usedModelNames: string[]
    modelOptionsLoading?: boolean
    validation: Record<string, unknown>
    datasetColumns: Array<{ name: string, type: string, role: string }>
  }>()

  const emit = defineEmits<{
    (e: 'add-model' | 'remove-model', name: string): void
    (e: 'update-preprocessing' | 'update-feature-engineering', steps: Array<Record<string, unknown>>): void
    (e: 'update-compute-ci', value: boolean): void
    (e: 'update-validation', value: Record<string, unknown>): void
    (e: 'continue'): void
    (e: 'back-node'): void
    (e: 'step-change', step: number): void
  }>()
```

- [ ] **Step 2: `STEPS` 加入「驗證方式」，本地 state 與同步邏輯**

找到（第 265-266 行）：

```ts
  const STEPS = ['前處理', '特徵工程', '模型', '信賴區間'] as const
  const currentStep = ref(0)
```

改成：

```ts
  const STEPS = ['前處理', '特徵工程', '模型', '驗證方式', '信賴區間'] as const
  const currentStep = ref(0)
```

找到（第 308-324 行，`localPreprocessing`/`localFE` 的宣告與 watch）：

```ts
  const localPreprocessing = ref<Array<Record<string, unknown>>>([...props.preprocessing])
  const localFE = ref<Array<Record<string, unknown>>>([...props.featureEngineering])

  watch(
    () => props.preprocessing,
    v => {
      localPreprocessing.value = [...v]
    },
    { deep: true },
  )
  watch(
    () => props.featureEngineering,
    v => {
      localFE.value = [...v]
    },
    { deep: true },
  )
```

改成（在後面加一組 `localValidation` 的宣告與 watch，`VALIDATION_METHODS` 常數放在同一區塊上方）：

```ts
  const localPreprocessing = ref<Array<Record<string, unknown>>>([...props.preprocessing])
  const localFE = ref<Array<Record<string, unknown>>>([...props.featureEngineering])
  const localValidation = ref<Record<string, unknown>>({ ...props.validation })

  watch(
    () => props.preprocessing,
    v => {
      localPreprocessing.value = [...v]
    },
    { deep: true },
  )
  watch(
    () => props.featureEngineering,
    v => {
      localFE.value = [...v]
    },
    { deep: true },
  )
  watch(
    () => props.validation,
    v => {
      localValidation.value = { ...v }
    },
    { deep: true },
  )
```

- [ ] **Step 3: 新增驗證方式的常數與 patch 函式**

找到（第 296-303 行，`FEATURE_LABELS` 常數後面）：

```ts
  const FEATURE_LABELS: Record<string, string> = {
    select_relevant_features: '特徵選擇',
    pca: 'PCA 降維',
    discretize_continuous: '連續→離散',
    continuize_discrete: '離散→連續',
    normalize_features: '特徵正規化',
    remove_sparse_features: '移除稀疏特徵',
  }
```

改成（在後面新增 `VALIDATION_METHODS` 常數）：

```ts
  const FEATURE_LABELS: Record<string, string> = {
    select_relevant_features: '特徵選擇',
    pca: 'PCA 降維',
    discretize_continuous: '連續→離散',
    continuize_discrete: '離散→連續',
    normalize_features: '特徵正規化',
    remove_sparse_features: '移除稀疏特徵',
  }

  const VALIDATION_METHODS: Array<{ value: string, label: string }> = [
    { value: 'k_fold', label: 'Cross validation' },
    { value: 'group_k_fold', label: 'Cross validation by feature' },
    { value: 'random_sampling', label: 'Random sampling' },
    { value: 'leave_one_out', label: 'Leave one out' },
    { value: 'test_on_train', label: 'Test on train data' },
    { value: 'test_on_test', label: 'Test on test data' },
  ]
```

在 `addModel` 函式（第 409-413 行）後面新增：

```ts
  function patchValidation (key: string, value: unknown): void {
    localValidation.value = { ...localValidation.value, [key]: value }
    emit('update-validation', localValidation.value)
  }

  function setValidationMethod (method: string): void {
    localValidation.value = { ...localValidation.value, method }
    emit('update-validation', localValidation.value)
  }
```

- [ ] **Step 4: template — 新增驗證方式的 step-body**

找到（第 176-178 行，Step 2「模型」結束、Step 3「信賴區間」開始之間）：

```html
      <p v-else class="empty-hint">尚未加入任何模型</p>
    </div>

    <!-- ── Step 3：信賴區間 ── -->
    <div v-else class="step-body">
```

改成（插入新的驗證方式 step-body，原本「信賴區間」的 `v-else` 改成明確判斷 `currentStep === 4`，因為現在有 5 個 step 不能再靠 `v-else` 兜底最後一步）：

```html
      <p v-else class="empty-hint">尚未加入任何模型</p>
    </div>

    <!-- ── Step 3：驗證方式 ── -->
    <div v-else-if="currentStep === 3" class="step-body">
      <div class="validation-methods">
        <div
          v-for="method in VALIDATION_METHODS"
          :key="method.value"
          class="validation-method"
        >
          <label class="validation-method__radio">
            <input
              :checked="localValidation.method === method.value"
              name="validation-method"
              type="radio"
              @change="setValidationMethod(method.value)"
            >
            {{ method.label }}
          </label>

          <div v-if="localValidation.method === method.value" class="validation-method__params">
            <template v-if="method.value === 'k_fold' || method.value === 'group_k_fold'">
              <div class="param-pair">
                <span class="param-key">Number of folds</span>
                <input
                  class="param-num"
                  min="2"
                  type="number"
                  :value="Number(localValidation.n_splits ?? 10)"
                  @change="patchValidation('n_splits', Number(($event.target as HTMLInputElement).value))"
                >
              </div>
            </template>
            <template v-if="method.value === 'k_fold'">
              <label class="param-checkbox">
                <input
                  :checked="Boolean(localValidation.stratified ?? true)"
                  type="checkbox"
                  @change="patchValidation('stratified', ($event.target as HTMLInputElement).checked)"
                >
                Stratified
              </label>
            </template>
            <template v-if="method.value === 'group_k_fold'">
              <div class="param-pair">
                <span class="param-key">Group column</span>
                <CustomSelect
                  class="param-select"
                  :disabled="datasetColumns.length === 0"
                  :model-value="String(localValidation.group_column ?? '')"
                  :options="datasetColumns.map(c => ({ value: c.name, label: c.name }))"
                  placeholder="選擇欄位"
                  @update:model-value="patchValidation('group_column', $event)"
                />
              </div>
            </template>
            <template v-if="method.value === 'random_sampling'">
              <div class="param-pair">
                <span class="param-key">Repeat train/test</span>
                <input
                  class="param-num"
                  min="1"
                  type="number"
                  :value="Number(localValidation.n_repeats ?? 10)"
                  @change="patchValidation('n_repeats', Number(($event.target as HTMLInputElement).value))"
                >
              </div>
            </template>
            <template v-if="method.value === 'random_sampling' || method.value === 'test_on_train' || method.value === 'test_on_test'">
              <div class="param-pair">
                <span class="param-key">Training set size (%)</span>
                <input
                  class="param-num"
                  max="99"
                  min="1"
                  type="number"
                  :value="Math.round(Number(localValidation.train_size ?? 0.8) * 100)"
                  @change="patchValidation('train_size', Number(($event.target as HTMLInputElement).value) / 100)"
                >
              </div>
              <label class="param-checkbox">
                <input
                  :checked="Boolean(localValidation.stratified ?? true)"
                  type="checkbox"
                  @change="patchValidation('stratified', ($event.target as HTMLInputElement).checked)"
                >
                Stratified
              </label>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Step 4：信賴區間 ── -->
    <div v-else-if="currentStep === 4" class="step-body">
```

同一段（`信賴區間` step-body）結尾找到（第 205-206 行）：

```html
        </div>
      </div>
    </div>

    <div class="settings-footer">
```

不需要改動（`v-else-if="currentStep === 4"` 已經在上一步改好開頭標籤，結尾的 `</div>` 不用動）。

- [ ] **Step 5: style — 新增驗證方式相關 CSS**

在 `<style scoped>` 區塊裡，找到既有的 `.item-params`/`.param-pair`/`.param-key`/`.param-select`/`.param-num` 這組樣式定義（用於前處理分頁的參數列），在其後新增：

```css
  .validation-methods {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .validation-method {
    padding: 8px 10px;
    border-radius: 8px;
  }

  .validation-method__radio {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--color-ink);
    cursor: pointer;
  }

  .validation-method__params {
    margin-top: 8px;
    margin-left: 24px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .param-checkbox {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12.5px;
    color: var(--color-secondary);
    cursor: pointer;
  }
```

- [ ] **Step 6: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/SettingsPanel.vue
git commit -m "feat: add validation method tab to SettingsPanel"
```

---

### Task 3: 前端 — 串接 testScore 節點的 validation 資料

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowOptionsPanel.vue`
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`

**Interfaces:**
- Consumes: Task 2 的 `SettingsPanel.vue` props（`validation`、`datasetColumns`）與 emit（`update-validation`）
- Produces: 無（最終任務，串接到既有的 `handleUpdateConfig`/`nodes` 狀態）

- [ ] **Step 1: `WorkflowOptionsPanel.vue` 新增 props 並傳給 SettingsPanel**

找到 `frontend/src/components/workflow/WorkflowOptionsPanel.vue` 的（第 259-270 行）：

```ts
  const props = defineProps<{
    selectedNode: SimpleNode | null
    file?: File | null
    workflowFileName?: string | null
    workflowSummary?: TestScoreSummary[]
    workflowResult?: Record<string, unknown> | null
    pausedNodeId?: string | null
    drawerStage?: Stage
    availableModels?: string[]
    usedModelNames?: string[]
    modelOptionsLoading?: boolean
  }>()
```

改成：

```ts
  const props = defineProps<{
    selectedNode: SimpleNode | null
    file?: File | null
    workflowFileName?: string | null
    workflowSummary?: TestScoreSummary[]
    workflowResult?: Record<string, unknown> | null
    pausedNodeId?: string | null
    drawerStage?: Stage
    availableModels?: string[]
    usedModelNames?: string[]
    modelOptionsLoading?: boolean
    validationConfig?: Record<string, unknown>
    datasetColumns?: Array<{ name: string, type: string, role: string }>
  }>()
```

找到（第 350-366 行，`settingsModels`/`settingsComputeCi` computed 附近）：

```ts
  const settingsModels = computed(() => {
    const used = props.usedModelNames ?? []
    return used.map(name => ({ name, type: 'Classification' }))
  })

  const settingsComputeCi = computed(() => Boolean(localConfig.compute_ci ?? false))
```

改成（在後面新增兩個 computed）：

```ts
  const settingsModels = computed(() => {
    const used = props.usedModelNames ?? []
    return used.map(name => ({ name, type: 'Classification' }))
  })

  const settingsComputeCi = computed(() => Boolean(localConfig.compute_ci ?? false))

  const settingsValidation = computed(() => props.validationConfig ?? {})
  const settingsDatasetColumns = computed(() => props.datasetColumns ?? [])
```

找到（第 379-383 行，`handleSettingsComputeCiUpdate` 函式）：

```ts
  function handleSettingsComputeCiUpdate (value: boolean): void {
    localConfig.compute_ci = value
    if (!props.selectedNode) return
    emit('update-config', { nodeId: props.selectedNode.id, config: { compute_ci: value } })
  }
```

改成（在後面新增 `handleSettingsValidationUpdate`，注意這裡固定寫 `nodeId: 'testScore'`，跟其他 handler 用 `props.selectedNode.id` 不同）：

```ts
  function handleSettingsComputeCiUpdate (value: boolean): void {
    localConfig.compute_ci = value
    if (!props.selectedNode) return
    emit('update-config', { nodeId: props.selectedNode.id, config: { compute_ci: value } })
  }

  function handleSettingsValidationUpdate (value: Record<string, unknown>): void {
    emit('update-config', { nodeId: 'testScore', config: { validation: value } })
  }
```

找到（第 72-90 行，template 裡的 `<SettingsPanel>` 呼叫）：

```html
        <template v-else-if="selectedNode.id === 'settings'">
          <SettingsPanel
            :available-models="availableModels"
            :compute-ci="settingsComputeCi"
            :feature-engineering="settingsFeatureEngineering"
            :model-options-loading="props.modelOptionsLoading"
            :models="settingsModels"
            :preprocessing="settingsPreprocessing"
            :used-model-names="(props.usedModelNames ?? [])"
            @add-model="name => emit('add-model', name)"
            @back-node="emit('back-node')"
            @continue="emit('continue-settings')"
            @remove-model="name => emit('remove-model', name)"
            @step-change="step => emit('settings-step-change', step)"
            @update-compute-ci="handleSettingsComputeCiUpdate"
            @update-feature-engineering="handleSettingsFEUpdate"
            @update-preprocessing="handleSettingsPreprocessingUpdate"
          />
        </template>
```

改成：

```html
        <template v-else-if="selectedNode.id === 'settings'">
          <SettingsPanel
            :available-models="availableModels"
            :compute-ci="settingsComputeCi"
            :dataset-columns="settingsDatasetColumns"
            :feature-engineering="settingsFeatureEngineering"
            :model-options-loading="props.modelOptionsLoading"
            :models="settingsModels"
            :preprocessing="settingsPreprocessing"
            :used-model-names="(props.usedModelNames ?? [])"
            :validation="settingsValidation"
            @add-model="name => emit('add-model', name)"
            @back-node="emit('back-node')"
            @continue="emit('continue-settings')"
            @remove-model="name => emit('remove-model', name)"
            @step-change="step => emit('settings-step-change', step)"
            @update-compute-ci="handleSettingsComputeCiUpdate"
            @update-feature-engineering="handleSettingsFEUpdate"
            @update-preprocessing="handleSettingsPreprocessingUpdate"
            @update-validation="handleSettingsValidationUpdate"
          />
        </template>
```

- [ ] **Step 2: `WorkflowWorkspace.vue` 算出 testScore/dataTable 的資料並往下傳**

找到 `frontend/src/components/workflow/WorkflowWorkspace.vue` 的（第 255-263 行，`selectedNode`/`availableModelOptions` computed 附近）：

```ts
  const selectedNode = computed(() => {
    if (!selectedNodeId.value) return null
    const node = nodes.value.find(n => n.id === selectedNodeId.value)
    return node ? { id: node.id, data: node.data } : null
  })

  const availableModelOptions = computed<string[]>(() =>
    availableModels.value.filter(name => !usedModelNames.value.includes(name)),
  )
```

改成（在 `selectedNode` 後面新增兩個 computed）：

```ts
  const selectedNode = computed(() => {
    if (!selectedNodeId.value) return null
    const node = nodes.value.find(n => n.id === selectedNodeId.value)
    return node ? { id: node.id, data: node.data } : null
  })

  const testScoreValidationConfig = computed<Record<string, unknown>>(() => {
    const node = nodes.value.find(n => n.id === 'testScore')
    const v = node?.data.config.validation
    return (v && typeof v === 'object') ? (v as Record<string, unknown>) : {}
  })

  const dataTableColumns = computed<Array<{ name: string, type: string, role: string }>>(() => {
    const node = nodes.value.find(n => n.id === 'dataTable')
    const cols = node?.data.config.columnConfig
    return Array.isArray(cols) ? (cols as Array<{ name: string, type: string, role: string }>) : []
  })

  const availableModelOptions = computed<string[]>(() =>
    availableModels.value.filter(name => !usedModelNames.value.includes(name)),
  )
```

找到（第 82-102 行，template 裡的 `<WorkflowOptionsPanel>` 呼叫）：

```html
              <WorkflowOptionsPanel
                :available-models="availableModelOptions"
                :drawer-stage="drawerStage"
                :file="workflowDataFile"
                :model-options-loading="modelOptionsLoading"
                :paused-node-id="pausedAtNodeId"
                :selected-node="selectedNode"
                :used-model-names="usedModelNames"
                :workflow-file-name="workflowDataFile?.name"
                :workflow-result="workflowResult"
                :workflow-summary="workflowSummary"
                @add-model="handleAddModel"
                @apply-column-config="handleApplyColumnConfig"
                @back-node="handleBackToDataTable"
                @continue-settings="handleContinueSettings"
                @open-upload="uploadDialogVisible = true"
                @remove-model="handleRemoveModel"
                @settings-step-change="step => { settingsStep = step }"
                @update-config="handleUpdateConfig"
                @update:file="handleDataFile"
              />
```

改成：

```html
              <WorkflowOptionsPanel
                :available-models="availableModelOptions"
                :dataset-columns="dataTableColumns"
                :drawer-stage="drawerStage"
                :file="workflowDataFile"
                :model-options-loading="modelOptionsLoading"
                :paused-node-id="pausedAtNodeId"
                :selected-node="selectedNode"
                :used-model-names="usedModelNames"
                :validation-config="testScoreValidationConfig"
                :workflow-file-name="workflowDataFile?.name"
                :workflow-result="workflowResult"
                :workflow-summary="workflowSummary"
                @add-model="handleAddModel"
                @apply-column-config="handleApplyColumnConfig"
                @back-node="handleBackToDataTable"
                @continue-settings="handleContinueSettings"
                @open-upload="uploadDialogVisible = true"
                @remove-model="handleRemoveModel"
                @settings-step-change="step => { settingsStep = step }"
                @update-config="handleUpdateConfig"
                @update:file="handleDataFile"
              />
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 4: 人工瀏覽器驗證**

開一個已經有資料表跟框架的專案，進 workflow 頁面，點 `settings` 節點。

Expected:
- 分頁列出現第 5 個「驗證方式」，順序在「模型」跟「信賴區間」之間
- 點進去能看到目前的驗證設定（如果框架萃取時有帶驗證方式，這裡應該直接顯示萃取結果；沒有的話顯示預設的 Cross validation / 10 folds / Stratified）
- 切換 6 種驗證方式，確認對應子參數正確展開/收合（Cross validation → folds+stratified；Cross validation by feature → folds+group column 下拉；Random sampling → repeat+訓練集比例+stratified；Leave one out → 無子參數；Test on train/test data → 訓練集比例+stratified）
- 選「Cross validation by feature」，確認 Group column 下拉選單列出目前資料表的欄位
- 調整任一參數後切到「信賴區間」分頁再切回來，確認剛剛的修改沒有消失
- 執行一次 workflow，開瀏覽器 Network 分頁確認送出的 `validation_config` payload 內容跟畫面上設定的一致

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workflow/WorkflowOptionsPanel.vue frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "feat: wire validation settings tab to testScore node config"
```
