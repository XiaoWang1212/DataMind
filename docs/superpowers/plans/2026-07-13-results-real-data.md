# /workflow → /results 真實資料串接 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** workflow 執行完成後,使用者可以手動點「查看結果」前往 `/results`,看到這次真正的模型訓練結果(取代目前寫死的假資料),且之後隨時重新造訪同一個專案的 `/results` 都能看到同一份結果與 AI 洞察文字。

**Architecture:** 後端在既有的 `PaperRAGService` 新增一個 `generate_insight()` 方法與 `POST /api/rag/insight` 路由,重用既有的 Gemini client 與 `_format_datamind_output()`。前端 `WorkflowWorkspace.vue` 新增「查看結果」按鈕導向 `/results?project=<id>`;`ResultsPage.vue` 改讀 `route.query.project` 並透過既有的 `loadWorkflowStateFromStorage()` 取出該專案的 `workflowResult`,指標卡片與比較表格改為依實際回傳的 metric 名稱動態產生;AI 洞察文字第一次造訪時呼叫新 API,結果存進 localStorage(新增一對獨立的快取函式,不動既有的 workflow state blob)。

**Tech Stack:** 後端 Flask + Gemini(既有 `google.generativeai`);前端 Vue 3 `<script setup lang="ts">` + vue-router,無新依賴。

## Global Constraints

- 本專案**沒有測試框架**(前端無 vitest/jest,後端無 pytest)。後端驗證用真實網路呼叫(比照本次專案先前 arXiv pipeline 的做法,直接呼叫真實 Gemini API);前端驗證用 `npm run type-check` + `npm run lint`,以及用真實後端資料手動核對邏輯(這個 sandbox 沒有瀏覽器自動化工具,無法真的操作 UI 點擊,最後一個 task 用 dev server + curl 做編譯/連線層級的驗證,並用真實資料手動核對計算邏輯)。不要為此計畫引入任何測試框架。
- 專案內有一份真實範例資料 `backend/samples/pycaret_sample/跌倒資料.csv`(對應 `backend/routes/model.py` 的預設 `target_col = "是否跌倒"`),可用來透過 `/api/models/workflow/jobs` 取得一份真實的 `workflowResult`,作為驗證 `/results` 邏輯與 `/api/rag/insight` 的真實資料來源。
- 指標數值一律以 `value.toFixed(3)` 顯示(例如 `0.942`),不做百分比轉換 —— 因為 metric 集合是動態的(可能包含 `mcc`/`kappa` 這類本來就不是比例的指標),統一格式比針對個別 metric 猜測百分比呈現方式更不會出錯。
- Python 檔案沿用現有 4 空白縮排風格(參考 `paper_rag.py`)。Vue 元件風格:`<template>` 在前、`<script setup lang="ts">` 在後、`<style scoped>` 最後,2 空格縮排。
- Commit message 使用英文、慣例式前綴(`feat:`),不加 Co-Authored-By 以外的尾註。
- 所有前端指令在 `frontend/` 目錄下執行;所有後端指令在 `backend/` 目錄下執行。

---

### Task 1: 後端 `generate_insight()` 方法與 `/api/rag/insight` 路由

**Files:**
- Modify: `backend/services/rag/paper_rag.py:325-327`(在 `ingest_arxiv_selection()` 之後、`get_status()` 之前插入新方法)
- Modify: `backend/routes/rag.py`(檔案末尾新增一個 route function)

**Interfaces:**
- Consumes: `PaperRAGService` 既有的 `self._model`(Gemini)、`self._call_gemini()`、`self._format_datamind_output()`
- Produces:
  - `PaperRAGService.generate_insight(mining_results: dict) -> str`,回傳一段繁體中文洞察文字
  - `POST /api/rag/insight`,body `{mining_results: dict}`,回傳 `{success, insight}`

- [ ] **Step 1: 新增 `generate_insight()` 方法**

`backend/services/rag/paper_rag.py` 第 325–327 行,原本:

```python
        return {"success": True, "ingested": ingested, "failed": failed}

    def get_status(self) -> dict:
```

改為:

