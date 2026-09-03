# Workflow 評估指標選擇 Design Spec

## 背景

Workflow 的「Test & Score」節點（`frontend/src/constants/workflowData.ts`）節點描述文字寫的是「切分資料、選擇評估指標」，config 也確實有一個 `metrics: string[]` 欄位（預設 `["balanced_accuracy", "auc", "auprc", "mcc", "f1"]`）。但 `SettingsPanel.vue` 從頭到尾沒有任何 UI 讓使用者調整這個陣列——它的值只能來自兩個地方：新建 workflow 時的硬寫預設，或是「提取新框架」時 Gemini 從論文抽出來的 `metrics` 清單（`backend/services/gemini_service.py`）。一旦進到 workflow，這份清單就固定死了。

後端其實已經支援任意組合：`backend/services/workflow/test_score_service.py` 的 `SUPPORTED_METRICS` 有 10 種指標（accuracy、balanced_accuracy、precision、recall、specificity、f1、mcc、kappa、auc、auprc，全部「越高越好」，沒有反向指標），`evaluate_metrics()` 逐一計算，結果會顯示在 `TestScorePanel.vue`（Score Summary 表格）、`ConfusionMatrixPanel.vue`（各分頁）、`ComputeCiPanel.vue`（Bootstrap CI 森林圖）。缺的只是前端這一塊選擇 UI。

## 範圍

- 前端：`SettingsPanel.vue` 的 Step 3（驗證方式）新增一個「評估指標」勾選區塊，10 個指標用 `AppCheckbox` 呈現
- 前端：把這個新的 `metrics` 設定值一路往上傳到 `WorkflowWorkspace.vue`，走跟「驗證方式」完全一樣的 `update-config` → `handleUpdateConfig()` gating 路徑
- **不**新增 Step，整合進現有 Step 3
- **不**動後端——`SUPPORTED_METRICS`/`evaluate_metrics()` 已經支援任意子集，不需要改
- **不**動框架抽取邏輯（`gemini_service.py` 產生的 `metrics` 依然是初始預設值的來源之一，只是現在使用者進到 workflow 後可以再調整）

## 資料流與元件改動

### 1. `SettingsPanel.vue`

**Props 新增**：
```typescript
metrics: string[]
```

**Emits 新增**：
```typescript
(e: 'update-metrics', value: string[]): void
```

**指標對照表**（新增常數，放在其他 LABELS 常數附近）：
```typescript
const METRIC_LABELS: Record<string, string> = {
  accuracy: '準確率',
  balanced_accuracy: '平衡準確率',
  precision: '精準度',
  recall: '召回率',
  f1: 'F1 分數',
  auc: 'AUC_ROC',
  auprc: 'AUPRC',
  specificity: '特異度',
  mcc: 'MCC',
  kappa: 'Kappa 係數',
}

const METRIC_KEYS = Object.keys(METRIC_LABELS)
```

**本地狀態**：比照現有 `localValidation` 的寫法——`localMetrics` 是本地可變陣列，`watch(() => props.metrics, ...)` 同步外部變化進來（例如切換節點又切回來）。

```typescript
const localMetrics = ref<string[]>([...props.metrics])

watch(
  () => props.metrics,
  v => {
    localMetrics.value = [...v]
  },
)
```

**切換函式**：
```typescript
function toggleMetric (key: string): void {
  const next = localMetrics.value.includes(key)
    ? localMetrics.value.filter(m => m !== key)
    : [...localMetrics.value, key]
  if (next.length === 0) return // 至少留一個，最後一個 checkbox 的 UI 會 disable 掉，這裡是雙保險
  localMetrics.value = next
  emit('update-metrics', next)
}
```

**Template**：在現有 Step 3（第 214-303 行）的 `.validation-methods` 區塊（第 215-302 行）之後、`</div>`（第 303 行，Step 3 的結尾）之前，新增：
```html
<div class="metric-section">
  <div class="metric-section__title">評估指標</div>
  <div class="metric-grid">
    <label
      v-for="key in METRIC_KEYS"
      :key="key"
      class="metric-item"
    >
      <AppCheckbox
        :aria-label="METRIC_LABELS[key]"
        :disabled="localMetrics.length === 1 && localMetrics.includes(key)"
        :model-value="localMetrics.includes(key)"
        @update:model-value="toggleMetric(key)"
      />
      {{ METRIC_LABELS[key] }}
    </label>
  </div>
</div>
```
`AppCheckbox` 是 `@/components/ui/AppCheckbox.vue`（`v-model:boolean`、`disabled`、`ariaLabel` props），要在 `<script setup>` 新增 import。

