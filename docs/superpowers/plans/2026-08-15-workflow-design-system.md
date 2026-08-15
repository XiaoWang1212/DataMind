# Workflow 頁面套用設計系統 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 workflow 相關的 15 個檔案套上設計系統：節點顏色從舊的三態 `colorClass` 改成獨立的 `nodeType`（五類分類色）+ `status`（執行狀態徽章），並清理殘留的硬寫 hex、原生 `<button>`、超規格字重/圓角/動畫時長，順便刪掉掃描中發現的死代碼。

**Architecture:** 先落地資料結構（`nodeType` 欄位、token、`IconNode.vue` 渲染），再逐檔案做樣式清理——按鈕遷移、字重/圓角/時長/hex token 化、死代碼刪除都在同一個檔案內一次做完，避免同一檔案被多個 task 重複觸碰。

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Vuetify 4 主題 token, `@vue-flow/core`。

## Global Constraints

- 字重只能是 400 或 500（§3），不用 600/700。
- 圓角只能是 `var(--radius-sm)`(8px) / `var(--radius-md)`(12px) / `var(--radius-lg)`(16px) / 字面量 `999px`(pill，無對應 token)。`50%`（圓形頭像/icon）與極小視覺細節（≤3px）不受此規範管轄。
- 互動 transition 時長只能是 `var(--dur-fast)`(120ms) / `var(--dur-base)`(200ms) / `var(--dur-slow)`(320ms)；keyframe `animation`（spinner、pulse、flash 等效果動畫）不受此規範管轄，維持原有數值。
- 按鈕一律用 `components/ui/AppButton.vue`（`import AppButton from '@/components/ui/AppButton.vue'`），不用原生 `<button>`。Props：`variant`(`primary`/`secondary`/`ghost`/`danger`，預設 `primary`)、`icon-only`、`loading`、`disabled`、`type`。icon-only 按鈕要加 `aria-label`。
- `SettingsPanel.vue` 的 `wizard-tab`（頁籤）與 `ci-toggle`（開關）**不是**按鈕，不套用 `AppButton`，只在圓角/時長清理範圍內套 token。
- 每個 task 完成後跑 `npx eslint <改動的檔案>` 與 `npm run build`（在 `frontend/` 目錄下），兩個都要過。
- Commit message 一行、用英文、不加 `Co-Authored-By` trailer。

---

## Task 1: 節點分類色 token + StyleGuideView 同步

**Files:**
- Modify: `frontend/src/plugins/vuetify.ts:55-60`
- Modify: `frontend/src/views/StyleGuideView.vue`
- Modify: `docs/DESIGN_SYSTEM.md`（§2.3 節點色表）

**Interfaces:**
- Produces：五個 CSS token `--color-node-source` / `--color-node-transform` / `--color-node-visualize` / `--color-node-model` / `--color-node-evaluate`，後續所有 task 讀取這五個 token，不直接寫 hex。

- [ ] **Step 1: 更新 vuetify.ts 的節點色 token**

打開 `frontend/src/plugins/vuetify.ts`，找到這段（第 55-60 行左右）：

```ts
          // workflow 節點分類色（docs/DESIGN_SYSTEM.md §2.3）。依 pipeline 角色分五類，
          // 全部避開綠/琥珀/紅 —— 那三色留給節點外圈的執行狀態，混用會讓「已完成」讀不出來
          'node-source': '#2F7E8C',
          'node-inspect': '#3A6BB8',
          'node-transform': '#6252BE',
          'node-model': '#93459F',
          'node-evaluate': '#B44476',
```

換成：

```ts
          // workflow 節點分類色（docs/DESIGN_SYSTEM.md §2.3）。依 pipeline 角色分五類，
          // 依 Orange Data Mining 的六類配色大致順序（橘/藍/紫/綠/紅）指派，OKLCH 明度/彩度
          // 統一（L=0.76 C=0.058，只有色相不同）。跟 success/warning/error 三個狀態色的
          // 色相距離沒有嚴格要求——這組色相跟狀態色偶有貼近（例如 source 對 error 只差 24°），
          // 是刻意換取「一眼看得出是 Orange 配色語彙」的結果，靠淺底+邊框+深色 icon 的構造
          // 而非色相距離本身來避免混淆
          'node-source': '#D2A596',
          'node-transform': '#8EB8D1',
          'node-visualize': '#A9AED6',
          'node-model': '#85BDBC',
          'node-evaluate': '#CFA3B6',
```

注意 `node-inspect` 這個 key 整個被移除、換成新的 `node-visualize`（原本 inspect 涵蓋 Data Table + Distribution 兩個節點，現在 Data Table 併入 source，Distribution 獨立成 visualize）。

- [ ] **Step 2: 更新 `frontend/src/styles/tailwind.css` 的 token 橋接**

打開 `frontend/src/styles/tailwind.css`，找到：

```css
  --color-node-source: rgb(var(--v-theme-node-source));
  --color-node-inspect: rgb(var(--v-theme-node-inspect));
  --color-node-transform: rgb(var(--v-theme-node-transform));
  --color-node-model: rgb(var(--v-theme-node-model));
  --color-node-evaluate: rgb(var(--v-theme-node-evaluate));
```

換成：

```css
  --color-node-source: rgb(var(--v-theme-node-source));
  --color-node-transform: rgb(var(--v-theme-node-transform));
  --color-node-visualize: rgb(var(--v-theme-node-visualize));
  --color-node-model: rgb(var(--v-theme-node-model));
  --color-node-evaluate: rgb(var(--v-theme-node-evaluate));
```

- [ ] **Step 3: 跑 build 確認 token 沒有語法錯誤**

Run（在 `frontend/` 目錄下）: `npm run build`
Expected: PASS（這步只是換色值跟 key 名，不影響任何邏輯，但先確認沒打錯字）

- [ ] **Step 4: 更新 `StyleGuideView.vue` 的節點分類色展示區塊**

打開 `frontend/src/views/StyleGuideView.vue`。

先處理 `<template>`：把第 20-38 行的說明文字換掉（節點不再是白色 icon）：

```html
    <section>
      <h2 class="sg-h2">Workflow 節點分類色（§2.3）</h2>
      <p class="sg-note">
        依 pipeline 角色分五類，比照 Orange Data Mining 的六類配色大致順序（橘/藍/紫/綠/紅）指派，
        低飽和大地色系。節點是圓形淺底 + 深色 icon + 細邊框，選中/完成用綠色勾勾徽章疊在右下角。
      </p>
      <div class="sg-node-grid">
        <div v-for="cat in nodeCategories" :key="cat.name" class="sg-node">
          <div class="sg-node-dot sg-node-dot--bordered" :style="{ background: cat.varRef }">
            <v-icon color="var(--color-ink-strong)" icon="mdi-circle-outline" size="24" />
            <span class="sg-node-badge">
              <v-icon icon="mdi-check" size="12" />
            </span>
          </div>
          <div>
            <div class="sg-swatch-label">{{ cat.name }}</div>
            <div class="sg-swatch-var">{{ cat.hex }}</div>
            <div class="sg-swatch-var">{{ cat.nodes }}</div>
          </div>
        </div>
      </div>
    </section>
```

然後**整段刪除**第 40-97 行的「節點配色對照（決策用）」`<section>`（從 `<!-- 決定要不要改採 Orange Data Mining 色系用的對照 -->` 這行註解開始，到它對應的 `</section>` 結束，含中間的參考色票/三版色票對照）——這是色彩定案前的比較用區塊，已經定案，整段連同底下註解一起刪。

- [ ] **Step 5: 更新 `<script setup>` 裡的 `nodeCategories` 資料與清掉決策用資料**

把第 279-286 行左右的 `nodeCategories` 換成：

```ts
  // §2.3：依 pipeline 角色分五類，比照 Orange 的六類配色大致順序（橘/藍/紫/綠/紅）指派
  const nodeCategories = [
    { name: 'source 資料來源', varRef: 'var(--color-node-source)', hex: '#D2A596', nodes: 'File、Data Table' },
    { name: 'transform 轉換', varRef: 'var(--color-node-transform)', hex: '#8EB8D1', nodes: 'Preprocessor、Feature Engineering' },
    { name: 'visualize 視覺化', varRef: 'var(--color-node-visualize)', hex: '#A9AED6', nodes: 'Distribution' },
    { name: 'model 建模', varRef: 'var(--color-node-model)', hex: '#85BDBC', nodes: 'Settings、Models' },
    { name: 'evaluate 評估', varRef: 'var(--color-node-evaluate)', hex: '#CFA3B6', nodes: 'Test & Score、Feature Importance、Confusion Matrix、Compute CI' },
  ]
```

然後**整段刪除**第 288-386 行（從 `// 決定要不要改採 Orange Data Mining 色系用的對照資料，定案後整段刪掉。` 這行註解開始，一路到 `referencePalettes` 陣列結束、`</script>` 之前）——包含 `NODE_ICONS`、`CATEGORY_LABELS`、`palette()` 函式、`nodePaletteOptions`、`referenceSwatch`、`referencePalettes` 全部刪除，這些只是色彩決策過程用的比較資料。

- [ ] **Step 6: 清掉只被刪除區塊使用的 CSS，保留並復用徽章/邊框樣式**