```python
        return {"success": True, "ingested": ingested, "failed": failed}

    def generate_insight(self, mining_results: dict) -> str:
        """讀 mining_results 摘要，用 Gemini 生成一段繁體中文洞察文字，供 /results 儀表板顯示。"""
        results_text = self._format_datamind_output(mining_results)
        prompt = (
            "你是資料科學顧問。請根據以下機器學習實驗結果，"
            "用繁體中文寫一段簡短的洞察摘要（約 2 到 3 句話），"
            "說明表現最好的模型、關鍵發現，以及是否適合投入實際應用。\n\n"
            f"【機器學習實驗結果】\n{results_text}\n\n"
            "請「只」輸出洞察摘要本身，不要加上任何標題、條列符號或多餘說明文字。"
        )
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        text = self._call_gemini(prompt, usage_total)
        return text.strip()

    def get_status(self) -> dict:
```

- [ ] **Step 2: 在 `backend/routes/rag.py` 末尾新增路由**

檔案末尾新增:

```python


@rag_bp.route("/insight", methods=["POST"])
def generate_insight():
    """根據 DataMind 探勘結果，用 Gemini 生成一段洞察摘要

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）

    回傳：
        - insight : AI 生成的洞察文字
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400

    service = get_paper_rag_service()

    try:
        insight = service.generate_insight(data["mining_results"])
        return jsonify({"success": True, "insight": insight})

    except Exception as e:
        logger.exception("洞察生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 3: 啟動本機 Flask dev server 並用真實資料驗證**

Run(在 `backend/` 目錄下,背景執行):`python app.py`

Run:

```bash
curl -s -X POST http://127.0.0.1:5001/api/rag/insight \
  -H "Content-Type: application/json" \
  -d '{"mining_results": {"results": [{"model_name": "XGBoost", "metrics": [{"metric": "balanced_accuracy", "value": 0.942}, {"metric": "auc", "value": 0.96}]}, {"model_name": "Random Forest", "metrics": [{"metric": "balanced_accuracy", "value": 0.91}, {"metric": "auc", "value": 0.93}]}]}}'
```

Expected: 回傳 JSON,`success: true`,`insight` 是一段非空的繁體中文文字(2–3 句話)。

停止 dev server(終止 Step 3 啟動的背景程序)。

- [ ] **Step 4: Commit**

```bash
git add backend/services/rag/paper_rag.py backend/routes/rag.py
git commit -m "feat: add generate_insight method and /api/rag/insight route"
```

---

### Task 2: 前端洞察文字快取(`useWorkflowStorage.ts`)

**Files:**
- Modify: `frontend/src/composables/workflow/useWorkflowStorage.ts`(檔案末尾新增兩個函式)

**Interfaces:**
- Consumes: 無
- Produces:
  - `saveResultInsightToStorage(projectId: string, insight: string): void`
  - `loadResultInsightFromStorage(projectId: string): string | null`

- [ ] **Step 1: 在檔案末尾新增快取函式**

`frontend/src/composables/workflow/useWorkflowStorage.ts` 檔案末尾(第 157 行之後),新增:

```ts

const RESULT_INSIGHT_KEY = 'resultInsight'

export function saveResultInsightToStorage (projectId: string, insight: string): void {
  const key = k(RESULT_INSIGHT_KEY, projectId)
  try {
    localStorage.setItem(key, insight)
  } catch (error) {
    console.error('[WF-SAVE] 無法儲存洞察文字:', error)
  }
}

export function loadResultInsightFromStorage (projectId: string): string | null {
  const key = k(RESULT_INSIGHT_KEY, projectId)
  return localStorage.getItem(key)
}
```

- [ ] **Step 2: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過,無新錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/workflow/useWorkflowStorage.ts
git commit -m "feat: add per-project result insight cache helpers"
```

---

### Task 3: 前端 `/api/rag/insight` client

**Files:**
- Create: `frontend/src/api/insight.ts`

**Interfaces:**
- Consumes: 無
- Produces: `fetchResultInsight(miningResults: Record<string, unknown>): Promise<string>`

- [ ] **Step 1: 建立 `frontend/src/api/insight.ts`**

```ts
export async function fetchResultInsight (miningResults: Record<string, unknown>): Promise<string> {
  const response = await fetch('/api/rag/insight', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mining_results: miningResults }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return String(result.insight ?? '')
}
```

- [ ] **Step 2: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/insight.ts
git commit -m "feat: add fetchResultInsight API client"
```

---

### Task 4: `WorkflowWorkspace.vue` 新增「查看結果」按鈕

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`

