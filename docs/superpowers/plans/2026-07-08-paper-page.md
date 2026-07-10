# 論文生成前端(PaperPage)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在獨立路由 `/paper` 建立論文檢視頁:論文內文含黃底引用標注,右側「來源文獻 + 檢索片段」側欄,雙向連動,全部使用假資料。

**Architecture:** 純前端、無後端呼叫。假資料與型別放在 `constants/reportData.ts`;`PaperPage.vue` 為頁面容器(Sidebar + 內文 + 側欄)持有 `activeCitationId` 狀態;`PaperSection.vue` 渲染章節與可點擊 highlight;`CitationPanel.vue` 渲染文獻卡片。不修改任何現有元件。

**Tech Stack:** Vue 3 `<script setup lang="ts">` + Vuetify(僅用 `v-btn`/`v-icon`)+ vue-router + scoped CSS(沿用 ResultsPage 的 CSS 變數風格)。

## Global Constraints

- 本專案**沒有測試框架**(package.json 無 vitest/jest)。每個 task 的驗證使用:`npm run type-check`、`npm run lint`,最後一個 task 加上 dev server 目視驗證。不要為此計畫引入測試框架。
- 所有指令在 `frontend/` 目錄下執行。
- 元件風格:`<template>` 在前、`<script setup lang="ts">` 在後、`<style scoped>` 最後,縮排 2 空格(參考 `frontend/src/views/ResultsPage.vue`)。
- 介面文案使用繁體中文,與現有頁面一致。
- 不修改 `ResultsPage.vue`、`Sidebar.vue` 或任何現有檔案(router 除外,只新增一條路由)。
- Commit message 使用英文、慣例式前綴(feat:),不加 Co-Authored-By 以外的尾註。

---

### Task 1: 假資料模型與內容(reportData.ts)

**Files:**
- Create: `frontend/src/constants/reportData.ts`

**Interfaces:**
- Consumes: 無
- Produces:
  - `interface Citation { id: string; title: string; authors: string; journal: string; year: number; snippet: string }`
  - `interface PaperSegment { text: string; citationId?: string }`
  - `interface PaperSection { heading: string; paragraphs: PaperSegment[][] }`(一個 section 有多個段落,每個段落是 segment 陣列)
  - `interface PaperReport { title: string; sections: PaperSection[]; citations: Citation[] }`
  - `const mockPaperReport: PaperReport`(具名匯出)

- [ ] **Step 1: 建立檔案與完整內容**

建立 `frontend/src/constants/reportData.ts`:

```ts
export interface Citation {
  id: string
  title: string
  authors: string
  journal: string
  year: number
  snippet: string
}

export interface PaperSegment {
  text: string
  citationId?: string
}

export interface PaperSection {
  heading: string
  paragraphs: PaperSegment[][]
}

export interface PaperReport {
  title: string
  sections: PaperSection[]
  citations: Citation[]
}

export const mockPaperReport: PaperReport = {
  title: '基於機器學習之電信客戶流失預測研究',
  citations: [
    {
      id: 'cite-1',
      title: 'Benchmarking Machine Learning Algorithms for Telecom Churn Prediction',
      authors: 'Chen, W., & Smith, J.',
      journal: 'International Journal of Data Science, 12(4)',
      year: 2023,
      snippet:
        '“...Our empirical comparison demonstrates that gradient boosting frameworks (specifically XGBoost) consistently outperform SVM. Their superiority is attributed to their robustness in handling mixed data types and modeling non-linear interactions...”',
    },
    {
      id: 'cite-2',
      title: 'Switching Costs and Customer Loyalty in Subscription-Based Markets',
      authors: 'Kumar, A., & Lee, D.',
      journal: 'Journal of Marketing Analytics, 8(2)',
      year: 2024,
      snippet:
        '“...Customers under long-term contracts exhibit significantly lower churn propensity, as contractual switching costs reinforce retention even when short-term satisfaction fluctuates...”',
    },
  ],
  sections: [
    {
      heading: '4.1 模型效能評估 (Model Performance Evaluation)',
      paragraphs: [
        [
          {
            text: '本研究採用分層十折交叉驗證 (Stratified 10-Fold Cross-Validation) 對三種異質模型進行了嚴謹的基準測試。實驗結果顯示,XGBoost 模型在各項關鍵指標上均優於隨機森林 (Random Forest) 與支持向量機 (SVM),其準確率 (Accuracy) 達到 94.2%,F1-Score 為 0.92。相較之下,SVM 在處理類別不平衡數據時表現較弱,Recall 僅為 0.76。',
          },
          {
            text: '這項結果與近期文獻一致,指出梯度提升決策樹 (GBDT) 演算法由於具備處理特徵間複雜非線性交互作用的能力,在結構化表格數據 (Tabular Data) 的分類任務中,通常能提供比傳統統計模型更穩健的預測能力 [1]。',
            citationId: 'cite-1',
          },
          {
            text: '因此,本系統最終選擇 XGBoost 作為部署至生產環境的最佳模型。',
          },
        ],
      ],
    },
    {
      heading: '4.2 關鍵特徵影響因子分析 (Analysis of Key Determinants)',
      paragraphs: [
        [
          {
            text: '進一步透過 SHAP (SHapley Additive exPlanations) 值解析模型的決策邏輯,我們發現「合約類型 (Contract Type)」是預測客戶流失的最顯著特徵。SHAP Summary Plot 顯示,合約期限越短,SHAP 值越高,代表流失風險越大。',
          },
          {
            text: '數據顯示,採「按月付費 (Month-to-month)」合約的客戶,其基礎流失機率比簽訂「兩年合約」的長期客戶高出 45%,這反映了合約轉換成本 (Switching Cost) 會顯著降低客戶的忠誠度 [2]。',
            citationId: 'cite-2',
          },
          {
            text: '這表明,電信營運商應將行銷資源集中於引導月租客戶升級至年約方案,而非僅依賴價格補貼。',
          },
        ],
      ],
    },
    {
      heading: '4.3 服務類型與市場競爭 (Service Type and Market Competition)',
      paragraphs: [
        [
          {
            text: '除了合約結構,「光纖網路服務 (Fiber Optic)」的使用者群體也呈現出異常高的流失傾向。雖然光纖用戶通常貢獻較高的 ARPU (每用戶平均收入),但模型預測顯示其流失風險反而是 DSL 用戶的 1.5 倍。',
          },
          {
            text: '針對此現象,可能的解釋包括光纖市場競爭激烈、價格敏感度高,以及用戶對高價服務的品質期望更為嚴苛,值得後續研究進一步驗證。',
          },
        ],
      ],
    },
  ],
}
```

