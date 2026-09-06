# ROC/PR 多模型疊圖 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「Classification Evaluation」節點的 ROC / PR 曲線分頁從「一次只看一個模型」改成「預設疊圖顯示全部模型，圖例可點擊切換單一模型顯示/隱藏」。

**Architecture:** 純前端單檔案改動（`ConfusionMatrixPanel.vue`）。新增 `hiddenModels` 狀態記錄使用者關掉哪些模型，把原本只算「目前選中模型」一條線的邏輯改成對 `groupedResults` 裡每個模型各自算一條線（`CurveSeries[]`），template 從畫單一 `<path>` 改成 `v-for` 疊圖 + 新增可點擊圖例。後端資料結構已經足夠，完全不動後端。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript，沿用既有的手刻 inline SVG 圖表模式（無圖表函式庫）。

## Global Constraints

- 只改 ROC、PR 兩個分頁；混淆矩陣、校準曲線、逐類別指標三個分頁完全不受影響
- 完全不動後端
- Fold 維度：維持現有 fold 下拉選單，一次選一個 fold，所有模型顯示同一個 fold 的曲線（不做跨 fold 平均）
- `hiddenModels` 切換 fold 時不清空；只有 `groupedResults` 整批換掉（重新執行 workflow）時才重置
- 「模型」下拉選單只在非 ROC/PR 分頁顯示
- 每條線的顏色**必須**用 `:style="{ stroke: series.color }"`（inline style），不能用 `:stroke="series.color"`（SVG 呈現屬性）——後者會被既有的 `.cm-chart-line { stroke: var(--color-ink) }` CSS class 蓋掉，變成所有線都同一個顏色
- 型別檢查要在 `datamind-frontend` container 內執行（`docker exec datamind-frontend sh -c "cd /app && npm run type-check"`），host 上因為缺 `@tiptap/*` 套件會有 53 個既有的、跟這次改動無關的錯誤
- 直接在 `main` branch 上工作，不開額外 git worktree

---

### Task 1: 多模型疊圖資料層 + Template + 圖例

這是唯一一個 task——單一檔案、資料層跟 template 高度耦合（疊圖顏色的正確性要接上 template 才能實際驗證，拆成兩個 task 沒有有意義的中間驗收點），不需要拆分。

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`

**Interfaces:**
- Consumes: 既有的 `groupedResults`（第 429-453 行，`GroupedResult[]`）、`selectedFold`（第 456 行）、`buildLinePath()`（第 771-776 行）、`RocPrCurveData` 型別（第 301 行附近）
- Produces: `hiddenModels: Ref<Set<string>>`、`toggleModelVisibility(modelName: string): void`、`rocSeries: ComputedRef<CurveSeries[]>`、`prSeries: ComputedRef<CurveSeries[]>`——這是這個 plan 唯一的 task，這些名稱不會被其他 task 消費，但列出來方便 code review 對照 spec

- [ ] **Step 1: 新增色盤常數**

在 `buildLinePath` 函式（第 771 行）之前新增：
```typescript
// 疊圖用的固定色盤：線圖需要飽和度夠、彼此區分度高，跟 --color-node-* 那組給色塊用的
// 低飽和 OKLCH 色票是不同調性用途，不重用。模型數超過 8 個時循環使用
const SERIES_COLORS = [
  '#2563EB', // 藍
  '#DC2626', // 紅
  '#16A34A', // 綠
  '#D97706', // 橙
  '#7C3AED', // 紫
  '#0891B2', // 青
  '#DB2777', // 桃紅
  '#65A30D', // 黃綠
]
```

- [ ] **Step 2: 新增 `hiddenModels` 狀態與切換函式**

在 `selectedModel`/`selectedFold` 宣告（第 455-456 行）附近新增：
```typescript
const hiddenModels = ref<Set<string>>(new Set())