**Interfaces:**
- Consumes: 無
- Produces: 無(頁面互動,無其他 task 依賴)

- [ ] **Step 1: 新增 `useRouter` import 與 `router` 實例**

`frontend/src/components/workflow/WorkflowWorkspace.vue` 第 113 行,原本:

```ts
  import { useRoute } from 'vue-router'
```

改為:

```ts
  import { useRoute, useRouter } from 'vue-router'
```

第 136 行,原本:

```ts
  const route = useRoute()
```

改為:

```ts
  const route = useRoute()
  const router = useRouter()
```

- [ ] **Step 2: 新增按鈕**

`frontend/src/components/workflow/WorkflowWorkspace.vue` 第 14–17 行,原本:

```vue
    />

    <!-- 上傳 model 檔案 dialog -->
    <UploadDialog
```

改為:

```vue
    />

    <button
      v-if="workflowResult"
      class="view-results-btn"
      type="button"
      @click="router.push(`/results?project=${projectId}`)"
    >
      查看結果
    </button>

    <!-- 上傳 model 檔案 dialog -->
    <UploadDialog
```

- [ ] **Step 3: 新增按鈕樣式**

`frontend/src/components/workflow/WorkflowWorkspace.vue` 第 606–626 行(`.execute-workflow-btn` 規則),原本:

```css
  .execute-workflow-btn {
    position: absolute;
    top: 14px;
    right: 120px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(0, 93, 255, 0.18);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #005dff;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }
```

改為(在後方新增 `.view-results-btn` 規則,沿用同樣的浮動圓角按鈕視覺樣式,放在目前沒有其他按鈕佔用的 `right: 14px` 位置):

```css
  .execute-workflow-btn {
    position: absolute;
    top: 14px;
    right: 120px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(0, 93, 255, 0.18);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #005dff;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .view-results-btn {
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(0, 93, 255, 0.18);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #005dff;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .view-results-btn:hover {
    background: rgba(255, 255, 255, 0.92);
  }
```

- [ ] **Step 4: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過

- [ ] **Step 5: 目視驗證**