- [ ] **Step 2: 型別檢查**

Run: `npm run type-check`(在 `frontend/` 下)
Expected: 通過,無錯誤

- [ ] **Step 3: Lint**

Run: `npm run lint`
Expected: 通過(或僅有既存於其他檔案的警告,新檔案無錯誤)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/constants/reportData.ts
git commit -m "feat: add mock paper report data model for paper page"
```

---

### Task 2: 引用側欄元件(CitationPanel.vue)

**Files:**
- Create: `frontend/src/components/paper/CitationPanel.vue`

**Interfaces:**
- Consumes: `Citation`(來自 `@/constants/reportData`)
- Produces: 元件 `CitationPanel`
  - props: `citations: Citation[]`、`activeCitationId: string | null`
  - emits: `(e: 'select', citationId: string): void`
  - 行為: `activeCitationId` 變更時自動將對應卡片捲動至可視範圍並套用高亮樣式

- [ ] **Step 1: 建立元件**

建立 `frontend/src/components/paper/CitationPanel.vue`:

```vue
<template>
  <aside class="citation-panel">
    <article
      v-for="(citation, index) in citations"
      :key="citation.id"
      :ref="el => setCardRef(citation.id, el)"
      class="citation-card"
      :class="{ 'citation-card--active': citation.id === activeCitationId }"
      @click="$emit('select', citation.id)"
    >
      <p class="citation-label">
        <v-icon icon="mdi-book-open-variant-outline" size="13" />
        來源文獻 [{{ index + 1 }}]
      </p>
      <p class="citation-field"><span>標題:</span>{{ citation.title }}</p>
      <p class="citation-field"><span>作者:</span>{{ citation.authors }} ({{ citation.year }})</p>
      <p class="citation-field"><span>期刊:</span>{{ citation.journal }}</p>

      <p class="citation-label snippet-label">
        <v-icon icon="mdi-text-search" size="13" />
        檢索片段
      </p>
      <p class="citation-snippet">{{ citation.snippet }}</p>
    </article>
  </aside>
</template>

<script setup lang="ts">
  import type { ComponentPublicInstance } from 'vue'
  import type { Citation } from '@/constants/reportData'
  import { watch } from 'vue'

  const props = defineProps<{
    citations: Citation[]
    activeCitationId: string | null
  }>()

  defineEmits<{
    (e: 'select', citationId: string): void
  }>()

  const cardRefs = new Map<string, HTMLElement>()

  const setCardRef = (id: string, el: Element | ComponentPublicInstance | null) => {
    if (el instanceof HTMLElement) {
      cardRefs.set(id, el)
    } else {
      cardRefs.delete(id)
    }
  }

  watch(
    () => props.activeCitationId,
    (id) => {
      if (!id) return
      cardRefs.get(id)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    },
  )
