# Workflow 結果頁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓已完成的 workflow job 有一個可回訪的結果頁（`/hub/projects/:id/result`），顯示真實的指標卡與模型比較表，並移除目前完全沒被使用、資料寫死的舊 `/results` 頁面。

**Architecture:** 新頁面直接讀取 `WorkflowWorkspace.vue` 早已在寫入的 `localStorage`（`workflowState_<projectId>` key 裡的 `workflowResult`），不呼叫任何後端 API、不依賴 canvas 是否掛載。模型分組平均指標的邏輯從 `useWorkflowExecution.ts` 抽成獨立純函式，canvas 抽屜與新結果頁共用同一份邏輯。

**Tech Stack:** Vue 3 `<script setup>`、TypeScript、Vue Router、Pinia（`projectStore`）。前端無自動化測試框架（無 vitest/jest），本計畫用 `npm run type-check`（`vue-tsc --build --force`）當自動化把關，其餘用手動瀏覽器驗證。

## Global Constraints

- 本 repo 前端沒有 vitest/jest 等測試框架；每個 task 用 `npm run type-check`（在 `frontend/` 目錄下執行）驗證型別正確，並輔以手動瀏覽器操作驗證行為。這是本計畫對 TDD 步驟結構的唯一調整，其餘步驟仍照「寫程式碼 → 驗證 → commit」的節奏。
- 程式碼風格照被修改檔案「原本」的風格：`frontend/src/router/index.ts` 用雙引號＋分號；其餘 `.vue`/`.ts`（`composables`、`views`、`utils`）一律用單引號、無分號、2 空白縮排、函式簽名 `functionName (args)` 中間留空格（跟現有 `useWorkflowExecution.ts`、`ProjectDetailView.vue` 一致）。
- 不新增訓練時間欄位、不接 AI 生成洞察文字、不回填 `Project.accuracy`/`Project.keyFinding`、不做 job 完成自動導頁 —— 這些都明確排除在本次 spec 範圍外（見 `docs/superpowers/specs/2026-07-15-workflow-result-page-design.md`）。

---

## Task 1: 抽出共用的結果彙總邏輯

**Files:**
- Create: `frontend/src/utils/workflow/summarizeWorkflowResult.ts`
- Modify: `frontend/src/composables/workflow/useWorkflowExecution.ts:1-99`

**Interfaces:**
- Produces: `summarizeWorkflowResult(workflowResult: Record<string, unknown> | null): ModelMetricSummary[]`，以及匯出型別 `ModelMetricSummary { model_name: string, split_name: string, metrics: { metric: string, valueFormatted: string }[], errors: Record<string, string> }`。這是 Task 2（`ResultView.vue`）唯一需要 import 的介面。

- [ ] **Step 1: 建立 `summarizeWorkflowResult.ts`**

把 `useWorkflowExecution.ts` 裡 `workflowSummary` computed 的邏輯原封不動搬進來（不改變任何行為，只是換成可重用的純函式）：

```ts
export interface ModelMetricSummary {
  model_name: string
  split_name: string
  metrics: { metric: string, valueFormatted: string }[]
  errors: Record<string, string>
}

export function summarizeWorkflowResult (
  workflowResult: Record<string, unknown> | null,
): ModelMetricSummary[] {
  if (!workflowResult) return []
  const results = Array.isArray(workflowResult.results)
    ? workflowResult.results
    : []

  const modelGroups = new Map<string, { count: number, metrics: Record<string, number[]>, errors: Record<string, string> }>()

  for (const result of results.filter((r: any) => r && typeof r === 'object')) {
    const modelName = result.model_name || 'unknown'
    const existing = modelGroups.get(modelName) ?? { count: 0, metrics: {}, errors: {} }

    if (Array.isArray(result.metrics)) {
      for (const metric of result.metrics) {
        const name = metric.metric || 'unknown'
        if (metric?.error) { existing.errors[name] = metric.error; continue }
        const value = Number(metric.value)
        if (!Number.isNaN(value)) {
          existing.metrics[name] = existing.metrics[name] ?? []
          existing.metrics[name].push(value)
        }
      }
    }
    existing.count += 1
    modelGroups.set(modelName, existing)
  }

  return Array.from(modelGroups.entries()).map(([modelName, group]) => ({
    model_name: modelName,
    split_name: `${group.count} splits`,
    metrics: Object.entries(group.metrics).map(([metric, values]) => ({
      metric,
      valueFormatted: values.length > 0
        ? (values.reduce((s, v) => s + v, 0) / values.length).toFixed(4)
        : 'N/A',
    })),
    errors: group.errors,
  }))
}
```