在 `<style scoped>` 裡找到 `.sg-palette`、`.sg-palette-head`、`.sg-palette-row`、`.sg-palette-item` 這四條規則，整段刪除（只被剛刪掉的 template 區塊使用）。

保留 `.sg-node-dot--bordered` 與 `.sg-node-badge`（`.sg-node-dot--done` 這個 class 名稱在新 template 裡沒有用到了，因為現在徽章固定顯示不需要條件 class，把 `.sg-node-dot--done` 規則也一併刪除，只留 `.sg-node-dot--bordered` 和 `.sg-node-badge`）。

- [ ] **Step 7: 確認頁面行為並跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/views/StyleGuideView.vue src/plugins/vuetify.ts src/styles/tailwind.css
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 8: 更新 `docs/DESIGN_SYSTEM.md` §2.3 節點色表**

打開 `docs/DESIGN_SYSTEM.md`，找到 §2.3 的節點分類色表（`--color-node-source` 那張表），把：

```
| `--color-node-source` | `#2F7E8C` 藍綠 | File |
| `--color-node-inspect` | `#3A6BB8` 藍 | Data Table、Distribution |
| `--color-node-transform` | `#6252BE` 靛紫 | Preprocessor、Feature Engineering |
| `--color-node-model` | `#93459F` 紫 | Settings、Models |
| `--color-node-evaluate` | `#B44476` 洋紅 | Test & Score、Feature Importance、Confusion Matrix、Compute CI |
```

換成：

```
| `--color-node-source` | `#D2A596` 灰橘棕 | File、Data Table |
| `--color-node-transform` | `#8EB8D1` 灰藍 | Preprocessor、Feature Engineering |
| `--color-node-visualize` | `#A9AED6` 灰藍紫 | Distribution |
| `--color-node-model` | `#85BDBC` 灰青綠 | Settings、Models |
| `--color-node-evaluate` | `#CFA3B6` 灰玫瑰 | Test & Score、Feature Importance、Confusion Matrix、Compute CI |
```

同一節上方描述文字如果提到「冷色、低飽和，沿 pipeline 由青往紫推移」「白色 icon 疊在五個底色上的對比」或「全部避開綠/琥珀/紅」，一併改成符合新色票的敘述：色系改成低飽和大地色系、比照 Orange Data Mining 六類配色的大致順序（橘/藍/紫/綠/紅）指派給五個分類（不是刻意避開特定色相）；節點構造改成淺底配深色 icon（`--color-ink-strong`），不是白色 icon 疊底色；跟 success/warning/error 三個狀態色的色相距離**沒有**嚴格要求，靠淺底 + 邊框 + 深色 icon 的構造本身，以及分類色統一走圓形節點底色、狀態色統一走外部徽章/spinner 的位置區隔來避免混淆，不是靠色相隔開。

- [ ] **Step 9: Commit**

```bash
git add frontend/src/plugins/vuetify.ts frontend/src/styles/tailwind.css frontend/src/views/StyleGuideView.vue docs/DESIGN_SYSTEM.md
git commit -m "feat(workflow): replace node category color tokens with earth-tone palette"
```

---

## Task 2: `types/workflow.ts` 新增 `NodeType`

**Files:**
- Modify: `frontend/src/types/workflow.ts`

**Interfaces:**
- Produces：`NodeType` type（`'source' | 'transform' | 'visualize' | 'model' | 'evaluate'`），`NodeData.nodeType: NodeType` 欄位。後續 Task 3-6 都依賴這個型別與欄位名。

- [ ] **Step 1: 修改 `NodeData` interface**

打開 `frontend/src/types/workflow.ts`，把：

```ts
export interface NodeData {
  icon: string;
  label: string;
  colorClass: string;
  description: string;
  fields: NodeField[];
  config: Record<string, unknown>;
  /** demo 動畫狀態，由 canvasNodes computed 動態註入 */
  status?: "running" | "finished" | null;
  /** 是否為目前點選中的節點，由 canvasNodes computed 依 selectedNodeId 動態註入 */
  isSelected?: boolean;
}
```

換成：

```ts
export type NodeType = "source" | "transform" | "visualize" | "model" | "evaluate";

export interface NodeData {
  icon: string;
  label: string;
  /** 節點分類，決定底色（docs/DESIGN_SYSTEM.md §2.3），建立節點時指定、不隨執行狀態改變 */
  nodeType: NodeType;
  description: string;
  fields: NodeField[];
  config: Record<string, unknown>;
  /** demo 動畫狀態，由 canvasNodes computed 動態註入 */
  status?: "running" | "finished" | null;
  /** 是否為目前點選中的節點，由 canvasNodes computed 依 selectedNodeId 動態註入 */
  isSelected?: boolean;
}
```

- [ ] **Step 2: 跑型別檢查（預期會出現一堆錯誤，這是正常的，後面幾個 task 會逐一修掉）**

Run（在 `frontend/` 目錄下）: `npm run build`
Expected: FAIL，錯誤訊息會指出 `constants/workflowData.ts`、`useWorkflowNodes.ts`、`useWorkflowImport.ts`、`IconNode.vue` 裡還在用 `colorClass` 的地方型別不符——這些正是 Task 3-6 要修的檔案，此時不用修，先確認錯誤訊息涵蓋的檔案跟預期一致即可

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/workflow.ts
git commit -m "feat(workflow): add NodeType field, replacing colorClass"
```

（這個 commit 之後 build 會是紅的，直到 Task 3-6 都完成——這是刻意的，資料結構改動要拆成看得懂進度的小步驟，不是為了維持每個 commit 都能 build 過）

---

## Task 3: `constants/workflowData.ts` 節點分類映射

**Files:**
- Modify: `frontend/src/constants/workflowData.ts`

**Interfaces:**
- Consumes：Task 2 的 `NodeType`
- Produces：7 個 demo 節點各自帶正確的 `nodeType`

- [ ] **Step 1: 把 7 個節點的 `colorClass: "node-pending"` 換成對應的 `nodeType`**

打開 `frontend/src/constants/workflowData.ts`，這個檔案裡有 7 處 `colorClass: "node-pending",`，逐一對照 `id` 換成：

| `id` | 原本 | 換成 |
|---|---|---|
| `file` (第 15 行) | `colorClass: "node-pending",` | `nodeType: "source",` |
| `dataTable` (第 30 行) | `colorClass: "node-pending",` | `nodeType: "source",` |
| `distribution` (第 45 行) | `colorClass: "node-pending",` | `nodeType: "visualize",` |
| `settings` (第 60 行) | `colorClass: "node-pending",` | `nodeType: "model",` |
| `testScore` (第 79 行) | `colorClass: "node-pending",` | `nodeType: "evaluate",` |
| `featureImportance` (第 99 行) | `colorClass: "node-pending",` | `nodeType: "evaluate",` |
| `confusionMatrix` (第 114 行) | `colorClass: "node-pending",` | `nodeType: "evaluate",` |

每處都是同樣的字串 `colorClass: "node-pending",`，靠上下文的 `id`/`label` 判斷是哪一個，逐一替換，不要用全域取代（7 處要換成 3 種不同的值）。

- [ ] **Step 2: 跑型別檢查**

Run（在 `frontend/` 目錄下）: `npm run build`
Expected: 這個檔案不再報錯，但 `useWorkflowNodes.ts`/`useWorkflowImport.ts`/`IconNode.vue` 仍會報錯（下個 task 處理）

- [ ] **Step 3: Commit**

```bash
git add frontend/src/constants/workflowData.ts
git commit -m "feat(workflow): map initial nodes to nodeType"
```

---

## Task 4: `useWorkflowNodes.ts` 節點分類映射 + 移除狀態耦合顏色

**Files:**
- Modify: `frontend/src/composables/workflow/useWorkflowNodes.ts`

**Interfaces:**
- Consumes：Task 2 的 `NodeType`
- Produces：動態產生的 model / preprocessor / featureEngineering / computeCi 節點都帶正確 `nodeType`；`canvasNodes` computed 不再覆寫顏色

- [ ] **Step 1: 移除 `canvasNodes` 裡狀態覆寫顏色的那行**

第 55-75 行左右的 `canvasNodes` computed，把：

```ts
      return {
        ...node,
        class: node.id.startsWith('model-') ? 'node-non-interactive' : '',
        data: {
          ...node.data,
          status,
          colorClass: status === 'finished' ? 'node-yellow' : node.data.colorClass,
          highlighted,
          highlightColor: highlighted ? color : null,
          isSelected: node.id === selectedNodeId.value,
          flashType: nodeFlash.value.get(node.id) ?? null,
        },
      }
```

換成（只刪掉 `colorClass` 那一行，其餘不動）：

```ts
      return {
        ...node,
        class: node.id.startsWith('model-') ? 'node-non-interactive' : '',
        data: {
          ...node.data,
          status,
          highlighted,
          highlightColor: highlighted ? color : null,
          isSelected: node.id === selectedNodeId.value,
          flashType: nodeFlash.value.get(node.id) ?? null,
        },
      }
```

- [ ] **Step 2: model 節點的 `nodeType`（第 153 行左右）**

找到建立 model 節點的地方（`icon: 'mdi-brain'` 那個 data 物件），把：

```ts
        data: {
          icon: 'mdi-brain',
          label: name,
          colorClass: 'node-pending',
          description: purposeZh || name,
          fields: [],
          config: { modelName: name },
        },
```

換成：