</script>

<style scoped>
  .citation-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .citation-card {
    background: #fffbe8;
    border: 1px solid #eadf9e;
    border-radius: 12px;
    padding: 12px 14px;
    cursor: pointer;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .citation-card:hover {
    border-color: #d8c65e;
  }

  .citation-card--active {
    border-color: #c9ad2a;
    box-shadow: 0 2px 10px rgba(180, 150, 30, 0.22);
  }

  .citation-label {
    margin: 0 0 6px;
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    font-weight: 700;
    color: #8a6d1a;
  }

  .snippet-label {
    margin-top: 10px;
  }

  .citation-field {
    margin: 0 0 3px;
    font-size: 12px;
    line-height: 1.55;
    color: #4a4433;
  }

  .citation-field span {
    font-weight: 700;
    color: #6d5c22;
  }

  .citation-snippet {
    margin: 0;
    font-size: 12px;
    line-height: 1.6;
    font-style: italic;
    color: #5c5340;
  }
</style>
```

- [ ] **Step 2: 型別檢查與 Lint**

Run: `npm run type-check`,接著 `npm run lint`
Expected: 皆通過

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/CitationPanel.vue
git commit -m "feat: add citation panel component for paper page"
```

---

### Task 3: 章節渲染元件(PaperSection.vue)

**Files:**
- Create: `frontend/src/components/paper/PaperSection.vue`

**Interfaces:**
- Consumes: `PaperSection` 型別(來自 `@/constants/reportData`)
- Produces: 元件 `PaperSection`
  - props: `section: PaperSection`、`activeCitationId: string | null`
  - emits: `(e: 'citation-click', citationId: string): void`
  - DOM 約定: 每個含引用的片段渲染為 `<mark data-citation-id="...">`,供父層以 `[data-citation-id="..."]` 選取並捲動(Task 4 依賴此屬性)

- [ ] **Step 1: 建立元件**

建立 `frontend/src/components/paper/PaperSection.vue`:

```vue
<template>
  <section class="paper-section">
    <h3 class="section-heading">{{ section.heading }}</h3>
    <p
      v-for="(paragraph, pIndex) in section.paragraphs"
      :key="pIndex"
      class="section-paragraph"
    >
      <template v-for="(segment, sIndex) in paragraph" :key="sIndex">
        <mark
          v-if="segment.citationId"
          class="cite-highlight"
          :class="{ 'cite-highlight--active': segment.citationId === activeCitationId }"
          :data-citation-id="segment.citationId"
          @click="$emit('citation-click', segment.citationId)"
        >{{ segment.text }}</mark>
        <template v-else>{{ segment.text }}</template>
      </template>
    </p>
  </section>
</template>

<script setup lang="ts">
  import type { PaperSection } from '@/constants/reportData'

  defineProps<{
    section: PaperSection
    activeCitationId: string | null
  }>()

  defineEmits<{
    (e: 'citation-click', citationId: string): void
  }>()
</script>

<style scoped>
  .paper-section {
    margin-bottom: 22px;
  }

  .section-heading {
    margin: 0 0 10px;
    font-size: 15px;
    font-weight: 700;
    color: #1c2130;
  }

  .section-paragraph {
    margin: 0 0 12px;
    font-size: 13.5px;
    line-height: 1.9;
    color: #2a2f3a;
    text-align: justify;
    text-indent: 2em;
  }

  .cite-highlight {
    background: #fdf0a8;
    padding: 1px 2px;
    border-radius: 3px;
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .cite-highlight:hover {
    background: #fae57e;
  }

  .cite-highlight--active {
    background: #f7dc5a;
    box-shadow: 0 0 0 2px rgba(201, 173, 42, 0.35);
  }
</style>
```

- [ ] **Step 2: 型別檢查與 Lint**

Run: `npm run type-check`,接著 `npm run lint`
Expected: 皆通過

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/PaperSection.vue
git commit -m "feat: add paper section component with citation highlights"
```

---

### Task 4: 論文頁容器與路由(PaperPage.vue + /paper)

**Files:**
- Create: `frontend/src/views/PaperPage.vue`
- Modify: `frontend/src/router/index.ts`(在 `/results` 路由後新增一條)

**Interfaces:**
- Consumes:
  - `mockPaperReport`(`@/constants/reportData`)
  - `PaperSection` 元件(props: `section`, `activeCitationId`;emit: `citation-click`)
  - `CitationPanel` 元件(props: `citations`, `activeCitationId`;emit: `select`)
  - `Sidebar`(`@/components/Sidebar.vue`,無 props,與 ResultsPage 用法相同)
- Produces: 路由 `/paper`(name: `paper`)

- [ ] **Step 1: 建立頁面**

建立 `frontend/src/views/PaperPage.vue`:

```vue
<template>
  <section class="paper-page">
    <Sidebar />

    <main class="paper-main">
      <header class="paper-toolbar">
        <v-btn
          class="back-btn"
          icon="mdi-arrow-left"
          size="small"
          variant="text"
          @click="router.back()"
        />
        <h2 class="paper-title">{{ report.title }}</h2>
      </header>

      <div class="paper-body">
        <article ref="sheetRef" class="paper-sheet">
          <PaperSection
            v-for="section in report.sections"
            :key="section.heading"
            :active-citation-id="activeCitationId"
            :section="section"
            @citation-click="onCitationClick"
          />
        </article>

        <CitationPanel
          :active-citation-id="activeCitationId"
          :citations="report.citations"
          class="paper-citations"
          @select="onPanelSelect"
        />
      </div>
    </main>
  </section>
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import Sidebar from '@/components/Sidebar.vue'
  import CitationPanel from '@/components/paper/CitationPanel.vue'
  import PaperSection from '@/components/paper/PaperSection.vue'
  import { mockPaperReport } from '@/constants/reportData'

  const router = useRouter()
  const report = mockPaperReport

  const activeCitationId = ref<string | null>(null)
  const sheetRef = ref<HTMLElement | null>(null)

  onMounted(() => {
    document.title = 'DataMind'
  })

  const onCitationClick = (citationId: string) => {
    activeCitationId.value = citationId
  }

  const onPanelSelect = (citationId: string) => {
    activeCitationId.value = citationId
    sheetRef.value
      ?.querySelector(`[data-citation-id="${citationId}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
</script>

<style scoped>
  .paper-page {
    --page-bg: #e4e4e8;
    --card-bg: #ffffff;
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: #15181e;
    --text-secondary: #6f7480;
    --brand: #1058d6;
    min-height: calc(100vh - 64px);
    display: flex;
    gap: 0;
    padding: 16px;
    background:
      radial-gradient(circle at 8% 12%, rgba(99, 146, 238, 0.18) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, rgba(88, 157, 255, 0.16) 0%, transparent 30%),
      linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .paper-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background:
      radial-gradient(circle, #cdd0d8 1px, transparent 1px) 0 0 / 18px 18px,
      linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%);
    padding: 12px 20px 18px;
    overflow: hidden;
  }

  .paper-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
  }

  .back-btn {
    color: #1f2430;
  }

  .paper-title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: #1c2130;
  }

  .paper-body {
    flex: 1;
    min-height: 0;
    display: flex;
    gap: 16px;
    margin-top: 14px;
    overflow: auto;
  }

  .paper-sheet {
    flex: 1;
    min-width: 0;
    max-width: 760px;
    margin: 0 auto;
    background: var(--card-bg);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 28px 34px;
    height: fit-content;
  }

  .paper-citations {
    width: 280px;
    flex-shrink: 0;
    position: sticky;
    top: 0;
    align-self: flex-start;
  }

  @media (max-width: 1100px) {
    .paper-body {
      flex-direction: column;
    }

    .paper-citations {
      width: 100%;
      position: static;
    }
  }
</style>
```

- [ ] **Step 2: 新增路由**

修改 `frontend/src/router/index.ts`,在 `results` 路由物件(`path: "/results"` 那段)之後、`/hub` 之前插入:

```ts
    {
      path: "/paper",
      name: "paper",
      component: () => import("@/views/PaperPage.vue"),
    },
```

- [ ] **Step 3: 型別檢查與 Lint**

Run: `npm run type-check`,接著 `npm run lint`
Expected: 皆通過

- [ ] **Step 4: 目視驗證**

Run: `npm run dev`(在 `frontend/` 下),開啟終端機顯示的網址 + `/paper`
Expected:
1. 頁面呈現 Sidebar + 論文白底文件 + 右側兩張黃色文獻卡片
2. 內文有兩處黃底 highlight;點擊第一處 → 右側「來源文獻 [1]」卡片高亮
3. 點擊右側「來源文獻 [2]」卡片 → 內文捲動至 4.2 的 highlight 並加深底色
4. 縮窄視窗至 <1100px → 側欄移至內文下方
5. 點左上返回鍵 → 回到上一頁

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/PaperPage.vue frontend/src/router/index.ts
git commit -m "feat: add paper page with citation linking at /paper"
```