（`errors` 型別從原本內部隱含的 `Record<string, string[]>` 改標成 `Record<string, string>`——這跟原本 `existing.errors[name] = metric.error` 實際賦值的型別一致，只是修正型別標註，賦值邏輯本身完全沒變。）

- [ ] **Step 2: 修改 `useWorkflowExecution.ts` 的 import**

Modify `frontend/src/composables/workflow/useWorkflowExecution.ts:1-5`:

Old:
```ts
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { executeWorkflowApi, fetchWorkflowJob, startWorkflowJob } from '@/api/workflow'
import type { DemoStep } from '@/constants/workflowData'
import type { FlowNode } from '@/types/workflow'
```

New:
```ts
import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { executeWorkflowApi, fetchWorkflowJob, startWorkflowJob } from '@/api/workflow'
import type { DemoStep } from '@/constants/workflowData'
import type { FlowNode } from '@/types/workflow'
import { summarizeWorkflowResult } from '@/utils/workflow/summarizeWorkflowResult'
```

- [ ] **Step 3: 把 `workflowSummary` computed 換成呼叫共用函式**

Modify `frontend/src/composables/workflow/useWorkflowExecution.ts`（原本的 `workflowSummary` computed 區塊，約在 import 之後第 61-99 行）：

Old:
```ts
  const workflowSummary = computed(() => {
    if (!workflowResult.value) return []
    const results = Array.isArray(workflowResult.value.results)
      ? workflowResult.value.results
      : []

    const modelGroups = new Map<string, { count: number; metrics: Record<string, number[]>; errors: Record<string, string[]> }>()

    for (const result of results.filter((r: any) => r && typeof r === 'object')) {
      const modelName = result.model_name || 'unknown'
      const existing = modelGroups.get(modelName) ?? { count: 0, metrics: {}, errors: {} }

      if (Array.isArray(result.metrics)) {
        for (const metric of result.metrics) {
          const name = metric.metric || 'unknown'
          if (metric?.error) { existing.errors[name] = metric.error; continue }
          const value = Number(metric.value)
          if (!Number.isNaN(value)) {
            existing.metrics[name] = existing.metrics[name] ?? []
            existing.metrics[name].push(value)
          }
        }
      }
      existing.count += 1
      modelGroups.set(modelName, existing)
    }

    return Array.from(modelGroups.entries()).map(([modelName, group]) => ({
      model_name: modelName,
      split_name: `${group.count} splits`,
      metrics: Object.entries(group.metrics).map(([metric, values]) => ({
        metric,
        valueFormatted: values.length > 0
          ? (values.reduce((s, v) => s + v, 0) / values.length).toFixed(4)
          : 'N/A',
      })),
      errors: group.errors,
    }))
  })
```

New:
```ts
  const workflowSummary = computed(() => summarizeWorkflowResult(workflowResult.value))
```

- [ ] **Step 4: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤輸出（跟修改前的 baseline 一致，這個 repo 目前 type-check 是乾淨的）。

- [ ] **Step 5: 手動驗證行為沒有改變**