```ts
        data: {
          icon: 'mdi-brain',
          label: name,
          nodeType: 'model',
          description: purposeZh || name,
          fields: [],
          config: { modelName: name },
        },
```

- [ ] **Step 3: pipeline 節點的 `nodeType`（第 235 行左右）**

找到：

```ts
        data: {
          icon: def.icon,
          label: def.label,
          colorClass: existing?.data.colorClass ?? 'node-pending',
          description: def.desc,
          fields: [],
          config: { pipeline: def.pipeline },
        },
```

換成（`existing?.data.colorClass ?? 'node-pending'` 這段是為了在重繪時保留舊的顏色狀態，但 `nodeType` 是靜態值不需要這個邏輯——`def.id` 只會是 `'preprocessor'` 或 `'featureEngineering'`，兩者都屬於 transform 類，直接寫死）：

```ts
        data: {
          icon: def.icon,
          label: def.label,
          nodeType: 'transform',
          description: def.desc,
          fields: [],
          config: { pipeline: def.pipeline },
        },
```

- [ ] **Step 4: computeCi 節點的 `nodeType`（第 314 行左右）**

找到：

```ts
        data: {
          icon: 'mdi-chart-areaspline-variant',
          label: 'Compute\nCI',
          colorClass: 'node-pending',
          description: 'Bootstrap 信賴區間',
          fields: [],
          config: {},
        },
```

換成：

```ts
        data: {
          icon: 'mdi-chart-areaspline-variant',
          label: 'Compute\nCI',
          nodeType: 'evaluate',
          description: 'Bootstrap 信賴區間',
          fields: [],
          config: {},
        },
```

- [ ] **Step 5: `ensureDynamicNodes` 裡第二處 preprocessor/featureEngineering 節點建立（第 360-361 行左右）**

找到：

```ts
        data: id === 'preprocessor'
          ? { icon: 'mdi-filter-cog-outline', label: 'Preprocessor', colorClass: 'node-pending', description: '資料前處理', fields: [], config: { pipeline: preprocessing } }
          : { icon: 'mdi-chart-scatter-plot', label: 'Feature\nEngineering', colorClass: 'node-pending', description: '特徵工程', fields: [], config: { pipeline: featureEng } },
```

換成：

```ts
        data: id === 'preprocessor'
          ? { icon: 'mdi-filter-cog-outline', label: 'Preprocessor', nodeType: 'transform', description: '資料前處理', fields: [], config: { pipeline: preprocessing } }
          : { icon: 'mdi-chart-scatter-plot', label: 'Feature\nEngineering', nodeType: 'transform', description: '特徵工程', fields: [], config: { pipeline: featureEng } },
```

- [ ] **Step 6: 跑型別檢查**

Run（在 `frontend/` 目錄下）: `npm run build`
Expected: 這個檔案不再報錯，只剩 `useWorkflowImport.ts` 與 `IconNode.vue` 報錯

- [ ] **Step 7: Commit**

```bash
git add frontend/src/composables/workflow/useWorkflowNodes.ts
git commit -m "feat(workflow): map dynamic nodes to nodeType, decouple color from status"
```

---

## Task 5: `useWorkflowImport.ts` 節點分類映射

**Files:**
- Modify: `frontend/src/composables/workflow/useWorkflowImport.ts`

**Interfaces:**
- Consumes：Task 2 的 `NodeType`
- Produces：從 Gemini 解析結果建立的 preprocessor/featureEngineering/model 節點都帶正確 `nodeType`

- [ ] **Step 1: pipeline 節點的 `nodeType`（第 130 行左右）**

找到：

```ts
      data: { icon: def.icon, label: def.label, colorClass: 'node-pending', description: def.desc, fields: [], config: { pipeline: def.pipeline } },
```

換成：

```ts
      data: { icon: def.icon, label: def.label, nodeType: 'transform', description: def.desc, fields: [], config: { pipeline: def.pipeline } },
```

- [ ] **Step 2: model 節點的 `nodeType`（第 149 行左右）**

找到：

```ts
        data: {
          icon: 'mdi-brain',
          label: name,
          colorClass: 'node-pending',
          description: purposeZh || name,
          fields: [],
          config: { modelName: name },
        },
```

換成：

```ts
        data: {
          icon: 'mdi-brain',
          label: name,
          nodeType: 'model',
          description: purposeZh || name,
          fields: [],
          config: { modelName: name },
        },
```

- [ ] **Step 3: 跑型別檢查**

Run（在 `frontend/` 目錄下）: `npm run build`
Expected: 這個檔案不再報錯，只剩 `IconNode.vue` 報錯（因為它還在讀 `props.data?.colorClass`，但因為 `defineProps<NodeProps>()` 沒指定泛型參數、`data` 型別是寬鬆的，這其實不會是型別錯誤，而是下個 task 要處理的邏輯錯誤——執行到這步 build 應該已經全綠）

Expected 若仍有錯誤：確認錯誤是不是都來自 `IconNode.vue`，如果是，繼續 Task 6

- [ ] **Step 4: Commit**

```bash
git add frontend/src/composables/workflow/useWorkflowImport.ts
git commit -m "feat(workflow): map imported nodes to nodeType"
```

---

## Task 6: `IconNode.vue` 重新設計

**Files:**
- Modify: `frontend/src/components/workflow/IconNode.vue`

**Interfaces:**
- Consumes：Task 1 的五個 `--color-node-*` token，Task 2 的 `NodeData.nodeType`
- Produces：節點渲染改成淺底 + 深色 icon + 邊框 + 完成徽章，不再讀 `colorClass`

這個檔案整個 `<script setup>` 和 `<style scoped>` 都要改，以下是完整的最終內容。

- [ ] **Step 1: 改 `<template>`，加上完成徽章**

把整個 `<template>` 換成：

```html
<template>
  <!-- 自訂節點 UI：左 target / 右 source + 圓形 icon + label -->
  <div
    class="icon-node-wrap"
    :style="{
      '--node-accent': accentColor,
      ...(highlightColor ? { '--highlight-color': highlightColor } : {}),
    }"
  >
    <!-- 右側輸出點：連到下一個節點 -->
    <Handle
      class="invisible-handle handle-right"
      :position="Position.Right"
      type="source"
    />
    <!-- 左側輸入點：接收前一個節點 -->
    <Handle
      class="invisible-handle handle-left"
      :position="Position.Left"
      type="target"
    />

    <!-- 節點主體 -->
    <div
      class="icon-node"
      :class="[nodeTypeClass, { 'node-highlighted': highlighted, 'flash-add': flashType === 'add', 'flash-remove': flashType === 'remove' }]"
    >
      <!-- running 時顯示 spinner，其餘顯示 icon -->
      <div v-if="status === 'running'" class="node-spinner" />
      <span v-else class="node-icon"><v-icon :icon="icon" size="26" /></span>
      <!-- 完成狀態：右下角重疊的勾勾徽章 -->
      <span v-if="status === 'finished'" class="node-done-badge">
        <v-icon icon="mdi-check" size="12" />
      </span>
    </div>

    <!-- 節點標籤（支援換行） -->
    <div class="icon-node-label">
      <span :class="{ 'label-selected': isSelected }">{{ label }}</span>
    </div>
  </div>
</template>
```

- [ ] **Step 2: 改 `<script setup>`**

把整個 `<script setup>` 換成：

```html
<script setup lang="ts">
  import { Handle, type NodeProps, Position } from '@vue-flow/core'
  import { computed } from 'vue'

  // Vue Flow 傳入的節點資料（id/data/selected...）
  const props = defineProps<NodeProps>()

  // 從節點 data 取出 icon，沒有就用預設 icon
  const icon = computed(() => String(props.data?.icon ?? 'mdi-circle'))

  // 從節點 data 取出 label
  const label = computed(() => String(props.data?.label ?? ''))

  // 從節點 data 取出分類，決定底色 class（見 docs/DESIGN_SYSTEM.md §2.3）
  const nodeType = computed(() => String(props.data?.nodeType ?? 'source'))
  const nodeTypeClass = computed(() => `node-${nodeType.value}`)

  // 選取指示線的顏色，直接用分類色 token，不用 JS 對照表重算一次
  const accentColor = computed(() => `var(--color-node-${nodeType.value})`)

  // demo 動畫狀態（running 顯示 spinner、finished 顯示右下角徽章）
  const status = computed(() => props.data?.status ?? null)

  // 用 data.isSelected 而非 Vue Flow 的 props.selected：
  // WorkflowCanvas 設了 elements-selectable="false"，內建的 selected 永遠是 false
  const isSelected = computed(() => Boolean(props.data?.isSelected))

  // Settings 步驟高亮外框
  const highlighted = computed(() => Boolean(props.data?.highlighted))
  const highlightColor = computed(() => props.data?.highlightColor as string | null ?? null)

  // 增刪元素時的閃色特效
  const flashType = computed(() => props.data?.flashType as 'add' | 'remove' | null ?? null)
</script>
```

- [ ] **Step 3: 改 `<style scoped>`**

把整個 `<style scoped>` 換成：