function toggleModelVisibility (modelName: string): void {
  const next = new Set(hiddenModels.value)
  if (next.has(modelName)) next.delete(modelName)
  else next.add(modelName)
  hiddenModels.value = next
}
```

- [ ] **Step 3: 新增 `CurveSeries` 介面與 `buildCurveSeries()` / `rocSeries` / `prSeries`**

在 `buildLinePath`（第 771-776 行）之後、`rocPath`/`prPath`（第 778-788 行，這兩個保留不動，不要刪除或修改）之後新增：
```typescript
interface CurveSeries {
  modelName: string
  color: string
  path: string
  visible: boolean
}

function buildCurveSeries (
  extractXY: (curve: RocPrCurveData) => [number[], number[]],
): CurveSeries[] {
  return groupedResults.value.map((group, index) => {
    const curve = group.splits.find(s => s.split_name === selectedFold.value)?.roc_pr_curve
    const [xs, ys] = curve ? extractXY(curve) : [[], []]
    return {
      modelName: group.model_name,
      color: SERIES_COLORS[index % SERIES_COLORS.length]!,
      path: buildLinePath(xs, ys),
      visible: !hiddenModels.value.has(group.model_name),
    }
  })
}

const rocSeries = computed<CurveSeries[]>(() => buildCurveSeries(curve => [curve.roc.fpr, curve.roc.tpr]))
const prSeries = computed<CurveSeries[]>(() => buildCurveSeries(curve => [curve.pr.recall, curve.pr.precision]))
```
（`RocPrCurveData` 是檔案裡已經定義好的既有型別，第 301 行附近，直接沿用不用重新定義）

- [ ] **Step 4: `watch(groupedResults, ...)` 加上 `hiddenModels` 重置**

第 810-819 行現有的：
```typescript
// 結果載入或換模型後，把選取校正到有效值（預設第一個模型 / 第一個 fold）
watch(groupedResults, groups => {
  if (groups.length === 0) {
    selectedModel.value = ''
    return
  }
  if (!groups.some(g => g.model_name === selectedModel.value)) {
    selectedModel.value = groups[0]!.model_name
  }
}, { immediate: true })
```
改成（只加一行 `hiddenModels.value = new Set()`，其餘邏輯不變）：
```typescript
// 結果載入或換模型後，把選取校正到有效值（預設第一個模型 / 第一個 fold）
watch(groupedResults, groups => {
  // 重新執行 workflow、結果整批換掉時，使用者之前關掉的模型不該延續下去
  hiddenModels.value = new Set()
  if (groups.length === 0) {
    selectedModel.value = ''
    return
  }
  if (!groups.some(g => g.model_name === selectedModel.value)) {
    selectedModel.value = groups[0]!.model_name
  }
}, { immediate: true })
```

- [ ] **Step 5: 語法檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`

Expected: 既有的 53 個 `@tiptap/*` 錯誤不變，沒有新增任何跟 `ConfusionMatrixPanel.vue` 有關的錯誤。用 `npm run type-check 2>&1 | grep -i "ConfusionMatrixPanel"` 確認沒有輸出（此時 template 還沒接上新的 computed，`rocSeries`/`prSeries`/`toggleModelVisibility`/`hiddenModels` 會被 TS 標記成「宣告了但沒使用」——這是預期中的暫時狀態，Step 6-8 接上 template 後就會消失，不用現在特別處理）。

- [ ] **Step 6: 「模型」下拉選單只在非 ROC/PR 分頁顯示**

第 3-11 行現有的：
```html
<div v-if="groupedResults.length > 0" class="cm-controls">
  <div class="cm-field">
    <span class="cm-field__label">模型</span>
    <CustomSelect
      v-model="selectedModel"
      class="cm-select"
      :options="modelOptions"
    />
  </div>
  <div class="cm-field">
    <span class="cm-field__label">fold</span>
    <CustomSelect
      v-model="selectedFold"
      class="cm-select"
      :options="foldOptions"
    />
  </div>
</div>
```
改成（只在「模型」欄位外層加 `v-if`，fold 欄位不變）：
```html
<div v-if="groupedResults.length > 0" class="cm-controls">
  <div v-if="activeTab !== 'roc' && activeTab !== 'pr'" class="cm-field">
    <span class="cm-field__label">模型</span>
    <CustomSelect
      v-model="selectedModel"
      class="cm-select"
      :options="modelOptions"
    />
  </div>
  <div class="cm-field">
    <span class="cm-field__label">fold</span>
    <CustomSelect
      v-model="selectedFold"
      class="cm-select"
      :options="foldOptions"
    />
  </div>
</div>
```

