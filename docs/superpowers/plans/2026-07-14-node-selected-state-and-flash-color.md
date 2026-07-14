# 節點選取狀態與增刪閃色 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 畫布上被點選的節點加上淡藍靜態外環，並把增刪節點的綠色閃光換成青色。

**Architecture:** 兩個改動都只動畫布節點的視覺層。選取外環從既有的 `selectedNodeId`（`WorkflowWorkspace.vue` 的 ref，已經傳進 `useWorkflowNodes()`）在 `canvasNodes` computed 裡算出 `isSelected` 旗標，塞進節點的 `data`，由 `IconNode.vue` 套一條 CSS class——**不開啟 Vue Flow 的 `elements-selectable`**，避免同一份選取狀態存兩套。閃色純粹是換一個色碼，動畫時序與觸發邏輯完全不動。

**Tech Stack:** Vue 3 `<script setup lang="ts">` SFC、`@vue-flow/core`、scoped CSS。無新增套件。

## Global Constraints

- 本專案前端未設置任何自動化測試框架（無 vitest/jest，`package.json` 沒有 `test` script）。依 `CLAUDE.md` 的慣例，改動以「啟動 `npm run dev`、在瀏覽器手動操作驗證」取代自動化測試步驟；**若執行者無法完成手動驗證，必須明確說明「無法測試 UI」，不能逕自宣稱驗證通過**。
- **Commit 前必須先取得使用者明確同意**：完成實作、跑完 `npm run build`、並列出手動驗證步驟後，必須停下來明確詢問使用者，取得明確答覆後才能執行 `git add` / `git commit`。即使透過 `superpowers:subagent-driven-development` 執行，也要覆蓋掉 implementer 預設會自動 commit 的行為。
- Commit 訊息**一行就好**，不加 `Co-Authored-By` trailer。
- **不要修改 `WorkflowCanvas.vue:19` 的 `:elements-selectable="false"`**，也不要動 `useWorkflowNodes.ts:63` 的 `class: ''`。選取狀態一律走 `selectedNodeId` → `data.isSelected` 這條路。
- 精確色碼（**逐字照抄，不要自行微調**）：
  - 選取外環：`box-shadow: 0 0 0 3px #f8fbff, 0 0 0 5px #a8c6ff, 0 4px 10px rgba(15, 23, 42, 0.12);`
    - `#f8fbff` 是**畫布底色**（`WorkflowCanvas.vue:214`），當作環的內側間隙——不可改成純白 `#fff`，那會在節點外圈出現一條比背景亮的白邊。
  - 新增閃色：`#06b6d4`（原 `#10b981` 綠）
  - 刪除閃色：`#ef4444`（**不動**）
- 選取狀態**只加外環**：標籤（`.icon-node-label`）不變色、節點不放大、不脈動。理由：節點跑完會變黃底（`node-yellow`），再染標籤會讓同一顆節點有三個顏色在打架。
- Spec 來源：`docs/superpowers/specs/2026-07-14-node-selected-state-and-flash-color-design.md`

---

## File Structure

| 檔案 | 職責 | 本次改動 |
|---|---|---|
| `frontend/src/types/workflow.ts` | 前端 workflow 的共用型別（`NodeData` / `FlowNode` / `EdgeBase`…） | `NodeData` 新增 `isSelected?: boolean`，比照既有的 `status?` |
| `frontend/src/composables/workflow/useWorkflowNodes.ts` | 節點/邊的狀態與 computed（`canvasNodes` / `canvasEdges`），以及節點增刪同步 | `canvasNodes` 的 `data` 多注入 `isSelected` |
| `frontend/src/components/workflow/IconNode.vue` | 單一節點的視覺呈現（圓形 icon、label、spinner、外框、閃色） | 讀出 `isSelected` 並套 `.node-selected`；`.flash-add` 換色 |

三個檔案都已存在，不新增檔案。

**注意**：spec 的「範圍」只寫了 `useWorkflowNodes.ts` 與 `IconNode.vue` 兩個檔案。這裡多加 `types/workflow.ts` 是刻意的——`NodeData` 是嚴格 interface，既有的 `highlighted` / `highlightColor` / `flashType` 都是未宣告就硬注入 `data`（靠 TS 推論漏過去），`status?` 則有明確宣告。新欄位跟著 `status?` 的做法走，型別自我說明、也不依賴推論的僥倖。

---

## Task 1: 選取中的節點加上淡藍外環

**Files:**
- Modify: `frontend/src/types/workflow.ts:18-27`（`NodeData` interface）
- Modify: `frontend/src/composables/workflow/useWorkflowNodes.ts:55-74`（`canvasNodes` computed）
- Modify: `frontend/src/components/workflow/IconNode.vue:23`（class binding）、`:53-61`（script）、`:119`（style，插在 `.node-highlighted` 之前）

