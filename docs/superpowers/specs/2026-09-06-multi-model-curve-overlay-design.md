# ROC/PR 多模型疊圖 Design Spec

## 背景

`ConfusionMatrixPanel.vue`（「Classification Evaluation」節點）的 ROC 跟 PR 曲線分頁，目前一次只顯示「一個模型、一個 fold」的曲線——上方有兩個下拉選單（模型 `selectedModel`、fold `selectedFold`），換模型就整條曲線換掉，沒辦法同時比較多個模型。

使用者的老師指出：分類曲線（ROC/PR）業界慣例是把所有模型的曲線疊在同一張圖上比較，這樣才看得出誰的曲線比較靠近左上角（ROC）或右上角（PR）。使用者想把這個變成預設行為：一打開就顯示全部模型的曲線，使用者可以自己點掉不想看的模型。

後端資料結構已經足夠：`groupedResults`（前端 computed，依 `model_name` 分組，每組底下 `splits` 陣列含每個 fold 的 `roc_pr_curve`）已經把所有模型、所有 fold 的曲線資料都準備好了，只是從沒有一次全部畫出來過。這次改動**完全是前端**，不動後端。

## 範圍

- ROC 分頁、PR 分頁：改成多模型疊圖，預設全部顯示，圖例可點擊切換單一模型的顯示/隱藏
- **不**動：校準曲線（Calibration）分頁、混淆矩陣分頁、逐類別指標分頁——這三個天生是單模型檢視，維持現狀
- **不**動後端——`build_roc_pr_curve()` 回傳的資料結構已經夠用
- Fold 維度：維持現有的 fold 下拉選單，切換 fold 時所有模型的曲線一起換成該 fold 的資料（不做跨 fold 平均）

## 元件改動：`ConfusionMatrixPanel.vue`

### 1. 新增狀態：哪些模型被使用者關掉

```typescript
const hiddenModels = ref<Set<string>>(new Set())

function toggleModelVisibility (modelName: string): void {
  const next = new Set(hiddenModels.value)
  if (next.has(modelName)) next.delete(modelName)
  else next.add(modelName)
  hiddenModels.value = next
}
```
`hiddenModels` 切換 fold 時**不清空**——使用者關掉的模型，換到別的 fold 應該還是關著。只有在 `groupedResults` 整批換掉時（重新執行 workflow）才需要重置，用既有的 `watch(groupedResults, ...)`（第 811 行附近，目前負責重選 `selectedModel`/`selectedFold` 預設值）順便加一行 `hiddenModels.value = new Set()`。

### 2. 新增固定色盤

在檔案裡（`buildLinePath` 函式附近）新增一個模組層級常數，8 種彼此區分度高、飽和度足夠的顏色（線圖用途，不是色塊，跟現有 `--color-node-*` 那組低飽和 OKLCH 色票不同調性，不重用）：

```typescript
const SERIES_COLORS = [
  '#2563EB', // 藍
  '#DC2626', // 紅
  '#16A34A', // 綠
  '#D97706', // 橙
  '#7C3AED', // 紫
  '#0891B2', //青
  '#DB2777', // 桃紅
  '#65A30D', // 黃綠
]
```
模型數超過 8 個時用 `index % SERIES_COLORS.length` 循環。

### 3. 把單一 `rocPath`/`prPath` 改成多模型陣列

現有的（第 778-788 行）：
```typescript
const rocPath = computed(() => {
  const curve = currentRocPrCurve.value
  if (!curve) return ''
  return buildLinePath(curve.roc.fpr, curve.roc.tpr)
})

const prPath = computed(() => {
  const curve = currentRocPrCurve.value
  if (!curve) return ''
  return buildLinePath(curve.pr.recall, curve.pr.precision)
})
```
改成（`currentRocPrCurve`/`currentModel`/`rocPath`/`prPath` 全部保留不動，因為混淆矩陣分頁等其他地方可能還在用類似的單模型 pattern——這裡是新增，不是取代。`RocPrCurveData` 是檔案裡已經定義好的既有型別，第 301 行附近）：

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
（`GroupedResult` 型別已經在檔案裡定義，這裡沿用；如果目前沒有直接匯出 `splits` 元素的型別給函式簽名用，用 `ReturnType`/`Parameters` 或直接內嵌型別皆可，實作時看現有型別定義調整，不強求上面這段簽名逐字照抄）

### 4. Template：ROC/PR 區塊改成多線疊圖 + 圖例