Run: `cd frontend && npm run dev`，瀏覽器開 `http://localhost:5173/hub/projects`，任意開一個曾經跑過 workflow 的專案 → 「在 Workflow 中開啟」→ 點選 Test Score 節點，確認下方抽屜的模型比較表跟修改前長得一樣（因為邏輯完全沒變，只是搬了位置）。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/utils/workflow/summarizeWorkflowResult.ts frontend/src/composables/workflow/useWorkflowExecution.ts
git commit -m "refactor: extract summarizeWorkflowResult into shared utility"
```

---

## Task 2: 新增 ResultView.vue 頁面元件

**Files:**
- Create: `frontend/src/views/hub/ResultView.vue`

**Interfaces:**
- Consumes: `summarizeWorkflowResult(workflowResult): ModelMetricSummary[]`、`ModelMetricSummary` 型別（Task 1 產出，`@/utils/workflow/summarizeWorkflowResult`）；`useProjectStore()` 的 `projects` state（`@/store/projectStore`，欄位 `id: string, name: string, frameworkName: string`）；`loadWorkflowStateFromStorage(projectId?: string)`（`@/composables/workflow/useWorkflowStorage`，回傳物件含 `workflowResult?: Record<string, unknown> | null`）。
- Produces: 元件本身不對外匯出任何介面，是路由的葉節點頁面。Task 3 會把它掛到路由上。

此元件這一步先不接路由（下一個 task 才接線），所以本步驟先用型別檢查驗證，瀏覽器手動驗證留到 Task 3（那時候路由才走得到這個頁面）。

- [ ] **Step 1: 建立 `frontend/src/views/hub/ResultView.vue`**

```vue
<template>
  <div>
    <RouterLink class="back-link" :to="`/hub/projects/${projectId}`">
      <v-icon icon="mdi-arrow-left" size="15" />
      返回專案
    </RouterLink>

    <div v-if="project" class="page-header">
      <h1 class="page-title">{{ project.name }}</h1>
      <p class="page-sub">結果總覽 · 框架：{{ project.frameworkName }}</p>
    </div>

    <div v-if="!project" class="not-found">找不到該專案</div>

    <template v-else-if="summary.length === 0">
      <div class="empty-state">
        <p class="empty-text">尚未有可用結果</p>
        <RouterLink class="open-workflow-btn" :to="`/workflow?project=${projectId}`">
          <v-icon icon="mdi-sitemap-outline" size="16" />
          在 Workflow 中開啟
        </RouterLink>
      </div>
    </template>

    <template v-else>
      <section class="metric-grid">
        <article
          v-for="card in metricCards"
          :key="card.key"
          class="metric-card"
          :class="{ 'metric-card--accent': card.accent }"
        >
          <p class="metric-title">{{ card.title }}</p>
          <p class="metric-value">{{ card.value }}</p>
          <p class="metric-hint">{{ card.hint }}</p>
        </article>
      </section>

      <section class="comparison-card">
        <div class="comparison-head">
          <h3>模型效能比較</h3>
        </div>

        <div class="table-wrap">
          <table class="result-table">
            <thead>
              <tr>
                <th>模型</th>
                <th v-for="metric in metricNames" :key="metric">{{ metric }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in summary" :key="row.model_name">
                <td class="model-name">{{ row.model_name }}</td>
                <td
                  v-for="metric in metricNames"
                  :key="metric"
                  :class="{ 'score-best': row.model_name === bestModelName && metric === metricNames[0] }"
                >{{ metricValue(row, metric) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { RouterLink, useRoute } from 'vue-router'
  import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { useProjectStore } from '@/store/projectStore'
  import { summarizeWorkflowResult, type ModelMetricSummary } from '@/utils/workflow/summarizeWorkflowResult'

  interface MetricCard {
    key: string
    title: string
    value: string
    hint: string
    accent?: boolean
  }

  const route = useRoute()
  const store = useProjectStore()

  const projectId = computed(() => route.params.id as string)

  const project = computed(() =>
    store.projects.find(p => p.id === projectId.value),
  )

  const summary = computed<ModelMetricSummary[]>(() => {
    const state = loadWorkflowStateFromStorage(projectId.value)
    return summarizeWorkflowResult(state?.workflowResult ?? null)
  })

  const metricNames = computed(() => {
    const names: string[] = []
    for (const row of summary.value) {
      for (const m of row.metrics) {
        if (!names.includes(m.metric)) names.push(m.metric)
      }
    }
    return names
  })

  function bestModelFor (metric: string): { model_name: string, valueFormatted: string } | null {
    let best: { model_name: string, valueFormatted: string, value: number } | null = null
    for (const row of summary.value) {
      const entry = row.metrics.find(m => m.metric === metric)
      if (!entry) continue
      const value = Number(entry.valueFormatted)
      if (Number.isNaN(value)) continue
      if (!best || value > best.value) {
        best = { model_name: row.model_name, valueFormatted: entry.valueFormatted, value }
      }
    }
    return best ? { model_name: best.model_name, valueFormatted: best.valueFormatted } : null
  }

  const bestModelName = computed(() => {
    if (metricNames.value.length === 0) return null
    return bestModelFor(metricNames.value[0]!)?.model_name ?? null
  })

  const metricCards = computed<MetricCard[]>(() => {
    if (metricNames.value.length === 0) return []
    const primaryMetric = metricNames.value[0]!
    const best = bestModelFor(primaryMetric)

    const cards: MetricCard[] = [
      {
        key: 'best-model',
        title: '最佳模型',
        value: best?.model_name ?? '—',
        hint: best ? `${primaryMetric}: ${best.valueFormatted}` : '',
        accent: true,
      },
    ]

    for (const metric of metricNames.value.slice(0, 3)) {
      const metricBest = bestModelFor(metric)
      cards.push({
        key: metric,
        title: metric,
        value: metricBest?.valueFormatted ?? '—',
        hint: metricBest?.model_name ?? '',
      })
    }

    return cards.slice(0, 4)
  })

  function metricValue (row: ModelMetricSummary, metric: string): string {
    const entry = row.metrics.find(m => m.metric === metric)
    if (entry) return entry.valueFormatted
    if (row.errors[metric]) return '錯誤'
    return '—'
  }
</script>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #6b7280;
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: #111827;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: #9ca3af;
  margin: 0;
}

.not-found {
  text-align: center;
  padding: 48px;
  color: #9ca3af;
  font-size: 14px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 64px 24px;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
}

.empty-text {
  margin: 0;
  font-size: 14px;
  color: #9ca3af;
}

.open-workflow-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: background 0.15s;
}

.open-workflow-btn:hover {
  background: #1b3ca0;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  padding: 14px;
}

.metric-card--accent .metric-value {
  color: #18a836;
}

.metric-title {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  color: #20232a;
}

.metric-value {
  margin: 8px 0 2px;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.15;
  color: #111827;
}

.metric-hint {
  margin: 0;
  font-size: 12px;
  color: #6f7480;
}

.comparison-card {
  margin-top: 16px;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  background: #ffffff;
  overflow: hidden;
}

.comparison-head {
  padding: 14px 18px;
  border-bottom: 1px solid #f0f1f3;
}

.comparison-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.table-wrap {
  overflow: auto;
}

.result-table {
  width: 100%;
  min-width: 480px;
  border-collapse: collapse;
}

.result-table th,
.result-table td {
  padding: 11px 18px;
  text-align: left;
  border-bottom: 1px solid #f0f1f3;
  font-size: 12px;
  white-space: nowrap;
}

.result-table th {
  font-weight: 700;
  color: #2a2f39;
  background: #fafbff;
}

.result-table tbody tr:last-child td {
  border-bottom: none;
}

.model-name {
  font-weight: 700;
  color: #1f2532;
}

.score-best {
  color: #18a836;
  font-weight: 700;
}

@media (max-width: 1260px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤輸出。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/hub/ResultView.vue
git commit -m "feat: add ResultView page for viewing workflow results"
```

---

## Task 3: 接上路由、移除舊的 /results 死頁面

**Files:**
- Modify: `frontend/src/router/index.ts`
- Delete: `frontend/src/views/ResultsPage.vue`

**Interfaces:**
- Consumes: Task 2 產出的 `frontend/src/views/hub/ResultView.vue`（本 task 把它掛到 `/hub/projects/:id/result`）。
- Produces: 路由 `hub-project-result`，path `/hub/projects/:id/result`。Task 4 的 `RouterLink` 會指到這個 path。

- [ ] **Step 1: 移除 `/results` 路由**

Modify `frontend/src/router/index.ts`：

Old:
```ts
    {
      path: "/sidebar",
      name: "sidebar",
      component: () => import("@/components/Sidebar.vue"),
    },
    {
      path: "/results",
      name: "results",
      component: () => import("@/views/ResultsPage.vue"),
    },
    {
      path: "/hub",
```

New:
```ts
    {
      path: "/sidebar",
      name: "sidebar",
      component: () => import("@/components/Sidebar.vue"),
    },
    {
      path: "/hub",
```

- [ ] **Step 2: 新增 `/hub/projects/:id/result` 子路由**

Modify `frontend/src/router/index.ts`（`/hub` 的 `children` 陣列裡）：

Old:
```ts
        {
          path: "projects/:id",
          name: "hub-project-detail",
          component: () => import("@/views/hub/ProjectDetailView.vue"),
        },
        {
          path: "settings",
          name: "hub-settings",
          component: () => import("@/views/hub/SettingsView.vue"),
        },
```

New:
```ts
        {
          path: "projects/:id",
          name: "hub-project-detail",
          component: () => import("@/views/hub/ProjectDetailView.vue"),
        },
        {
          path: "projects/:id/result",
          name: "hub-project-result",
          component: () => import("@/views/hub/ResultView.vue"),
        },
        {
          path: "settings",
          name: "hub-settings",
          component: () => import("@/views/hub/SettingsView.vue"),
        },
```

- [ ] **Step 3: 刪除 `ResultsPage.vue`**

```bash
rm frontend/src/views/ResultsPage.vue
```

- [ ] **Step 4: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤輸出（確認刪除 `ResultsPage.vue` 後沒有任何殘留引用它的地方壞掉）。

- [ ] **Step 5: 手動驗證路由**

Run: `cd frontend && npm run dev`，瀏覽器操作：
1. 開 `http://localhost:5173/results` → 確認變成 404（不再是舊的假資料頁）。
2. 開 `http://localhost:5173/hub/projects/1`（或任一存在的 project id）→ 直接改網址列到 `.../result` → 確認能進入新頁面，不會噴錯（此時因為 Task 4 還沒接按鈕，直接改網址列進去即可）。若這個 project 沒有 `workflowResult`，應該看到「尚未有可用結果」空狀態。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/router/index.ts
git rm frontend/src/views/ResultsPage.vue
git commit -m "feat: route /hub/projects/:id/result to ResultView, remove dead /results page"
```

---

## Task 4: ProjectDetailView 新增「查看完整結果」入口

**Files:**
- Modify: `frontend/src/views/hub/ProjectDetailView.vue`

**Interfaces:**
- Consumes: Task 3 產出的路由 path `/hub/projects/:id/result`。

- [ ] **Step 1: 在「分析結果」卡片的完成狀態區塊加入按鈕**

Modify `frontend/src/views/hub/ProjectDetailView.vue`：

Old:
```html
        <!-- Completed -->
        <template v-if="project.status === 'completed'">
          <div class="result-row">
            <div class="result-label">模型準確率</div>
            <div class="result-value large">{{ project.accuracy }}</div>
          </div>
          <div class="result-divider" />
          <div class="result-row">
            <div class="result-label">關鍵發現</div>
            <div class="result-value">{{ project.keyFinding }}</div>
          </div>
        </template>
```

New:
```html
        <!-- Completed -->
        <template v-if="project.status === 'completed'">
          <div class="result-row">
            <div class="result-label">模型準確率</div>
            <div class="result-value large">{{ project.accuracy }}</div>
          </div>
          <div class="result-divider" />
          <div class="result-row">
            <div class="result-label">關鍵發現</div>
            <div class="result-value">{{ project.keyFinding }}</div>
          </div>
          <div class="result-divider" />
          <RouterLink class="view-result-btn" :to="`/hub/projects/${project.id}/result`">
            查看完整結果
            <v-icon icon="mdi-arrow-right" size="14" />
          </RouterLink>
        </template>
```

- [ ] **Step 2: 加上對應的 CSS（次要按鈕風格，跟 `.open-workflow-btn` 區隔）**

Modify `frontend/src/views/hub/ProjectDetailView.vue`（`<style scoped>` 區塊，緊接在 `.result-value.large` 規則之後加入新規則）：

Old:
```css
.result-value.large {
  font-size: 30px;
  font-weight: 700;
}
```

New:
```css
.result-value.large {
  font-size: 30px;
  font-weight: 700;
}

.view-result-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding-top: 14px;
  font-size: 13.5px;
  font-weight: 500;
  color: #2347c5;
  text-decoration: none;
}

.view-result-btn:hover {
  color: #1b3ca0;
}
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤輸出。

- [ ] **Step 4: 手動驗證**

Run: `cd frontend && npm run dev`，瀏覽器開一個 `status: 'completed'` 的專案（`/hub/projects/1`，若用預設種子資料，id `'1'` 的「市場情緒研究」就是 completed），確認：
1. 「分析結果」卡片裡看得到新的「查看完整結果 →」連結
2. 點下去會導到 `/hub/projects/1/result`
3. 因為這個種子專案的 `workflowResult` 從沒被寫進 localStorage 過，會看到「尚未有可用結果」空狀態——這是預期行為，不是 bug（種子資料本來就沒跑過真的 workflow job）
4. 對一個真的跑過 workflow job 的專案重複同樣操作，確認指標卡與比較表顯示正確的真實資料

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/hub/ProjectDetailView.vue
git commit -m "feat: add link to full results page from project detail view"
```

---

## Self-Review Notes

- **Spec coverage**：spec 的五個「做」項目（新頁面、指標卡+比較表、抽出共用彙總邏輯、ProjectDetailView 入口、移除死頁面）分別對應 Task 2、Task 2、Task 1、Task 4、Task 3。「不做」清單（訓練時間、AI 洞察、accuracy/keyFinding 回填、自動導頁）都沒有出現在任何 task 裡，符合排除範圍。
- **型別一致性**：`ModelMetricSummary` 在 Task 1 定義，Task 2 原樣 import 使用，欄位名稱（`model_name` / `split_name` / `metrics` / `errors`）前後一致；`summarizeWorkflowResult` 的函式簽名在兩個 task 裡完全相同。
- **無佔位符**：所有 step 都是可直接執行的完整程式碼或指令，沒有「之後補」「視情況處理」這類字眼。