**Interfaces:**
- Consumes: `selectedNodeId: Ref<string | null>`——`useWorkflowNodes()` 的第 3 個參數（`useWorkflowNodes.ts:16`），**已經存在、已經被傳進來**（`WorkflowWorkspace.vue:185`），目前只被 `getHighlightedIds()` 用來判斷是否為 `'settings'`。本任務不改它的來源或型別。
- Produces: `NodeData.isSelected?: boolean`——由 `canvasNodes` 動態注入，`IconNode.vue` 消費。這是 `data` 上第 4 個「computed 注入、非持久化」的欄位（前三個是 `status` / `highlighted` + `highlightColor` / `flashType`）。**不會被寫進 localStorage**：`useWorkflowStorage` 序列化的是 `nodes`（原始 ref），不是 `canvasNodes`（computed 產物）。

- [ ] **Step 1: `NodeData` 宣告 `isSelected`**

把（`types/workflow.ts:18-27`）：

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
}
```

改成（尾端新增一個 optional 欄位）：

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

- [ ] **Step 2: `canvasNodes` 注入 `isSelected`**

把（`useWorkflowNodes.ts:55-74`）：

```ts
  const canvasNodes = computed<FlowNode[]>(() => {
    const highlightedIds = getHighlightedIds()
    const color: string | null = STEP_HIGHLIGHT_COLORS[settingsStep.value] ?? null
    return nodes.value.map(node => {
      const status = nodeStatuses.value.get(node.id) ?? null
      const highlighted = highlightedIds.has(node.id)
      return {
        ...node,
        class: '',
        data: {
          ...node.data,
          status,
          colorClass: status === 'finished' ? 'node-yellow' : node.data.colorClass,
          highlighted,
          highlightColor: highlighted ? color : null,
          flashType: nodeFlash.value.get(node.id) ?? null,
        },
      }
    })
  })