- [ ] **Step 7: ROC 區塊改成多線疊圖 + 圖例**

第 79-95 行現有的：
```html
<div v-if="activeTab === 'roc' && currentRocPrCurve" class="cm-chart-wrap">
  <div class="cm-chart-label">正類：{{ currentRocPrCurve?.posLabel }}</div>
  <svg class="cm-chart" viewBox="0 0 100 100">
    <line class="cm-chart-diagonal" x1="18" y1="82" x2="82" y2="18" />
    <path class="cm-chart-line" :d="rocPath" fill="none" />
    <text class="cm-chart-tick" x="13" y="95" text-anchor="middle">0</text>
    <text class="cm-chart-tick" x="50" y="90" text-anchor="middle">0.5</text>
    <text class="cm-chart-tick" x="82" y="90" text-anchor="end">1</text>
    <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="50">0.5</text>
    <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="18">1</text>
  </svg>
  <div class="cm-chart-axis-x">FPR (0 – 1)</div>
  <div class="cm-chart-axis-y">TPR (0 – 1)</div>
</div>
<div v-else-if="activeTab === 'roc'" class="summary-empty">
  此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
</div>
```
改成（`v-if` 判斷條件從單模型的 `currentRocPrCurve` 改成 `groupedResults.length > 0`，因為現在同時畫多個模型；正類標籤取第一個模型在目前 fold 的 `posLabel`）：
```html
<div v-if="activeTab === 'roc' && groupedResults.length > 0" class="cm-chart-wrap">
  <div class="cm-chart-label">
    正類：{{ groupedResults[0]?.splits.find(s => s.split_name === selectedFold)?.roc_pr_curve?.posLabel }}
  </div>
  <svg class="cm-chart" viewBox="0 0 100 100">
    <line class="cm-chart-diagonal" x1="18" y1="82" x2="82" y2="18" />
    <path
      v-for="series in rocSeries"
      v-show="series.visible"
      :key="series.modelName"
      class="cm-chart-line"
      :d="series.path"
      fill="none"
      :style="{ stroke: series.color }"
    />
    <text class="cm-chart-tick" x="13" y="95" text-anchor="middle">0</text>
    <text class="cm-chart-tick" x="50" y="90" text-anchor="middle">0.5</text>
    <text class="cm-chart-tick" x="82" y="90" text-anchor="end">1</text>
    <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="50">0.5</text>
    <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="18">1</text>
  </svg>
  <div class="cm-chart-axis-x">FPR (0 – 1)</div>
  <div class="cm-chart-axis-y">TPR (0 – 1)</div>
  <div class="cm-chart-legend">
    <button
      v-for="series in rocSeries"
      :key="series.modelName"
      class="cm-legend-item"
      :class="{ 'cm-legend-item--hidden': !series.visible }"
      type="button"
      @click="toggleModelVisibility(series.modelName)"
    >
      <span class="cm-legend-swatch" :style="{ background: series.color }" />
      {{ series.modelName }}
    </button>
  </div>
</div>
<div v-else-if="activeTab === 'roc'" class="summary-empty">
  此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
</div>
```

- [ ] **Step 8: PR 區塊改成多線疊圖 + 圖例**