```html
<style scoped>
  .icon-node-wrap {
    --icon-size: 58px;
    /* calc() 自動隨 icon-size 同步，不需手動維護 */
    --icon-half: calc(var(--icon-size) / 2);
    position: relative;
    width: 122px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .icon-node {
    position: relative;
    overflow: visible;
    width: var(--icon-size);
    height: var(--icon-size);
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    /* 淺底配深色 icon（比照 Orange Data Mining 的構造），取代原本的飽和底配白色 icon */
    color: var(--color-ink-strong);
    border: 1.5px solid rgba(18, 36, 74, 0.16);
  }

  .flash-add::before,
  .flash-remove::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: inherit;
    animation: flash-overlay 1.2s linear forwards;
    pointer-events: none;
    z-index: 0;
  }

  .flash-add::before {
    background: var(--color-success);
  }

  .flash-remove::before {
    background: var(--color-error);
  }

  @keyframes flash-overlay {
    0%   { opacity: 0; }
    8%   { opacity: 0.85; }
    30%  { opacity: 0.85; }
    42%  { opacity: 0; }
    58%  { opacity: 0; }
    70%  { opacity: 0.85; }
    92%  { opacity: 0.85; }
    100% { opacity: 0; }
  }

  .node-highlighted {
    box-shadow: 0 0 0 4px var(--highlight-color, var(--color-accent));
    animation: highlight-pulse 1.4s ease-in-out infinite;
  }

  @keyframes highlight-pulse {
    0%, 100% { box-shadow: 0 0 0 3px var(--highlight-color, var(--color-accent)); }
    50% { box-shadow: 0 0 0 6px var(--highlight-color, var(--color-accent)); }
  }

  .node-spinner,
  .node-icon {
    position: relative;
    z-index: 1;
  }

  .node-spinner {
    width: 22px;
    height: 22px;
    border: 3px solid color-mix(in oklab, var(--color-ink-strong) 25%, transparent);
    border-top-color: var(--color-ink-strong);
    border-radius: 50%;
    animation: node-spin 0.75s linear infinite;
  }

  @keyframes node-spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* 右下角重疊的完成徽章，外圈套一圈畫布底色把它跟節點本體分開 */
  .node-done-badge {
    position: absolute;
    right: -2px;
    bottom: -2px;
    z-index: 2;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    border: 2px solid var(--color-page);
    border-radius: 50%;
    background: var(--color-success);
    color: #fff;
  }

  .icon-node-label {
    min-height: 32px;
    text-align: center;
    font-size: 13px;
    line-height: 1.2;
    font-weight: 500;
    color: var(--color-text);
    white-space: pre-line;
  }

  /* inline-block 讓 span 高度貼合文字；掛在外層 .icon-node-label 的話，
     它的 min-height 會把線推得離單行標籤很遠 */
  .label-selected {
    position: relative;
    display: inline-block;
    padding-bottom: 8px;
  }

  .label-selected::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    width: 34px;
    height: 2px;
    transform: translateX(-50%);
    border-radius: 2px;
    background: var(--node-accent, var(--color-node-source));
    animation: underline-in var(--dur-base) var(--ease-out);
  }

  @keyframes underline-in {
    from {
      transform: translateX(-50%) scaleX(0);
      opacity: 0;
    }

    to {
      transform: translateX(-50%) scaleX(1);
      opacity: 1;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .label-selected::after {
      animation: none;
    }
  }

  .node-source {
    background: var(--color-node-source);
  }

  .node-transform {
    background: var(--color-node-transform);
  }

  .node-visualize {
    background: var(--color-node-visualize);
  }

  .node-model {
    background: var(--color-node-model);
  }

  .node-evaluate {
    background: var(--color-node-evaluate);
  }

  .invisible-handle {
    opacity: 0;
    width: 8px;
    height: 8px;
    border: none;
    background: transparent;
    /* 垂直方向對齊到 icon 圓形中心，不是整個節點 wrapper 的中心 */
    top: var(--icon-half) !important;
  }

  /* 把 left/right handle 從容器邊緣移到 icon 邊緣 */
  .handle-left {
    left: calc(50% - var(--icon-half)) !important;
  }

  .handle-right {
    right: calc(50% - var(--icon-half)) !important;
  }

  @media (max-width: 1024px) {
    .icon-node-wrap {
      --icon-size: 54px;
      width: 108px;
    }

    .icon-node-label {
      font-size: 12px;
      min-height: 28px;
    }
  }

  @media (max-width: 768px) {
    .icon-node-wrap {
      --icon-size: 48px;
      width: 96px;
      gap: 6px;
    }

    .icon-node-label {
      font-size: 11px;
      line-height: 1.15;
      min-height: 24px;
    }
  }
</style>
```

這裡有幾個跟原檔案的差異，注意：
- `.icon-node` 的 `overflow: hidden` 改成 `overflow: visible`：原本 hidden 是為了讓 `flash-add`/`flash-remove` 的圓形疊層不溢出，但完成徽章要露在節點右下角外面，`hidden` 會把它裁掉，所以改成 `visible`。`flash-add`/`flash-remove` 的 `::before` 本身有 `border-radius: inherit` 會自己維持圓形，不靠父層裁切。
- `.node-spinner` 的邊框顏色從白色系（`rgba(255,255,255,0.35)` / `#fff`）改成用 `--color-ink-strong` 混色：因為節點底色從深色變淺色，白色系的 spinner 在淺底上會看不見。
- `.label-selected::after` 的顏色來源從 JS 算好的 `--node-accent` fallback 值（原本是硬寫 `#005dff`）改成 `var(--color-node-source)`（fallback 用哪個分類色不影響視覺，因為 `--node-accent` 平常都會被 script 設定覆蓋，只是型別安全的預設值）。
- `.label-selected::after` 的 `animation: underline-in 0.2s ease-out` 改成 `animation: underline-in var(--dur-base) var(--ease-out)`（動畫時長 token 化，這是 §4 清理範圍的一部分，因為這個檔案整個重寫，順手一起做）。

- [ ] **Step 4: 跑型別檢查與 lint**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/IconNode.vue
npm run build
```
Expected: 兩個都 PASS，這是 Task 2 開始累積的型別錯誤全部清完的時間點

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workflow/IconNode.vue
git commit -m "feat(workflow): redesign IconNode with nodeType colors and completion badge"
```

---

## Task 7: `UploadDialog.vue` 按鈕遷移 + 清理

**Files:**
- Modify: `frontend/src/components/workflow/UploadDialog.vue`

**Interfaces:**
- Consumes：`components/ui/AppButton.vue`

- [ ] **Step 1: import AppButton**

在 `<script setup lang="ts">` 的 `import { ref, watch } from 'vue'` 下面加一行：

```ts
  import AppButton from '@/components/ui/AppButton.vue'
```

- [ ] **Step 2: 關閉按鈕遷移**

把：

```html
          <button
            class="upload-dialog-close"
            type="button"
            @click="emit('close')"
          >
            ×
          </button>
```

換成：

```html
          <AppButton
            aria-label="關閉"
            icon-only
            variant="ghost"
            @click="emit('close')"
          >
            <v-icon icon="mdi-close" size="18" />
          </AppButton>
```

- [ ] **Step 3: 取消/上傳按鈕遷移**

把：

```html
        <button
          class="btn btn-secondary"
          type="button"
          @click="emit('close')"
        >
          取消
        </button>
        <button
          class="btn btn-primary"
          :disabled="!selectedFile"
          type="button"
          @click="handleConfirm"
        >
          上傳
        </button>
```

換成：

```html
        <AppButton variant="secondary" @click="emit('close')">
          取消
        </AppButton>
        <AppButton :disabled="!selectedFile" variant="primary" @click="handleConfirm">
          上傳
        </AppButton>
```

（原本的 `.btn`/`.btn-primary`/`.btn-secondary` 在這個檔案的 `<style>` 裡沒有對應規則——這兩顆按鈕原本其實是沒有樣式的原生按鈕，遷移後才第一次有正確樣式，不用刪除任何 CSS。）

- [ ] **Step 4: 刪除 `.upload-dialog-close` 的 CSS（AppButton 自己處理樣式）**

刪除：

```css
  .upload-dialog-close {
    border: none;
    background: rgba(243, 244, 246, 0.9);
    width: 36px;
    height: 36px;
    border-radius: 999px;
    color: var(--color-text);
    font-size: 18px;
    cursor: pointer;
  }
```

- [ ] **Step 5: 其餘樣式清理**

在同一個 `<style scoped>` 裡：

- `border-radius: 20px;`（`.upload-dialog-card`，第 121 行）→ `border-radius: var(--radius-lg);`（20 更接近 16）
- `border-radius: 18px;`（`.upload-dropzone`，第 165 行）→ `border-radius: var(--radius-lg);`
- `font-weight: 600;`（`.upload-dropzone__text`，第 187 行）→ `font-weight: 500;`
- `transition: border-color 0.2s ease, background 0.2s ease;`（`.upload-dropzone`，第 171 行）→ `transition: border-color var(--dur-base) ease, background var(--dur-base) ease;`

`.upload-dropzone__browse` 的 `color: #fff`（第 197 行）維持不變——這是 `<label>` 不是 `<button>`，白字疊在 `var(--color-accent)` 色塊上，不在按鈕遷移範圍內，也沒有對應 token。

- [ ] **Step 6: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/UploadDialog.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/workflow/UploadDialog.vue
git commit -m "refactor(workflow): migrate UploadDialog buttons to AppButton, apply design tokens"
```

---

## Task 8: `WorkflowCanvas.vue` 圓角清理

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowCanvas.vue`