現有 ROC 區塊（第 79-92 行）：
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
```
改成（`v-if` 判斷條件從 `currentRocPrCurve`（單模型）改成 `groupedResults.length > 0`，因為現在是多模型一起畫，只要有任何一個模型有資料就該顯示圖表本身；`正類` 標籤取第一個模型的 `posLabel`，因為 posLabel 是資料集目標欄位決定的，理論上跨模型一致）：
```html
<div v-if="activeTab === 'roc' && groupedResults.length > 0" class="cm-chart-wrap">
  <div class="cm-chart-label">正類：{{ groupedResults[0]?.splits.find(s => s.split_name === selectedFold)?.roc_pr_curve?.posLabel }}</div>
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
PR 區塊（第 97-112 行）同樣改法，用 `prSeries`，沒有對角參考線（跟現況一致，PR 圖本來就沒畫對角線）。

`.cm-chart-line`（第 965-969 行）目前用 CSS class 寫死 `stroke: var(--color-ink)`，這條 class 選取器的優先權比 SVG 的 `stroke="..."` 呈現屬性高，所以每條線的顏色**必須**用 `:style="{ stroke: series.color }"`（inline style，優先權比 class 選取器高）而不是 `:stroke="series.color"`（呈現屬性，會被 class 蓋掉、變成全部線都是同一個顏色）——上面的 template 已經照這個寫，不要「簡化」成屬性綁定。

### 5. 「模型」下拉選單只在非 ROC/PR 分頁顯示

現有的（第 3-11 行）：
```html
<div v-if="groupedResults.length > 0" class="cm-controls">
  <div class="cm-field">
    <span class="cm-field__label">模型</span>
    <CustomSelect v-model="selectedModel" class="cm-select" :options="modelOptions" />
  </div>
  <div class="cm-field">
    <span class="cm-field__label">fold</span>
    <CustomSelect v-model="selectedFold" class="cm-select" :options="foldOptions" />
  </div>
</div>
```
「模型」欄位外層加 `v-if="activeTab !== 'roc' && activeTab !== 'pr'"`，fold 欄位不變（兩個分頁都需要）。

### 6. 圖例樣式

新增 CSS（比照現有 `.cm-chart-*` 命名慣例）：
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

## 邊界情況

- 只有 1 個模型：疊圖邏輯照常運作，圖例只顯示 1 個項目，效果等同現在的單模型檢視
- 使用者把全部模型都點掉：圖表區塊變空白（所有 `<path>` 都 `v-show="false"`），圖例仍然顯示（讓使用者點回來）——不特別擋「至少留一個」，因為這只是檢視層級的顯示切換，不影響任何底層資料或後續動作
- 某個模型在目前選定的 fold 沒有 ROC/PR 資料（例如該模型只支援部分 fold，或該次結果是舊版執行結果沒有 curve 欄位）：`buildCurveSeries` 會給該模型 `path: ''`，SVG 的 `<path d="">` 不會畫出任何東西，圖例仍然列出該模型（點擊沒有實際效果，可接受，不特別處理成 disabled，因為判斷「這個模型是否真的沒資料」在圖例層級要多一層檢查，YAGNI）
- 切換 fold 後：`hiddenModels` 不重置，維持使用者原本關掉的模型
- 重新執行 workflow（`groupedResults` 整批換掉）：`hiddenModels` 重置為空集合，全部模型預設顯示

## 測試

前端沒有自動化測試框架，比照這個 session 其他前端改動的慣例：
1. `npm run type-check`（在 `datamind-frontend` container 內跑）
2. 人工瀏覽器驗證：
   - 執行一個有多個模型的 workflow，進 Classification Evaluation 節點的 ROC 分頁，確認一次看到所有模型的曲線，顏色各不相同
   - 點圖例裡的某個模型名稱，確認該模型的線消失、名稱變灰色刪除線；再點一次確認恢復
   - 切換 fold 下拉選單，確認所有模型的曲線一起換成新 fold 的資料，剛才關掉的模型維持關閉狀態
   - 切到 PR 分頁，確認同樣的疊圖 + 圖例行為，且沒有對角參考線
   - 切到混淆矩陣分頁，確認「模型」下拉選單重新出現，且選單邏輯跟現在一樣正常運作
   - 切到校準曲線分頁，確認維持單模型檢視，沒有被這次改動影響
   - 只有 1 個模型的 workflow，確認 ROC/PR 分頁顯示正常（圖例只有一項）