**樣式**：新增 `.metric-section`（`margin-top: 16px`，跟 `.validation-methods` 隔開）、`.metric-section__title`（`font-size: 12px; font-weight: 500; color: var(--color-ink-soft); margin-bottom: 8px;`，比照 SettingsPanel 既有小標字級）、`.metric-grid`（`display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;`，兩欄排列，10 個指標排 5 列）、`.metric-item`（`display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--color-text); cursor: pointer;`，比照 `.param-checkbox` 的字級）。

### 2. `WorkflowOptionsPanel.vue`

**Props 新增**：
```typescript
metricsConfig?: string[]
```

**新增 computed**（比照 `settingsValidation`）：
```typescript
const settingsMetrics = computed(() => props.metricsConfig ?? [])
```

**`<SettingsPanel>` 呼叫新增**：
```html
:metrics="settingsMetrics"
...
@update-metrics="handleSettingsMetricsUpdate"
```

**新增 handler**（比照 `handleSettingsValidationUpdate`）：
```typescript
function handleSettingsMetricsUpdate (value: string[]): void {
  emit('update-config', { nodeId: 'testScore', config: { metrics: value } })
}
```

### 3. `WorkflowWorkspace.vue`

**新增 computed**（比照 `testScoreValidationConfig`）：
```typescript
const testScoreMetricsConfig = computed<string[]>(() => {
  const node = nodes.value.find(n => n.id === 'testScore')
  const m = node?.data.config.metrics
  return Array.isArray(m) ? m as string[] : []
})
```

**`<WorkflowOptionsPanel>` 呼叫新增**：
```html
:metrics-config="testScoreMetricsConfig"
```

### 中斷確認 / gating

`nodeId: 'testScore'` 已經在 `GATED_NODE_IDS` 裡（`WorkflowWorkspace.vue` 的 `handleUpdateConfig()`），跟「驗證方式」走一模一樣的路徑：有既有結果時改動會跳中斷確認對話框，取消會用 `panelResetKey` 重新掛載面板還原成目前存的值（`localMetrics` 的 `watch` 會在重新掛載時吃到新的 `props.metrics` 重新同步，不用額外處理）。這條路徑完全不用改，新功能自動繼承這個行為。

## 錯誤處理 / 邊界情況

- 至少要選 1 個：`toggleMetric()` 擋掉會讓陣列變空的取消動作；最後一個仍勾著的 checkbox 額外用 `:disabled` 擋掉，讓使用者在按下去之前就看得出「這個不能取消」，而不是按了沒反應才發現
- `props.metrics` 傳進來是空陣列或 `undefined`（理論上不該發生，因為預設值一定有東西）：`localMetrics` 會是空陣列，UI 上 10 個都不勾——不特別防呆，因為 `toggleMetric()` 加回任何一個都會讓陣列變成 1 個以上，之後正常運作
- 框架抽取出的 `metrics` 裡有 `SUPPORTED_METRICS` 沒有的 key（理論上不會，Gemini prompt 已經限定只能從這 10 種選）：`METRIC_LABELS` 對照不到的 key 不會出現在勾選列表裡，但如果它殘留在 `localMetrics`/`props.metrics` 裡也不影響——後端 `evaluate_metrics()` 本來就會把不支援的 metric 標記 `error` 略過，不會讓整個 workflow 掛掉

## 測試

- 前端無 vitest，用 `npm run type-check` 做語法/型別檢查
- 人工瀏覽器驗證：
  1. 開一個還沒有 workflow 結果的專案，進 Settings 節點 Step 3，確認「評估指標」區塊顯示，勾選狀態符合目前 `testScore.config.metrics`（預設或框架抽取來的）
  2. 勾掉一個指標、勾上一個沒勾過的指標，執行 workflow，確認 `ConfusionMatrixPanel.vue`/`TestScorePanel.vue`/`ComputeCiPanel.vue` 顯示的指標確實跟著變
  3. 只留最後一個指標時，確認它的 checkbox 變成 disabled、點了沒反應
  4. 已經有 workflow 結果的專案，改動評估指標，確認跳出中斷確認對話框；取消後確認勾選狀態還原成改動前的樣子（沒有殘留使用者改一半的狀態）；確認後確認結果被清空、可以重新執行
  5. 提取一個框架、建立專案進到 workflow，確認 Step 3 一開始的勾選狀態符合框架抽取出的 `metrics`（不是硬寫預設）