這個檔案沒有按鈕、沒有硬寫 hex、沒有字重或動畫時長問題，只有 3 處圓角。

- [ ] **Step 1: 圓角 token 化**

在 `<style scoped>` 裡：

- 第 197 行 `border-radius: 12px;` → `border-radius: var(--radius-md);`
- 第 213 行 `border-radius: 12px;` → `border-radius: var(--radius-md);`
- 第 262 行（`@media (max-width: 768px)` 內的 `.flow-area`）`border-radius: 10px;` → `border-radius: var(--radius-md);`（10px 是容器類元素，歸 md）

- [ ] **Step 2: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/WorkflowCanvas.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/workflow/WorkflowCanvas.vue
git commit -m "style(workflow): apply radius tokens to WorkflowCanvas"
```

---

## Task 9: `WorkflowWorkspace.vue` 死代碼刪除 + 按鈕遷移 + 清理

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`

**Interfaces:**
- Consumes：`components/ui/AppButton.vue`

- [ ] **Step 1: import AppButton**

在 `<script setup>` 裡任一個既有 import 下面加：

```ts
  import AppButton from '@/components/ui/AppButton.vue'
```

- [ ] **Step 2: 「查看結果」按鈕遷移**

找到（template 開頭附近）：

```html
    <button
      v-if="workflowResult"
      class="view-results-btn"
      type="button"
      @click="router.push(`/hub/projects/${projectId}/result`)"
    >
      查看結果
    </button>
```

換成：

```html
    <AppButton
      v-if="workflowResult"
      class="view-results-btn"
      variant="primary"
      @click="router.push(`/hub/projects/${projectId}/result`)"
    >
      查看結果
    </AppButton>
```

（保留 `class="view-results-btn"` 是為了維持它在 template 裡的絕對定位——這個 class 接下來只留 `position`/`top`/`right`/`z-index` 這幾個版面屬性，不留按鈕外觀樣式，見 Step 3。）

- [ ] **Step 3: 刪除死代碼按鈕樣式，`.view-results-btn` 只留版面定位**

找到從 `.demo-btn {` 到 `.gemini-upload-btn:disabled { ... }`（大約第 651-810 行）這一大段，這段裡有 6 組按鈕樣式：`.demo-btn`、`.execute-workflow-btn`、`.view-results-btn`、`.json-upload-btn`、`.paper-upload-btn`、`.gemini-upload-btn`（含各自的 `:hover`/`:disabled` 變體）。除了 `.view-results-btn` 外，其餘 5 組在 template 或 script 都查無引用，是舊版工具列的殘留死代碼。

把整段換成只保留 `.view-results-btn` 的版面定位部分（拿掉外觀樣式，因為外觀交給 `AppButton`）：

```css
  .view-results-btn {
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 5;
  }
```

也就是說，原本 `.demo-btn` 開始到 `.gemini-upload-btn:disabled` 結束的一大段（`.workspace-canvas` 規則之後、`.workflow-result` 規則之前的全部內容），改成只有上面這 6 行。

- [ ] **Step 4: `.workflow-error` 的 hex 色值**

找到：

```css
  .workflow-error {
    margin-bottom: 10px;
    color: #ef4444;
    font-size: 13px;
    font-weight: 600;
  }
```

換成：

```css
  .workflow-error {
    margin-bottom: 10px;
    color: var(--color-error-text);
    font-size: 13px;
    font-weight: 500;
  }
```

- [ ] **Step 5: 其餘圓角/字重/動畫時長清理**

在 `<style scoped>` 裡（行號可能因為 Step 3 刪除內容而往前移，用內容比對定位）：

- `.workspace-canvas-wrap`（或含 `overflow: auto` 那個容器選擇器）的 `border-radius: 16px 16px 0 0;` → `border-radius: var(--radius-lg) var(--radius-lg) 0 0;`
- `.workflow-result` 的 `border-radius: 16px;` → `border-radius: var(--radius-lg);`
- `.options-drawer__scroll::-webkit-scrollbar-thumb` 的 `border-radius: 999px;` 維持不變（pill，字面量已經是對的）
- `.options-drawer__bar` 的 `border-radius: 999px;` 維持不變
- `.workspace`（`@media (max-width: 768px)` 內）的 `border-radius: 12px;` → `border-radius: var(--radius-md);`
- `.options-drawer`（桌面版）的 `border-top-left-radius: 14px;` / `border-top-right-radius: 14px;` → 兩個都改成 `var(--radius-lg)`（14px 剛好在 12/16 正中間，這是覆蓋整個設定面板的大型底部抽屜，取視覺份量較重的 lg）
- `.options-drawer`（`@media (max-width: 768px)` 內覆寫）的 `border-top-left-radius: 12px;` / `border-top-right-radius: 12px;` → 兩個都改成 `var(--radius-md)`
- `.options-drawer` 的 `transition: height 260ms cubic-bezier(0.4, 0, 0.2, 1);` → `transition: height var(--dur-slow) cubic-bezier(0.4, 0, 0.2, 1);`
- 6 處 `transition: background 0.15s, opacity 0.15s;`（原本分布在剛才刪除的 6 組按鈕樣式裡，Step 3 已經連同整段刪除，這裡不用再處理）
- 找 `transition: transform 0.22s ease, opacity 0.22s ease;` → `transition: transform var(--dur-base) ease, opacity var(--dur-base) ease;`
- 找 `transition: opacity 180ms ease, transform 180ms ease;` → `transition: opacity var(--dur-base) ease, transform var(--dur-base) ease;`

- [ ] **Step 6: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/WorkflowWorkspace.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 7: 手動在瀏覽器確認**

打開 workflow 頁面，確認：
- 「查看結果」按鈕位置、樣式正常（右上角、實色藏青底）
- 設定抽屜（options drawer）拖拉展開/收合正常，圓角看起來沒變
- 沒有任何按鈕消失或跑版（demo-btn/execute-workflow-btn/json-upload-btn/paper-upload-btn/gemini-upload-btn 這 5 個 class 名稱本來就沒有對應的畫面元素，刪除它們的 CSS 不會讓畫面上少東西）

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "refactor(workflow): remove dead toolbar button styles, migrate view-results button"
```

---

## Task 10: `WorkflowOptionsPanel.vue` 死代碼刪除 + 按鈕遷移 + 清理

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowOptionsPanel.vue`

**Interfaces:**
- Consumes：`components/ui/AppButton.vue`

- [ ] **Step 1: import AppButton**

在 `<script setup>` 裡加：

```ts
  import AppButton from '@/components/ui/AppButton.vue'
```

- [ ] **Step 2: 「新增模型」按鈕遷移**

找到（第 127-135 行左右）：

```html
          <div class="form-row">
            <button
              class="btn btn-primary"
              :disabled="!selectedModel || modelOptionsLoading"
              type="button"
              @click="handleAddModel"
            >
              新增模型
            </button>
```

換成：

```html
          <div class="form-row">
            <AppButton
              :disabled="!selectedModel || modelOptionsLoading"
              variant="primary"
              @click="handleAddModel"
            >
              新增模型
            </AppButton>
```

- [ ] **Step 3: 刪除完全沒用到的死代碼區塊**

找到從 `.upload-card {`（約第 485 行）開始，到 `.actions {` 規則結束（約第 740 行，`.btn {` 規則開始之前）為止的整段——這段涵蓋 `.upload-card`、`.upload-card__*`、`.upload-modal-*`、`.details__*`、`.preview-box`、`.hint`、`.actions`，全部在這個檔案的 template 裡查無引用（這個元件現在的上傳流程走別的元件，這段是舊版遺留），整段刪除。

刪除後，`.form-row select { ... }` 規則結束的地方應該直接接到 `.btn {`（第 4 步會處理 `.btn`）。

- [ ] **Step 4: `.btn`/`.btn-primary` 隨按鈕遷移一起刪除**

刪除：

```css
  .btn {
    border: none;
    border-radius: 10px;
    padding: 8px 16px;
    cursor: pointer;
    background: color-mix(in oklab, var(--color-accent) 12%, transparent);
    color: var(--color-accent);
    font-weight: 600;
    font-size: 13px;
    transition: background 0.15s;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-primary {
    background: var(--color-accent);
    color: #fff;
    font-weight: 700;
  }

  .btn-primary:hover {
    background: color-mix(in oklab, var(--color-accent) 85%, black);
  }
```

（實際內容以檔案為準，抓的是 `.btn {` 到 `.btn-primary:hover { ... }` 這一整組，`@media` 區塊裡的 `.btn { width: 100%; }` 也要一併刪除，見下一步。）

- [ ] **Step 5: 清掉 `@media` 內對應死 class 的覆寫**

在 `@media (max-width: 768px) { ... }` 區塊裡，刪除 `.details__summary { ... }`、`.actions { ... }`、`.btn { width: 100%; }` 這三條（同樣是死 class 的響應式覆寫），保留 `.setting-area`、`.panel-header h3`、`.panel-header p`、`.form-row`、`.form-row label`、`.form-row input, .form-row select` 這些仍在使用的規則。

- [ ] **Step 6: 剩餘清理**

- `.setting-area` 的 `border-radius: 0;` 維持不變（是明確重置，不在圓角規範管轄範圍）
- `.form-row label` 的 `font-weight: 600;` → `font-weight: 500;`
- `.form-row input, .form-row select` 的 `border-radius: 8px;` → `border-radius: var(--radius-sm);`