第 97-112 行現有的（結構跟 ROC 幾乎一樣，但沒有對角參考線）：
```html
<div v-if="activeTab === 'pr' && currentRocPrCurve" class="cm-chart-wrap">
  <div class="cm-chart-label">正類：{{ currentRocPrCurve?.posLabel }}</div>
  <svg class="cm-chart" viewBox="0 0 100 100">
    <path class="cm-chart-line" :d="prPath" fill="none" />
    <text class="cm-chart-tick" x="13" y="95" text-anchor="middle">0</text>
    <text class="cm-chart-tick" x="50" y="90" text-anchor="middle">0.5</text>
    <text class="cm-chart-tick" x="82" y="90" text-anchor="end">1</text>
    <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="50">0.5</text>
    <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="18">1</text>
  </svg>
  <div class="cm-chart-axis-x">Recall (0 – 1)</div>
  <div class="cm-chart-axis-y">Precision (0 – 1)</div>
</div>
<div v-else-if="activeTab === 'pr'" class="summary-empty">
  此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
</div>
```
改成：
```html
<div v-if="activeTab === 'pr' && groupedResults.length > 0" class="cm-chart-wrap">
  <div class="cm-chart-label">
    正類：{{ groupedResults[0]?.splits.find(s => s.split_name === selectedFold)?.roc_pr_curve?.posLabel }}
  </div>
  <svg class="cm-chart" viewBox="0 0 100 100">
    <path
      v-for="series in prSeries"
      v-show="series.visible"
      :key="series.modelName"
      class="cm-chart-line"
      :d="series.path"
      fill="none"
      :style="{ stroke: series.color }"
    />
    <text class="cm-chart-tick" x="13" y="95" text-anchor="middle">0</text>
    <text class="cm-chart-tick" x="50" y="90" text-anchor="middle">0.5</text>
    <text class="cm-chart-tick" x="82" y="90" text-anchor="end">1</text>
    <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="50">0.5</text>
    <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="18">1</text>
  </svg>
  <div class="cm-chart-axis-x">Recall (0 – 1)</div>
  <div class="cm-chart-axis-y">Precision (0 – 1)</div>
  <div class="cm-chart-legend">
    <button
      v-for="series in prSeries"
      :key="series.modelName"
      class="cm-legend-item"
      :class="{ 'cm-legend-item--hidden': !series.visible }"
      type="button"
      @click="toggleModelVisibility(series.modelName)"
    >
      <span class="cm-legend-swatch" :style="{ background: series.color }" />
      {{ series.modelName }}
    </button>
  </div>
</div>
<div v-else-if="activeTab === 'pr'" class="summary-empty">
  此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
</div>
```

- [ ] **Step 9: 新增圖例 CSS**

在 `.cm-chart-line`（第 965-969 行）附近新增：
```css
.cm-chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 8px;
}

.cm-legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: none;
  padding: 2px 4px;
  cursor: pointer;
  font-size: 12px;
  color: var(--color-text);
}

.cm-legend-item--hidden {
  color: var(--color-ink-soft);
  text-decoration: line-through;
}

.cm-legend-swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.cm-legend-item--hidden .cm-legend-swatch {
  opacity: 0.35;
}
```

- [ ] **Step 10: 語法檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`

Expected: 既有的 53 個 `@tiptap/*` 錯誤不變，`npm run type-check 2>&1 | grep -i "ConfusionMatrixPanel"` 沒有輸出（這次應該完全乾淨，Step 5 提到的「宣告未使用」警告在 template 接上後會消失）。

- [ ] **Step 11: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
git commit -m "feat: overlay all models on ROC/PR curves with clickable legend"
```

---

## 完成後的人工驗證

Commit 完成後，在瀏覽器 `http://localhost:5173` 上驗證（前端/後端 dev server 都已在跑，直接測）：

1. 執行一個有多個模型的 workflow，進 Classification Evaluation 節點的 ROC 分頁，確認一次看到所有模型的曲線，顏色各不相同
2. 點圖例裡的某個模型名稱，確認該模型的線消失、名稱變灰色刪除線；再點一次確認恢復
3. 切換 fold 下拉選單，確認所有模型的曲線一起換成新 fold 的資料，剛才關掉的模型維持關閉狀態
4. 切到 PR 分頁，確認同樣的疊圖 + 圖例行為，且沒有對角參考線
5. 切到混淆矩陣分頁，確認「模型」下拉選單重新出現，且選單邏輯跟現在一樣正常運作
6. 切到校準曲線分頁，確認維持單模型檢視，沒有被這次改動影響
7. 只有 1 個模型的 workflow，確認 ROC/PR 分頁顯示正常（圖例只有一項）
8. 重新執行一次 workflow，確認 ROC/PR 分頁的圖例回到全部顯示（之前關掉的模型不會延續到新的執行結果）