```

改成（只多一行 `isSelected`）：

```ts
  const canvasNodes = computed<FlowNode[]>(() => {
    const highlightedIds = getHighlightedIds()
    const color: string | null = STEP_HIGHLIGHT_COLORS[settingsStep.value] ?? null
    return nodes.value.map(node => {
      const status = nodeStatuses.value.get(node.id) ?? null
      const highlighted = highlightedIds.has(node.id)
      return {
        ...node,
        class: '',
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
    })
  })
```

- [ ] **Step 3: `IconNode.vue` 讀出 `isSelected`**

在 `IconNode.vue` 的 `<script setup>` 裡，把（`IconNode.vue:56-58`）：

```ts
  // Settings 步驟高亮外框
  const highlighted = computed(() => Boolean(props.data?.highlighted))
  const highlightColor = computed(() => props.data?.highlightColor as string | null ?? null)
```

改成（在它前面插入 `isSelected`）：

```ts
  // 目前點選中的節點（來自 selectedNodeId，不是 Vue Flow 內建的 selected——
  // WorkflowCanvas 設了 elements-selectable="false"，內建的 props.selected 永遠是 false）
  const isSelected = computed(() => Boolean(props.data?.isSelected))

  // Settings 步驟高亮外框
  const highlighted = computed(() => Boolean(props.data?.highlighted))
  const highlightColor = computed(() => props.data?.highlightColor as string | null ?? null)
```

- [ ] **Step 4: `IconNode.vue` 掛上 class**

把（`IconNode.vue:21-24`）：

```html
    <div
      class="icon-node"
      :class="[colorClass, { 'node-highlighted': highlighted, 'flash-add': flashType === 'add', 'flash-remove': flashType === 'remove' }]"
    >
```

改成（在 `node-highlighted` 前面加上 `node-selected`）：

```html
    <div
      class="icon-node"
      :class="[colorClass, { 'node-selected': isSelected, 'node-highlighted': highlighted, 'flash-add': flashType === 'add', 'flash-remove': flashType === 'remove' }]"
    >
```

- [ ] **Step 5: `IconNode.vue` 新增 `.node-selected` 樣式**

在 `<style scoped>` 裡，把（`IconNode.vue:119-122`）：

```css
  .node-highlighted {
    box-shadow: 0 0 0 4px var(--highlight-color, #005dff);
    animation: highlight-pulse 1.4s ease-in-out infinite;
  }
```

改成（在 `.node-highlighted` **之前**插入新規則。順序有意義：兩條規則都寫 `box-shadow`，`.node-highlighted` 放後面確保它在權重相同時勝出——雖然依 `getHighlightedIds()` 的邏輯兩者不會落在同一顆節點上，但真的撞上時，引導用的脈動框比選取環重要）：

```css
  /* 目前點選中的節點：淡藍靜態外環 + 柔投影。
     #f8fbff 是畫布底色（WorkflowCanvas .flow-area），當作環的內側間隙 */
  .node-selected {
    box-shadow:
      0 0 0 3px #f8fbff,
      0 0 0 5px #a8c6ff,
      0 4px 10px rgba(15, 23, 42, 0.12);
  }

  .node-highlighted {
    box-shadow: 0 0 0 4px var(--highlight-color, #005dff);
    animation: highlight-pulse 1.4s ease-in-out infinite;
  }
```

- [ ] **Step 6: 型別/建置檢查**

Run:

```bash
cd frontend && npm run build
```

Expected: 通過（`vue-tsc` type-check + `vite build` 都不報錯）。這一步只能抓型別與語法錯誤，**不能證明視覺效果正確**，下一步一定要接著手動驗證。

- [ ] **Step 7: 手動驗證（需要瀏覽器操作；無法操作瀏覽器時必須明確說明「無法測試 UI」，不可宣稱驗證通過）**

執行（若尚未啟動）：

```bash
cd frontend && npm run dev
```

在瀏覽器開 `http://localhost:3000/workflow`，上傳一份 CSV 並匯入/建立一個有模型的流程，確認：

1. **選取環**：依序點 File / Data Table / Distribution / Settings / Test & Score → 被點到的那顆出現淡藍細環＋淺投影，切到下一顆時**前一顆的環消失**（同時只有一顆有環）。
2. **環的間隙不是白邊**：湊近看選取的節點，環與圓形之間那圈是畫布底色（帶點陣的淡藍白），**不是**一條比背景亮的白邊。
3. **取消選取**：點畫布空白處 → drawer 關閉、環一併消失。
4. **跟黃色脈動框並存**：點 Settings 節點、在面板裡切到步驟 ①→④ → 畫面上同時有「Settings 的靜態淡藍環」與「被引導節點（Preprocessor / Feature Engineering / Model / Compute CI）的黃色脈動框」，兩者一眼分得出來、不會誤認為同一種狀態。
5. **黃底節點上仍可讀**：把流程跑完（節點變黃底 `node-yellow`）後點 Test & Score → 選取環在黃底上仍清楚可見。
6. **重新整理後**：`selectedNodeId` 會由 localStorage 還原（`WorkflowWorkspace.vue:487`）。重整頁面後仍選在同一顆節點上，環也還在。

- [ ] **Step 8: 停下來，等待使用者確認**

不要執行下一步的 `git add` / `git commit`。明確詢問使用者：「`npm run build` 已通過，麻煩實際在瀏覽器測過上述 6 項（尤其是『選取環 vs 黃色脈動框』同時出現時分不分得出來、以及黃底節點上的可讀性），確認沒問題後再讓我 commit。」等待使用者明確回覆「可以」或指出問題，才能進到下一步。

- [ ] **Step 9: Commit（僅在使用者確認沒問題後執行）**

```bash
git add frontend/src/types/workflow.ts frontend/src/composables/workflow/useWorkflowNodes.ts frontend/src/components/workflow/IconNode.vue
git commit -m "feat: add selected ring to canvas nodes"
```

---

## Task 2: 增刪閃色由綠改青

**Files:**
- Modify: `frontend/src/components/workflow/IconNode.vue:100-102`（`.flash-add::before`）

**Interfaces:**
- Consumes: 無。`flashType`（`IconNode.vue:61`）與 `WorkflowWorkspace.vue` 的 `flashNode()`（151 行）both 既有，本任務不碰。
- Produces: 無新的函式/型別/props/emits。純 CSS 色碼替換。

- [ ] **Step 1: 換掉 `.flash-add` 的背景色**

把（`IconNode.vue:100-102`）：

```css
  .flash-add::before {
    background: #10b981;
  }
```

改成：

```css
  .flash-add::before {
    background: #06b6d4;
  }
```

**不要動** `.flash-remove::before` 的 `#ef4444`（紅色是刪除的通用視覺語言），也不要動 `flash-overlay` keyframes（`IconNode.vue:108-117`）的時序與 opacity、或 `WorkflowWorkspace.vue` 的 `flashNode()` 觸發邏輯。

- [ ] **Step 2: 型別/建置檢查**

Run:

```bash
cd frontend && npm run build
```

Expected: 通過。

- [ ] **Step 3: 手動驗證（需要瀏覽器操作；無法操作瀏覽器時必須明確說明「無法測試 UI」，不可宣稱驗證通過）**

在瀏覽器開 `http://localhost:3000/workflow`（dev server 若未啟動，先 `cd frontend && npm run dev`），確認：

1. **新增模型**：點 Settings 節點 → 面板切到「③ 模型」→ 加一個模型 → 畫布上新出現的 model 節點**閃青色**（`#06b6d4`）兩下，不再是綠色。
2. **刪除模型**：移除一個模型 → 該節點**閃紅色**兩下（跟改動前一樣）。
3. **前處理 / 特徵工程節點**：在「① 前處理」加/刪步驟導致 Preprocessor 節點出現/消失時，同樣是新增閃青、刪除閃紅。
4. **閃色跟選取環不打架**：Task 1 做完後，Settings 是選取中的節點（有淡藍環），此時新增模型 → 新節點閃青色、Settings 的環仍在，兩者互不干擾（閃色是圓形內的疊層，環在圓形外）。

- [ ] **Step 4: 停下來，等待使用者確認**

不要執行下一步的 `git add` / `git commit`。明確詢問使用者：「閃色已改成青色，`npm run build` 通過。麻煩在瀏覽器加/刪一個模型看一下閃色，確認沒問題後再讓我 commit。」等待使用者明確回覆。

- [ ] **Step 5: Commit（僅在使用者確認沒問題後執行）**

```bash
git add frontend/src/components/workflow/IconNode.vue
git commit -m "style: change node add flash from green to cyan"
```