- [ ] **Step 7: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/WorkflowOptionsPanel.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 8: 手動在瀏覽器確認**

打開 workflow 頁面，點進一個節點的設定面板，確認「新增模型」按鈕正常、畫面沒有跑版（刪除的死代碼本來就沒有對應畫面元素）。

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/workflow/WorkflowOptionsPanel.vue
git commit -m "refactor(workflow): remove dead upload-modal styles, migrate add-model button"
```

---

## Task 11: `TestScorePanel.vue` 清理

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/TestScorePanel.vue`

沒有按鈕、沒有硬寫 hex、沒有動畫時長問題，只有字重與圓角。

- [ ] **Step 1: 字重 token 化**

在 `<style scoped>` 裡，4 處 `font-weight: 700;` / `font-weight: 600;`（第 105、136、166、179 行）全部改成 `font-weight: 500;`。

- [ ] **Step 2: 圓角 token 化**

第 113 行 `border-radius: 12px;` → `border-radius: var(--radius-md);`

- [ ] **Step 3: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/nodePanel/TestScorePanel.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/TestScorePanel.vue
git commit -m "style(workflow): apply typography and radius tokens to TestScorePanel"
```

---

## Task 12: `DataTablePanel.vue` 按鈕遷移 + 死規則刪除 + 清理

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue`

**Interfaces:**
- Consumes：`components/ui/AppButton.vue`

- [ ] **Step 1: import AppButton**

在 `<script setup>` 裡加：

```ts
  import AppButton from '@/components/ui/AppButton.vue'
```

- [ ] **Step 2: Reset/Apply 按鈕遷移**

找到：

```html
        <div class="column-settings-actions">
          <button class="btn-reset" type="button" @click="resetColumnSettings">
            Reset
          </button>
          <button
            class="btn-apply"
            :class="{ 'btn-apply--disabled': !hasTarget || !props.loading }"
            :disabled="!hasTarget || !props.loading"
            type="button"
            @click="applyColumnSettings"
          >
            繼續
          </button>
        </div>
```

換成（`:disabled` 的判斷式原封不動保留，不是本次要修的邏輯）：

```html
        <div class="column-settings-actions">
          <AppButton variant="secondary" @click="resetColumnSettings">
            Reset
          </AppButton>
          <AppButton
            :disabled="!hasTarget || !props.loading"
            variant="primary"
            @click="applyColumnSettings"
          >
            繼續
          </AppButton>
        </div>
```

- [ ] **Step 3: 刪除 `.btn-reset`/`.btn-apply`/`.btn-apply--disabled` CSS**

刪除：

```css
  .btn-reset,
  .btn-apply {
    min-width: 88px;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    cursor: pointer;
  }

  .btn-reset {
    background: var(--color-surface);
    color: var(--color-text);
    border: 1px solid color-mix(in oklab, var(--color-accent) 18%, transparent);
  }

  .btn-apply {
    background: var(--color-accent);
    color: #fff;
  }

  .btn-apply--disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }
```

- [ ] **Step 4: 刪除死規則 `.role-select--attention`**

找到並刪除（含它上面那行說明用途已經不存在的註解）：

```css
  /* 未選 target 前，Role 下拉維持靜態高亮，把動效留給漣漪圈 */
  .role-select--attention {
    border-color: #94a3b8;
  }
```

（這個 class 在 template 裡查無引用，是舊功能移除後留下的殘留規則。）

- [ ] **Step 5: 其餘 hex/圓角/字重/動畫時長清理**

- `.data-table-guide--ready` 的 `color: #16a34a;` → `color: var(--color-success);`
- `.column-name-input` 的 `border-radius: 8px;` → `border-radius: var(--radius-sm);`
- `.column-settings-table select` 的 `border-radius: 8px;` → `border-radius: var(--radius-sm);`（若同一規則內出現多次 8px，一併換）
- `border-radius: 16px;`（`.data-table-guide` 或相鄰卡片容器，第 440 行附近）→ `border-radius: var(--radius-lg);`
- `border-radius: 12px;`（第 470、516 行）→ `border-radius: var(--radius-md);`
- `border-radius: 3px;`（第 550 行）維持不變（極小視覺細節，不在規範管轄）
- `border-radius: 50%;`（第 704、711、759 行）維持不變（圓形頭像/圖示）
- 兩處 `font-weight: 600;`（第 529、594 行）→ `font-weight: 500;`
- `transition: border-color 0.12s, box-shadow 0.12s;`（第 664 行）→ `transition: border-color var(--dur-fast), box-shadow var(--dur-fast);`
- `transition: opacity 0.3s ease;`（第 694 行）→ `transition: opacity var(--dur-slow) ease;`

- [ ] **Step 6: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/nodePanel/DataTablePanel.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 7: 手動在瀏覽器確認**

打開 Data Table 節點的設定面板，Reset/Apply 按鈕正常運作、disabled 狀態正確（未選 target 或非 loading 狀態時 Apply 應為 disabled）。

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "refactor(workflow): migrate DataTablePanel buttons, remove dead rule, apply tokens"
```

---

## Task 13: `DistributionPanel.vue` 按鈕遷移 + 長條圖顏色 + 清理

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DistributionPanel.vue`

**Interfaces:**
- Consumes：`components/ui/AppButton.vue`

- [ ] **Step 1: import AppButton**

在 `<script setup>` 裡加：

```ts
  import AppButton from '@/components/ui/AppButton.vue'
```

- [ ] **Step 2: 「更多/收起」toggle 按鈕遷移**

找到：

```html
            <button
              v-if="isChartLabelLong(chart.label)"
              class="distribution-title-toggle"
              type="button"
              @click="toggleChartLabel(index)"
            >
              {{ isChartLabelExpanded(index) ? "收起" : "更多" }}
            </button>
```

換成：

```html
            <AppButton
              v-if="isChartLabelLong(chart.label)"
              class="distribution-title-toggle"
              variant="ghost"
              @click="toggleChartLabel(index)"
            >
              {{ isChartLabelExpanded(index) ? "收起" : "更多" }}
            </AppButton>
```

- [ ] **Step 3: 長條圖顏色調淡**

找到 SVG 裡的長條 `<rect>`：

```html
                  <rect
                    fill="var(--color-accent)"
```

換成：

```html
                  <rect
                    fill="color-mix(in oklab, var(--color-ink) 45%, white)"
```

- [ ] **Step 4: `.distribution-title-toggle` 樣式調整為 AppButton 的補充定位（外觀交給 AppButton，這裡只留版面）**

找到：

```css
  .distribution-title-toggle {
    border: none;
    background: transparent;
    color: var(--color-accent);
    font-size: 12px;
    padding: 0;
    margin-bottom: 8px;
    cursor: pointer;
    text-align: left;
  }
```

換成：

```css
  .distribution-title-toggle {
    margin-bottom: 8px;
  }
```

（`AppButton` 的 `ghost` variant 已經處理顏色、padding、cursor；這裡只保留跟下面內容的間距。遷移後這顆按鈕會比原本的純文字連結明顯一些——變成有 padding 的小按鈕，這是預期內的外觀變化，不是缺陷。）

- [ ] **Step 5: 其餘字重/圓角清理**

- `.distribution-title`（第 303 行）`font-weight: 700;` → `font-weight: 500;`
- `.distribution-chart-title`（第 384 行）`font-weight: 600;` → `font-weight: 500;`
- `.distribution-empty` 的 `border-radius: 12px;`（第 316 行）→ `border-radius: var(--radius-md);`
- `.distribution-chart-title.expanded` 附近的 `border-radius: 16px;`（第 366 行）→ `border-radius: var(--radius-lg);`
- 第 376 行 `border-radius: 16px;` → `border-radius: var(--radius-lg);`
- 第 427 行 `border-radius: 12px;` → `border-radius: var(--radius-md);`
- 第 342 行 `border-radius: 999px;` 維持不變（pill）

- [ ] **Step 6: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/nodePanel/DistributionPanel.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 7: 手動在瀏覽器確認**

打開 Distribution 節點面板，確認長條圖顏色變淡但仍看得出資料量差異、標籤過長時的「更多/收起」按鈕正常切換。

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/DistributionPanel.vue
git commit -m "refactor(workflow): lighten distribution chart bars, migrate toggle button"
```

---

## Task 14: `FeatureEngineeringPanel.vue` 清理

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/FeatureEngineeringPanel.vue`

沒有按鈕、沒有動畫時長問題。有 hex、圓角、字重。

- [ ] **Step 1: hex 清理**

找到：

```css
    border: 1px solid #e2e8f0;
```

（`.step-*` 容器邊框，第 95 行）→ `border: 1px solid var(--color-border);`

找到：

```css
  .step-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #e0e7ff;
    color: #4f46e5;
```

換成（改用品牌色淡色調的軟性徽章，跟其他地方 `color-mix` 用法一致）：

```css
  .step-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: color-mix(in oklab, var(--color-ink) 12%, white);
    color: var(--color-ink);
```

找到第 137 行 `border-top: 1px dashed #e2e8f0;` → `border-top: 1px dashed var(--color-border);`

- [ ] **Step 2: 圓角清理**