Run: `npm run dev`(在 `frontend/` 下),開啟 `/workflow`
Expected: 尚未執行 workflow 時「查看結果」按鈕不顯示;若無法在此環境實際跑完整個 workflow(需要上傳 CSV 並等待模型訓練),至少確認頁面正常編譯載入、無 console 錯誤,且按鈕的 `v-if="workflowResult"` 條件在程式碼邏輯上正確(`workflowResult` 初始為 `null`)。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "feat: add view-results button to WorkflowWorkspace"
```

---

### Task 5: `ResultsPage.vue` 讀取真實資料(動態指標卡片、表格、AI 洞察)

**Files:**
- Modify: `frontend/src/views/ResultsPage.vue`(整個 `<script setup>` 與部分 `<template>` 改寫)

**Interfaces:**
- Consumes:
  - `loadWorkflowStateFromStorage`(來自 `@/composables/workflow/useWorkflowStorage`)
  - `saveResultInsightToStorage`/`loadResultInsightFromStorage`(Task 2)
  - `fetchResultInsight`(Task 3,`@/api/insight`)
- Produces: 無(頁面元件,無其他 task 依賴)

**背景:** 後端每個模型的 `metrics` 是使用者在 workflow 裡自己選的,不固定;且沒有逐模型訓練時間資料。表格欄位需要依實際回傳的 metric 名稱動態產生,「訓練時間」欄位直接移除。

- [ ] **Step 1: 改寫 `<template>` 的比較表格與新增空狀態**

`frontend/src/views/ResultsPage.vue` 第 1–103 行(整個 `<template>`),改為:

```vue
<template>
  <section class="results-page">

    <HubSidebar />

    <main class="results-main">
      <header class="results-toolbar">
        <v-btn
          class="back-btn"
          icon="mdi-arrow-left"
          size="small"
          variant="text"
        />

        <div class="toolbar-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="toolbar-tab"
            :class="{ 'toolbar-tab--active': tab.active }"
            type="button"
            @click="setActiveTab(tab.key)"
          >
            <v-icon :icon="tab.icon" size="14" />
            <span>{{ tab.label }}</span>
          </button>
        </div>

        <v-btn
          class="generate-paper-btn"
          color="primary"
          size="small"
          @click="router.push('/paper/sources')"
        >
          生成論文
        </v-btn>
      </header>

      <section v-if="!hasLoaded" class="empty-state">
        載入中...
      </section>

      <section v-else-if="!workflowResult" class="empty-state">
        <p>尚無結果。請先在 workflow 頁面完成執行。</p>
        <v-btn color="primary" size="small" @click="router.push('/workflow')">
          前往 Workflow
        </v-btn>
      </section>

      <template v-else>
        <section class="metric-grid">
          <article
            v-for="card in metricCards"
            :key="card.title"
            class="metric-card"
            :class="{ 'metric-card--accent': card.accent }"
          >
            <p class="metric-title">{{ card.title }}</p>
            <p class="metric-value">{{ card.value }}</p>
            <p class="metric-hint">{{ card.hint }}</p>
          </article>
        </section>

        <section class="insight-card">
          <div class="insight-header">
            <div class="insight-icon-wrap">
              <v-icon icon="mdi-shimmer" size="18" />
            </div>
            <h2 class="insight-title">AI生成洞察</h2>
          </div>

          <p v-if="insightLoading" class="insight-text">正在生成洞察...</p>
          <template v-else-if="insightError">
            <p class="insight-text">洞察生成失敗:{{ insightError }}</p>
            <v-btn size="small" variant="text" @click="loadInsight">重試</v-btn>
          </template>
          <p v-else class="insight-text">{{ insightText }}</p>
        </section>

        <section class="comparison-card">
          <div class="comparison-head">
            <h3>模型效能比較</h3>
            <p>各模型依實際設定的驗證方法訓練</p>
          </div>

          <div class="table-wrap">
            <table class="result-table">
              <thead>
                <tr>
                  <th>模型</th>
                  <th v-for="metric in allMetricNames" :key="metric">
                    {{ metricLabel(metric) }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in modelRows" :key="row.model">
                  <td class="model-name">{{ row.model }}</td>
                  <td
                    v-for="metric in allMetricNames"
                    :key="metric"
                    :class="{ 'score-best': row.best && metric === rankingMetric }"
                  >
                    {{ row.values[metric] }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </main>
  </section>
</template>
```

- [ ] **Step 2: 改寫 `<script setup>`**

`frontend/src/views/ResultsPage.vue` 第 105–195 行(整個 `<script setup>`),改為:

```ts
<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { fetchResultInsight } from '@/api/insight'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import {
    loadResultInsightFromStorage,
    loadWorkflowStateFromStorage,
    saveResultInsightToStorage,
  } from '@/composables/workflow/useWorkflowStorage'

  const route = useRoute()
  const router = useRouter()

  const projectId = computed(() => route.query.project as string | undefined)

  onMounted(() => {
    document.title = 'DataMind'
  })

  interface ToolbarTab {
    key: string
    label: string
    icon: string
    active?: boolean
  }

  const tabs = ref<ToolbarTab[]>([
    { key: 'report', label: '報告', icon: 'mdi-file-document-outline', active: true },
    { key: 'code', label: '程式碼', icon: 'mdi-code-tags', active: false },
  ])

  function setActiveTab (targetKey: ToolbarTab['key']): void {
    for (const tab of tabs.value) {
      tab.active = tab.key === targetKey
    }
  }

  // ─── 讀取真實 workflow 結果 ──────────────────────────────────────────────────

  const workflowResult = ref<Record<string, unknown> | null>(null)
  const hasLoaded = ref(false)

  interface ModelMetric {
    metric: string
    value: number | null
  }

  interface ModelResult {
    model_name: string
    metrics: ModelMetric[]
  }

  const modelResults = computed<ModelResult[]>(() => {
    const raw = workflowResult.value?.results
    if (!Array.isArray(raw)) return []
    return raw
      .filter((r): r is Record<string, unknown> => !!r && typeof r === 'object' && !('error' in r))
      .map(r => ({
        model_name: String(r.model_name ?? 'Unknown'),
        metrics: Array.isArray(r.metrics)
          ? r.metrics.map((m: Record<string, unknown>) => ({
              metric: String(m.metric),
              value: typeof m.value === 'number' ? m.value : null,
            }))
          : [],
      }))
  })

  const METRIC_LABELS: Record<string, string> = {
    accuracy: '準確率',
    balanced_accuracy: '平衡準確率',
    precision: '精準度',
    recall: '召回率',
    specificity: '特異度',
    f1: 'F1 分數',
    auc: 'AUC_ROC',
    auprc: 'AUPRC',
    mcc: 'MCC',
    kappa: 'Kappa',
  }

  const PREFERRED_METRIC_ORDER = [
    'balanced_accuracy', 'accuracy', 'f1', 'auc', 'auprc', 'precision', 'recall', 'specificity', 'mcc', 'kappa',
  ]

  const RANKING_PRIORITY = ['balanced_accuracy', 'accuracy', 'auc']

  function metricLabel (metric: string): string {
    return METRIC_LABELS[metric] ?? metric.toUpperCase()
  }

  function metricValueOf (result: ModelResult, metric: string): number | null {
    return result.metrics.find(m => m.metric === metric)?.value ?? null
  }

  const rankingMetric = computed<string | null>(() => {
    const results = modelResults.value
    if (results.length === 0) return null
    for (const candidate of RANKING_PRIORITY) {
      if (results.every(r => metricValueOf(r, candidate) !== null)) return candidate
    }
    return results[0]?.metrics[0]?.metric ?? null
  })

  const bestResult = computed<ModelResult | null>(() => {
    const metric = rankingMetric.value
    const results = modelResults.value
    if (!metric || results.length === 0) return null
    return results.reduce((best, current) => {
      const bestValue = metricValueOf(best, metric) ?? Number.NEGATIVE_INFINITY
      const currentValue = metricValueOf(current, metric) ?? Number.NEGATIVE_INFINITY
      return currentValue > bestValue ? current : best
    })
  })

  const allMetricNames = computed<string[]>(() => {
    const seen = new Set<string>()
    for (const result of modelResults.value) {
      for (const m of result.metrics) seen.add(m.metric)
    }
    const ordered = PREFERRED_METRIC_ORDER.filter(m => seen.has(m))
    const rest = [...seen].filter(m => !ordered.includes(m))
    return [...ordered, ...rest]
  })

  interface MetricCard {
    title: string
    value: string
    hint: string
    accent?: boolean
  }

  const metricCards = computed<MetricCard[]>(() => {
    const best = bestResult.value
    const ranking = rankingMetric.value
    if (!best || !ranking) return []

    const cards: MetricCard[] = [
      { title: '最佳模型', value: best.model_name, hint: `依 ${metricLabel(ranking)} 排名` },
    ]

    const otherMetrics = allMetricNames.value.filter(m => m !== ranking)
    const cardMetrics = [ranking, ...otherMetrics].slice(0, 3)
    for (const metric of cardMetrics) {
      const value = metricValueOf(best, metric)
      cards.push({
        title: metricLabel(metric),
        value: value === null ? 'N/A' : value.toFixed(3),
        hint: metric,
        accent: metric === ranking,
      })
    }
    return cards
  })

  interface ResultRow {
    model: string
    values: Record<string, string>
    best: boolean
  }

  const modelRows = computed<ResultRow[]>(() => {
    const bestName = bestResult.value?.model_name
    return modelResults.value.map(result => {
      const values: Record<string, string> = {}
      for (const metric of allMetricNames.value) {
        const value = metricValueOf(result, metric)
        values[metric] = value === null ? 'N/A' : value.toFixed(3)
      }
      return {
        model: result.model_name,
        values,
        best: result.model_name === bestName,
      }
    })
  })

  // ─── AI 洞察文字(快取) ───────────────────────────────────────────────────────

  const insightText = ref<string | null>(null)
  const insightLoading = ref(false)
  const insightError = ref<string | null>(null)

  async function loadInsight (): Promise<void> {
    if (!projectId.value || !workflowResult.value) return
    const cached = loadResultInsightFromStorage(projectId.value)
    if (cached) {
      insightText.value = cached
      return
    }
    insightLoading.value = true
    insightError.value = null
    try {
      const insight = await fetchResultInsight(workflowResult.value)
      insightText.value = insight
      saveResultInsightToStorage(projectId.value, insight)
    } catch (error) {
      insightError.value = error instanceof Error ? error.message : String(error)
    } finally {
      insightLoading.value = false
    }
  }

  onMounted(() => {
    const state = loadWorkflowStateFromStorage(projectId.value)
    workflowResult.value = state?.workflowResult ?? null
    hasLoaded.value = true
    if (workflowResult.value) {
      loadInsight()
    }
  })
</script>
```

- [ ] **Step 3: 移除舊的 `insightTags` 樣式殘留(若 lint 提示未使用的 CSS 選取器可略過,`<style>` 區塊本身不需要改動,因為 `.insight-tags`/`.insight-tag` 規則沒有被移除的必要——這兩個 class 已經不再由 template 使用,但保留不影響功能;若你想保持乾淨,可以連同以下步驟一併移除,非必要)**

跳過此步驟(保留現有 `<style scoped>` 不動,`.insight-tags`/`.insight-tag`/`.result-table th:nth-child` 等既有樣式規則沒有語法錯誤,只是部分不再被使用,不影響渲染)。

- [ ] **Step 4: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過,無新錯誤

- [ ] **Step 5: 取得一份真實 workflowResult 作為驗證資料**

Run(在 `backend/` 目錄下,背景執行):`python app.py`

Run:

```bash
python -c "
import json, time, urllib.request

with open('samples/pycaret_sample/跌倒資料.csv', 'rb') as f:
    csv_bytes = f.read()

boundary = '----datamind'
payload = json.dumps({
    'model_names': ['Logistic Regression', 'Random Forest'],
    'validation_config': {'method': 'train_test_split', 'train_size': 0.8, 'test_size': 0.2},
    'score_variants': [{'metric': 'balanced_accuracy'}, {'metric': 'auc'}, {'metric': 'f1'}],
})

body = (
    f'--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"data.csv\"\r\nContent-Type: text/csv\r\n\r\n'
).encode() + csv_bytes + (
    f'\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"workflow_payload\"\r\n\r\n{payload}\r\n--{boundary}--\r\n'
).encode()

req = urllib.request.Request(
    'http://127.0.0.1:5001/api/models/workflow/jobs',
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
)
job = json.loads(urllib.request.urlopen(req, timeout=60).read())
job_id = job['job_id']
print('job_id:', job_id)

for _ in range(60):
    time.sleep(2)
    status = json.loads(urllib.request.urlopen(f'http://127.0.0.1:5001/api/models/workflow/jobs/{job_id}', timeout=30).read())
    print('status:', status['status'], status.get('completed_models'))
    if status['status'] in ('done', 'error'):
        break

with open('/tmp/real_workflow_result.json', 'w', encoding='utf-8') as f:
    json.dump(status.get('result'), f, ensure_ascii=False, indent=2)
print('saved to /tmp/real_workflow_result.json')
"
```

Expected: job 狀態最終變成 `done`,`/tmp/real_workflow_result.json` 存下一份含 `results: [...]` 的真實 JSON(每個模型有 `model_name` 與 `metrics: [{metric, value, ...}]`)。

- [ ] **Step 6: 用真實資料手動核對 `ResultsPage.vue` 的計算邏輯**

這個 sandbox 沒有瀏覽器自動化工具,無法真的把 `/tmp/real_workflow_result.json` 寫進瀏覽器的 localStorage 並截圖驗證渲染結果。改用手動核對邏輯是否正確:

1. 讀 `/tmp/real_workflow_result.json` 的 `results` 陣列,列出每個模型的 `model_name` 與各 `metrics[].metric`。
2. 依 `rankingMetric` 的邏輯(依序檢查 `balanced_accuracy`/`accuracy`/`auc` 是否所有模型都有),手動算出排名 metric 應該是哪一個。
3. 依該 metric 找出數值最高的模型,確認等於 `bestResult` 邏輯應該算出的結果。
4. 確認 `allMetricNames` 會是這次所有模型 `metrics[].metric` 的聯集,且依 `PREFERRED_METRIC_ORDER` 排序。
5. 把上述手動核對結果寫進 report,證明程式邏輯與真實資料一致。

- [ ] **Step 7: dev server 編譯/連線層級驗證**

Run: `npm run dev`(在 `frontend/` 下)

Run:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/results
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:5173/results?project=test"
```

Expected: 皆回傳 200(SPA 皆回傳同一個 shell,主要用來確認 dev server 有正常編譯這次改動、沒有編譯錯誤)。檢查 dev server 的終端機輸出沒有出現這個檔案相關的編譯錯誤。

停止兩個 dev server。

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/ResultsPage.vue
git commit -m "feat: wire ResultsPage to real workflow results and AI insight"
```