第 96 行 `border-radius: 10px;`（輸入類元素，跟 `.step-*` 容器同一條規則）→ `border-radius: var(--radius-sm);`
第 109 行 `border-radius: 50%;` 維持不變（`.step-index` 圓形徽章）

- [ ] **Step 3: 字重清理**

第 116 行 `font-weight: 700;` → `font-weight: 500;`（`.step-index` 內文字）
第 122 行 `font-weight: 600;` → `font-weight: 500;`（`.step-label`）

- [ ] **Step 4: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/nodePanel/FeatureEngineeringPanel.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/FeatureEngineeringPanel.vue
git commit -m "style(workflow): apply design tokens to FeatureEngineeringPanel"
```

---

## Task 15: `FeatureImportancePanel.vue` 清理

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue`

沒有按鈕、沒有 hex、沒有動畫時長問題，只有 1 處字重、1 處圓角。

- [ ] **Step 1: 清理**

- 第 231 行 `font-weight: 600;` → `font-weight: 500;`
- 第 209 行 `border-radius: 12px;` → `border-radius: var(--radius-md);`

- [ ] **Step 2: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/nodePanel/FeatureImportancePanel.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue
git commit -m "style(workflow): apply typography and radius tokens to FeatureImportancePanel"
```

---

## Task 16: `PreprocessorPanel.vue` 清理

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/PreprocessorPanel.vue`

跟 `FeatureEngineeringPanel.vue` 是同樣結構的姊妹元件，違規項目完全對應。

- [ ] **Step 1: hex 清理**

第 95 行 `border: 1px solid #e2e8f0;` → `border: 1px solid var(--color-border);`

找到：

```css
  .step-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #e0e7ff;
    color: #4f46e5;
```

換成：

```css
  .step-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: color-mix(in oklab, var(--color-ink) 12%, white);
    color: var(--color-ink);
```

第 137 行 `border-top: 1px dashed #e2e8f0;` → `border-top: 1px dashed var(--color-border);`

- [ ] **Step 2: 圓角清理**

第 96 行 `border-radius: 10px;` → `border-radius: var(--radius-sm);`
第 109 行 `border-radius: 50%;` 維持不變

- [ ] **Step 3: 字重清理**

第 116 行 `font-weight: 700;` → `font-weight: 500;`
第 122 行 `font-weight: 600;` → `font-weight: 500;`

- [ ] **Step 4: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/nodePanel/PreprocessorPanel.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/PreprocessorPanel.vue
git commit -m "style(workflow): apply design tokens to PreprocessorPanel"
```

---

## Task 17: `SettingsPanel.vue` 按鈕遷移 + 清理（最大檔案）

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/SettingsPanel.vue`

**Interfaces:**
- Consumes：`components/ui/AppButton.vue`

這個檔案有 8 個真正的按鈕要遷移，`wizard-tab`（頁籤）與 `ci-toggle`（開關）不動。

- [ ] **Step 1: import AppButton**

在 `<script setup>` 裡加：

```ts
  import AppButton from '@/components/ui/AppButton.vue'
```

- [ ] **Step 2: 「新增前處理」按鈕遷移**

找到：

```html
        <button class="add-btn" :disabled="!newPreprocessType" type="button" @click="addPreprocessStep">
          新增
        </button>
```

換成：

```html
        <AppButton :disabled="!newPreprocessType" variant="secondary" @click="addPreprocessStep">
          新增
        </AppButton>
```

- [ ] **Step 3: 「移除」按鈕遷移（前處理項目，第一處）**

找到：

```html
            <button class="del-btn" title="移除" type="button" @click="removePreprocessStep(i)">✕</button>
```

換成：

```html
            <AppButton aria-label="移除" icon-only title="移除" variant="ghost" @click="removePreprocessStep(i)">
              <v-icon icon="mdi-close" size="14" />
            </AppButton>
```

- [ ] **Step 4: 「新增特徵工程」按鈕遷移**

找到：

```html
        <button class="add-btn" :disabled="!newFEType" type="button" @click="addFEStep">
          新增
        </button>
```

換成：

```html
        <AppButton :disabled="!newFEType" variant="secondary" @click="addFEStep">
          新增
        </AppButton>
```

- [ ] **Step 5: 「移除」按鈕遷移（特徵工程項目，第二處）**

找到：

```html
            <button class="del-btn" title="移除" type="button" @click="removeFEStep(i)">✕</button>
```

換成：

```html
            <AppButton aria-label="移除" icon-only title="移除" variant="ghost" @click="removeFEStep(i)">
              <v-icon icon="mdi-close" size="14" />
            </AppButton>
```

- [ ] **Step 6: 「新增模型」按鈕遷移**

找到：

```html
        <button class="add-btn" :disabled="!selectedModel" type="button" @click="addModel">
          新增
        </button>
```

換成：

```html
        <AppButton :disabled="!selectedModel" variant="secondary" @click="addModel">
          新增
        </AppButton>
```

- [ ] **Step 7: 「移除」按鈕遷移（模型項目，第三處）**

找到：

```html
            <button class="del-btn" title="移除" type="button" @click="emit('remove-model', modelName(model))">✕</button>
```

換成：

```html
            <AppButton aria-label="移除" icon-only title="移除" variant="ghost" @click="emit('remove-model', modelName(model))">
              <v-icon icon="mdi-close" size="14" />
            </AppButton>
```

- [ ] **Step 8: 「回 Data Table」與「上一步」按鈕遷移**

找到：

```html
      <button
        class="btn-back"
        type="button"
        @click="emit('back-node')"
      >
        回 Data Table
      </button>
      <div class="settings-footer__right">
        <button
          v-if="currentStep > 0"
          class="btn-back"
          type="button"
          @click="currentStep -= 1"
        >
          上一步
        </button>
```

換成：

```html
      <AppButton variant="secondary" @click="emit('back-node')">
        回 Data Table
      </AppButton>
      <div class="settings-footer__right">
        <AppButton
          v-if="currentStep > 0"
          variant="secondary"
          @click="currentStep -= 1"
        >
          上一步
        </AppButton>
```

- [ ] **Step 9: 主要動作按鈕遷移（用 primary，讓它視覺上更明確是主要動作）**

找到：

```html
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

換成：

```html
        <AppButton
          :disabled="isPrimaryDisabled"
          variant="primary"
          @click="handlePrimary"
        >
          {{ primaryLabel }}
        </AppButton>
      </div>
```

- [ ] **Step 10: 刪除 `.add-btn`/`.del-btn`/`.btn-continue`/`.btn-back` 相關 CSS**

刪除 `.add-btn`、`.add-btn:disabled`、`.add-btn:not(:disabled):hover`（約第 514-540 行）整組。

刪除 `.del-btn`、`.del-btn:hover`（約第 631-650 行）整組。

刪除 `.btn-continue`、`.btn-continue--disabled`（約第 778-793 行）整組。

刪除 `.btn-back`、`.btn-back:hover`（約第 794-810 行）整組。

（實際內容與行號以檔案當下狀態為準——每組都是「選擇器 + 到下一個獨立選擇器之間」的完整區塊，`wizard-tab`/`ci-toggle` 相關規則不在此列，不要刪到。）

- [ ] **Step 11: 剩餘字重清理**

以下全部把 `font-weight: 700;` 或 `font-weight: 600;` 改成 `font-weight: 500;`（`wizard-tab`/`ci-card` 相關的也要改，這條規則沒有例外）：

- `.wizard-tab--active`
- `.wizard-tab__num`
- `.wizard-tab__required`
- `.item-idx`
- `.item-name`
- `.ci-card__title`
- `.ci-card__status`

- [ ] **Step 12: 剩餘圓角清理**

- `.wizard-tabs` `border-radius: 12px;` → `border-radius: var(--radius-md);`
- `.wizard-tab` `border-radius: 8px;` → `border-radius: var(--radius-sm);`
- `.wizard-tab__num` `border-radius: 50%;` 維持不變
- `.wizard-tab__required` `border-radius: 6px;` → `border-radius: var(--radius-sm);`
- `.item-row` `border-radius: 8px;` → `border-radius: var(--radius-sm);`
- `.item-idx` `border-radius: 50%;` 維持不變
- `.param-num` `border-radius: 6px;` → `border-radius: var(--radius-sm);`
- `.ci-card` `border-radius: 10px;` → `border-radius: var(--radius-md);`
- `.ci-card__status` `border-radius: 6px;` → `border-radius: var(--radius-sm);`
- `.ci-toggle` `border-radius: 999px;` 維持不變（pill，開關本來就該是膠囊形）
- `.ci-toggle__thumb` `border-radius: 50%;` 維持不變

- [ ] **Step 13: 剩餘 hex 清理**

- `.wizard-tab--active .wizard-tab__num` 的 `color: #fff;` 維持不變（實色底上的白字，不在按鈕遷移範圍內、沒有對應 token）
- `.wizard-tab__required` 的 `color: #ef4444;` → `color: var(--color-error);`
- `.del-btn` / `.del-btn:hover` 的 `color: #94a3b8;` / `color: #ef4444;` 隨 Step 10 刪除，不用處理
- `.empty-hint` 的 `color: #94a3b8;` → `color: var(--color-ink-soft);`
- `.ci-toggle` 的 `background: #e2e8f0;` → `background: var(--color-border);`

- [ ] **Step 14: 剩餘動畫時長清理**

- `.wizard-tab` 的 `transition: background 0.15s, color 0.15s, box-shadow 0.15s;` → `transition: background var(--dur-fast), color var(--dur-fast), box-shadow var(--dur-fast);`
- `.wizard-tab__num` 的 `transition: background 0.15s, color 0.15s;` → `transition: background var(--dur-fast), color var(--dur-fast);`
- `.item-name`（或該行所在選擇器）的 `transition: opacity 0.12s;` → `transition: opacity var(--dur-fast);`
- `.param-num`（或該行所在選擇器）的 `transition: color 0.12s, background 0.12s;` → `transition: color var(--dur-fast), background var(--dur-fast);`
- `.ci-toggle` 的 `transition: background 0.2s;` → `transition: background var(--dur-base);`
- `.ci-toggle__thumb` 的 `transition: transform 0.2s;` → `transition: transform var(--dur-base);`

- [ ] **Step 15: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/nodePanel/SettingsPanel.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 16: 手動在瀏覽器確認**

打開 Settings 節點面板，逐一確認：
- 4 個步驟頁籤（`wizard-tab`）切換正常，樣式沒被誤套用 `AppButton`
- 前處理/特徵工程/模型 3 組的「新增」「移除」按鈕正常運作
- 「回 Data Table」「上一步」「繼續」三顆按鈕的視覺層級：繼續（primary，實色）明顯比另外兩顆（secondary）更突出
- Compute CI 的開關（`ci-toggle`）切換正常，樣式沒被誤套用 `AppButton`

- [ ] **Step 17: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/SettingsPanel.vue
git commit -m "refactor(workflow): migrate SettingsPanel buttons to AppButton, apply design tokens"
```

---

## Task 18: `ComputeCiPanel.vue` 清理

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ComputeCiPanel.vue`

沒有按鈕，有 hex、圓角、字重問題。

- [ ] **Step 1: hex 清理**

找到 `.ci-info__notice`（或其 `color` 屬性所在選擇器）：

```css
    color: #92400e;
```

換成：

```css
    color: var(--color-warning-text);
```

（這個顏色用在 `background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25);` 的琥珀色提示框裡，`#92400e` 是深琥珀文字色，語意正是 warning。）

- [ ] **Step 2: 字重清理**

以下全部把 `font-weight: 700;` 或 `font-weight: 600;` 改成 `font-weight: 500;`：第 183、206、219、244、277、302、321 行。

- [ ] **Step 3: 圓角清理**

第 201、352、370 行 `border-radius: 8px;` → `border-radius: var(--radius-sm);`
第 231 行 `border-radius: 6px;` → `border-radius: var(--radius-sm);`

- [ ] **Step 4: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/nodePanel/ComputeCiPanel.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/ComputeCiPanel.vue
git commit -m "style(workflow): apply design tokens to ComputeCiPanel"
```

---

## Task 19: `WorkflowFileUploadPanel.vue` 死代碼刪除 + 按鈕遷移 + 清理

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/WorkflowFileUploadPanel.vue`

**Interfaces:**
- Consumes：`components/ui/AppButton.vue`

- [ ] **Step 1: import AppButton**

在 `<script setup>` 裡加：

```ts
  import AppButton from '@/components/ui/AppButton.vue'
```

- [ ] **Step 2: 「瀏覽檔案」按鈕遷移**

找到：

```html
      <button class="upload-modal-button" type="button" @click="browseFile">
        瀏覽檔案
      </button>
```

換成：

```html
      <AppButton variant="primary" @click="browseFile">
        瀏覽檔案
      </AppButton>
```

- [ ] **Step 3: 刪除 `.upload-modal-button` CSS**

刪除：

```css
  .upload-modal-button {
    border: none;
    border-radius: 999px;
    padding: 10px 22px;
    background: var(--color-accent);
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }
```

- [ ] **Step 4: 刪除死代碼區塊一：`.upload-card`/`.upload-card__desc`**

找到並整段刪除（位於 `.workflow-file-upload-panel { ... }` 之後、`.upload-modal-dropzone { ... }` 之前）：

```css
  .upload-card {
    padding: 18px;
    border: 1px dashed color-mix(in oklab, var(--color-accent) 28%, transparent);
    border-radius: 16px;
    background: color-mix(in oklab, var(--color-accent) 4%, transparent);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .upload-card__desc {
    margin: 0;
    color: var(--color-secondary);
    font-size: 13px;
    line-height: 1.5;
  }
```

（這兩個 class 在 template 裡查無引用，是舊版遺留。）

- [ ] **Step 5: 刪除死代碼區塊二：`.upload-modal-preview` 到 `.upload-modal-preview-table th`**

找到並整段刪除（從 `.upload-modal-preview {` 開始，到 `.upload-modal-preview-table th { ... }` 結束，位於 `.upload-modal-error { ... }` 之後、下一個 `.workflow-file-upload-panel { ... }`（`@media` 覆寫）之前）：

```css
  .upload-modal-preview {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .upload-modal-preview-header {
    font-size: 16px;
    font-weight: 700;
    color: var(--color-text);
  }

  .upload-modal-preview-summary {
    display: flex;
    gap: 16px;
    color: var(--color-secondary);
    font-size: 13px;
  }

  .upload-modal-chart-grid {
    display: flex;
    gap: 16px;
    overflow-x: auto;
    padding-bottom: 8px;
    scroll-snap-type: x proximity;
  }

  .upload-modal-chart-grid::-webkit-scrollbar {
    height: 10px;
  }

  .upload-modal-chart-grid::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.7);
    border-radius: 999px;
  }

  .upload-modal-chart-card {
    flex: 0 0 320px;
    min-width: 320px;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 18px;
    padding: 16px;
    background: var(--color-surface);
    scroll-snap-align: start;
  }

  .upload-modal-chart-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
    color: var(--color-text);
  }

  .upload-modal-chart-subtitle {
    margin-top: 6px;
    color: var(--color-secondary);
    font-size: 12px;
  }

  .upload-modal-chart-meta {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: var(--color-secondary);
    font-size: 12px;
    margin-bottom: 14px;
  }

  .upload-modal-chart-bars {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .upload-modal-chart-bar-row {
    display: grid;
    grid-template-columns: minmax(75px, 1.4fr) 1fr auto;
    gap: 10px;
    align-items: center;
  }

  .upload-modal-chart-bar-label {
    font-size: 12px;
    color: var(--color-text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .upload-modal-chart-bar-track {
    height: 10px;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .upload-modal-chart-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: var(--color-accent);
  }

  .upload-modal-chart-bar-value {
    font-size: 12px;
    color: var(--color-text);
    text-align: right;
  }

  .upload-modal-preview-table {
    max-height: 220px;
    overflow: auto;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 14px;
    background: var(--color-surface);
    color: var(--color-text);
  }

  .upload-modal-preview-table table {
    width: 100%;
    min-width: max-content;
    border-collapse: collapse;
  }

  .upload-modal-preview-table th,
  .upload-modal-preview-table td {
    padding: 10px 12px;
    border-bottom: 1px solid rgba(226, 232, 240, 0.9);
    text-align: left;
    font-size: 13px;
    white-space: nowrap;
    color: var(--color-text);
  }

  .upload-modal-preview-table th {
    background: var(--color-surface);
    color: var(--color-text);
  }
```

（同樣是 template 裡查無引用的整組預覽圖表樣式。）

- [ ] **Step 6: 剩餘清理**

- `.upload-modal-dropzone` 的 `border-radius: 18px;`（第 128 行左右）→ `border-radius: var(--radius-lg);`
- `.upload-modal-dropzone` 的 `transition: border-color 0.2s ease, background 0.2s ease;` → `transition: border-color var(--dur-base) ease, background var(--dur-base) ease;`
- `.upload-modal-line1` 的 `font-weight: 700;` → `font-weight: 500;`
- `.upload-modal-error` 的 `color: #ef4444;` → `color: var(--color-error);`

- [ ] **Step 7: 跑檢查**

Run（在 `frontend/` 目錄下）:
```bash
npx eslint src/components/workflow/nodePanel/WorkflowFileUploadPanel.vue
npm run build
```
Expected: 兩個都 PASS

- [ ] **Step 8: 手動在瀏覽器確認**

打開 File 節點面板，拖拉/瀏覽上傳 CSV 檔案，確認拖曳區、瀏覽按鈕、錯誤訊息（若上傳失敗）都正常顯示。

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/WorkflowFileUploadPanel.vue
git commit -m "refactor(workflow): remove dead preview styles, migrate browse button"
```

---

## 最終檢查

19 個 task 都完成後：

- [ ] 在 `frontend/` 目錄下跑一次全域 `npx eslint src/components/workflow src/views/WorkflowPage.vue src/views/StyleGuideView.vue src/types/workflow.ts src/constants/workflowData.ts src/composables/workflow src/plugins/vuetify.ts` 與 `npm run build`，兩個都要 PASS
- [ ] 手動跑一次完整流程：上傳論文或用 demo 資料 → 產生節點 → 逐一點開每個節點面板 → 執行 workflow → 確認節點進行中顯示 spinner、完成後右下角出現綠色勾勾徽章、五種節點分類色彼此可辨識
- [ ] 確認 `/style-guide` 頁面（dev 模式）的節點分類色展示區塊正確顯示新色票 + 邊框 + 徽章
