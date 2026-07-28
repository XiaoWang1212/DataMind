# 節點選取狀態與增刪閃色 設計

日期：2026-07-14
範圍：`frontend/src/types/workflow.ts`、`frontend/src/composables/workflow/useWorkflowNodes.ts`、`frontend/src/components/workflow/IconNode.vue`

要解決的兩個問題：

- **無法辨識目前點在哪個節點的 panel**
- **增刪節點時閃的綠色很醜**

兩題都落在畫布節點的視覺回饋上，改動集中在同幾個檔案，一起做只需走一次驗證。

> **實作階段的修正（2026-07-14）**：選取狀態的視覺表達與原設計完全不同，下方「改動 2」已改寫成實際落地的版本。原設計是**圓形外的淡藍細環**（`box-shadow` 三層：畫布色間隙 + `#a8c6ff` 環 + 柔投影）。實作時在瀏覽器上一一試過外環、往上浮起（`translateY` + 同色相投影），全部都不好看，根因是：
>
> 1. **圓形的填色這個「頻道」已經被狀態佔用了**（灰＝未跑／黃＝已完成）。任何加在圓形上的選取指示——環、投影、浮起——都會跟正在表達狀態的那個顏色打架。這不是色碼沒調好，是頻道衝突。
> 2. 解法是把選取移到**沒被佔用的頻道**：標籤。`ui-ux-pro-max` 的 UX 準則也指向同一個做法（Active State：`text-primary border-b-2`）。
> 3. 底線的顏色若用固定色（淡藍 `#9cc0ff`、飽和主色 `#005dff`）仍會跟黃色節點較勁；用中性墨色 `#242424` 則因為跟標籤同色而不夠顯眼。最後採用**跟著節點自己的色相走**（`--node-accent`）：灰節點灰藍線、黃節點金色線——線與正上方的圓同色相，永遠不會不搭。
> 4. 加了 `scaleX` 從中央長出的 200ms 進場動畫（`prefers-reduced-motion` 會停用）。
>
> **另外查證到的事實**：畫布上的節點**永遠不會是藍色**。`INITIAL_NODES`（`workflowData.ts`）七顆全是 `node-pending`，動態生成的 `model-*` / preprocessor / featureEngineering / computeCi 也一律 `node-pending`，唯一的顏色轉換是 `useWorkflowNodes.ts:67` 的 `finished → node-yellow`。`node-purple`（藍漸層）只出現在 `components/WorkflowBuilder.vue`，而那是**死檔案**（全前端零 import）。所以實際只有灰、黃兩種底色；`LABEL_ACCENTS` 裡的 `node-purple` 那一條只是 fallback。

## 背景

### 畫布上沒有「選取中」的視覺回饋

點節點會開啟 drawer 顯示該節點的 panel，但**畫布這一側完全沒有回饋**——被點到的節點看起來跟其他節點一模一樣。切幾個節點之後就分不清目前這個 panel 是誰的。

Panel 那一側其實已經有身分資訊了：`WorkflowOptionsPanel.vue:7-10` 的 `.panel-header` 會顯示 `selectedNode.data.label` 與 `description`。所以缺的純粹是畫布端的對應，**不需要動 panel**。

`IconNode.vue` 目前只讀三種視覺狀態：

- `colorClass`：`node-pending`（灰 `#ced3e9`）／`node-purple`（藍漸層 `#005dff`→`#4c8cff`）／`node-yellow`（已完成 `#f0e274`）
- `highlighted`：Settings 步驟的黃色脈動外框（`.node-highlighted`）
- `flashType`：增刪時的閃色疊層（`.flash-add` / `.flash-remove`）

沒有任何一項代表「使用者現在點在這顆」。

**Vue Flow 的 `props.selected` 用不了**：`WorkflowCanvas.vue:19` 設了 `:elements-selectable="false"`，所以 Vue Flow 內建的選取狀態永遠是 `false`；`useWorkflowNodes.ts:63` 又把每個節點的 `class` 硬設成 `''`。這個 app 真正的選取事實來源是 `WorkflowWorkspace.vue:147` 的 `selectedNodeId`，而它**已經被傳進 `useWorkflowNodes()`**（第 16 行參數），目前只用來算步驟高亮。

### 綠色閃光跟藍色系不搭

`IconNode.vue:100-106`：

```css
.flash-add::before    { background: #10b981; }   /* 綠 */
.flash-remove::before { background: #ef4444; }   /* 紅 */
```

`flash-overlay` 動畫讓整顆節點被顏色蓋滿、閃兩下（1.2s）。綠色 `#10b981` 跟整體藍色系（`#005dff`）突兀。

閃色的觸發點在 `WorkflowWorkspace.vue`：新增模型（307 行）、刪除模型（318 行）、preprocessor / featureEngineering 節點增刪（370、379 行）。這些節點在閃的當下幾乎都是 `node-pending` 灰底，所以閃色只要在灰底上讀得出來即可。

## 改動 1：`canvasNodes` 傳出 `isSelected`

`useWorkflowNodes.ts:55-74`，在組 `data` 的地方多一個旗標：

```diff
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
+          isSelected: node.id === selectedNodeId.value,
           flashType: nodeFlash.value.get(node.id) ?? null,
         },
       }
     })
   })
```

**為什麼不開 Vue Flow 的 `elements-selectable`**：那會引入 Vue Flow 自己的 `.selected` 預設樣式與框選行為，而且 `class: ''`（63 行）本來就會把它加的 class 洗掉。`selectedNodeId` 已經是這個 app 唯一的選取來源（drawer 開關、localStorage 還原都靠它），再開一套等於同一份狀態存兩份。

## 改動 2：`IconNode.vue` 用「標籤底線」表示選取

`NodeData`（`types/workflow.ts`）先宣告新欄位，比照既有的 `status?`（既有的 `highlighted` / `flashType` 都是沒宣告就硬注入 `data`，靠 TS 推論漏過去；新欄位不跟進這個習慣）：

```ts
/** 是否為目前點選中的節點，由 canvasNodes computed 依 selectedNodeId 動態註入 */
isSelected?: boolean;
```

`IconNode.vue` 讀出旗標，並把底線的顏色依 `colorClass` 映射成 CSS 變數：

```ts
// 用 data.isSelected 而非 Vue Flow 的 props.selected：
// WorkflowCanvas 設了 elements-selectable="false"，內建的 selected 永遠是 false
const isSelected = computed(() => Boolean(props.data?.isSelected))

// 選取指示線的顏色，對應各 colorClass 的底色（壓深過，淺色在近白的畫布上看不見）
const LABEL_ACCENTS: Record<string, string> = {
  'node-pending': '#7c88a8',
  'node-purple': '#005dff',
  'node-yellow': '#c2a935',
}
const accentColor = computed(() => LABEL_ACCENTS[colorClass.value] ?? '#005dff')
```

`--node-accent` 掛在 wrapper 上——底線在標籤上、`colorClass` 在圓形上，兩者是兄弟節點，CSS 沒辦法直接跨過去取值：

```diff
   <div
     class="icon-node-wrap"
-    :style="highlightColor ? { '--highlight-color': highlightColor } : {}"
+    :style="{
+      '--node-accent': accentColor,
+      ...(highlightColor ? { '--highlight-color': highlightColor } : {}),
+    }"
   >
```

標籤包一層 `<span>`，class 掛在 span 上：

```diff
-    <div class="icon-node-label">{{ label }}</div>
+    <div class="icon-node-label">
+      <span :class="{ 'label-selected': isSelected }">{{ label }}</span>
+    </div>
```

樣式：

```css
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
  background: var(--node-accent, #005dff);
  animation: underline-in 0.2s ease-out;
}

@keyframes underline-in {
  from { transform: translateX(-50%) scaleX(0); opacity: 0; }
  to   { transform: translateX(-50%) scaleX(1); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .label-selected::after { animation: none; }
}
```

**設計決策**：

- **選取畫在標籤上，圓形完全不碰**。圓形的填色已經在表達「狀態」（灰＝未跑／黃＝已完成），再把「選取」也塞進同一個頻道就一定會打架——外環、投影、浮起都試過，全部都怪。標籤是空著的頻道。
- **底線顏色跟著節點自己的色相走**。固定色（不論淡藍或飽和主色）都會跟黃色節點較勁；中性墨色又因為跟標籤同色而不夠顯眼。跟著走則永遠協調，代價是「選取」少一個固定識別色——可接受，因為畫面上同時只會有一顆被選取。
- **色碼要壓深**：`#c2a935` 不是節點的 `#f0e274`。原色在近白的畫布（`#f8fbff`）上根本看不見。
- **動畫用 `scaleX` 不用 `width`**：只動 transform/opacity，不觸發 layout；200ms 落在微互動的 150–300ms 區間；`prefers-reduced-motion` 會停用。

**跟現有效果的關係**：底線畫在標籤上，`.node-highlighted`（Settings 步驟的黃色脈動框，`box-shadow`）和閃色（`::before` 疊層，被 `.icon-node` 的 `overflow: hidden` 裁在圓形內）都畫在圓形上，三者位置互不重疊，可以同時出現。

## 改動 3：閃色換色

`IconNode.vue:100-106`：

```diff
   .flash-add::before {
-    background: #10b981;
+    background: #06b6d4;
   }

   .flash-remove::before {
     background: #ef4444;
   }
```

- **新增改成青色 `#06b6d4`**：靠藍的色相，跟整體藍色系協調；同時仍與主色 `#005dff` 有足夠區別，不會讓「剛加進來」看起來像「這是預設節點」。
- **刪除的紅 `#ef4444` 不動**：紅色是刪除的通用視覺語言，換掉反而降低可讀性。

動畫時序（`flash-overlay` keyframes）、opacity、以及 `WorkflowWorkspace.vue` 的 `flashNode()` 觸發邏輯**完全不動**。

## 驗收

開 dev server（`npm run dev`）：

1. **選取底線**：依序點 File / Data Table / Settings / Test & Score 各節點 → 被點到的那顆標籤下方長出一條線（從中央往兩側展開），切到下一顆時前一顆的線消失。
2. **線的長度與位置一致**：單行標籤（File）與兩行標籤（Data Table）的線一樣長（34px）、離文字一樣遠（8px）。
3. **取消選取**：點畫布空白處（`@pane-click`）→ drawer 關閉、線一併消失。
4. **顏色跟著節點走**：灰底節點（未跑）是灰藍線 `#7c88a8`；跑完變黃底後是金色線 `#c2a935`。
5. **跟黃色脈動框並存**：選 Settings、切到步驟 ①～④ → Settings 的底線與被引導節點的黃色脈動框同時在畫面上，位置不重疊、不互相干擾。
6. **閃色**：Settings ③ 加一個模型 → 新的 model 節點閃**青色**兩下；刪掉一個模型 → 閃紅色兩下。在 ①／② 增刪前處理/特徵工程步驟導致 preprocessor / featureEngineering 節點增刪時同理。
7. **重新整理後**：`selectedNodeId` 由 localStorage 還原（`WorkflowWorkspace.vue:487`），重整後仍選在同一顆節點上，線也還在。
8. `npm run build` 通過，改動過的檔案沒有新增 lint 錯誤（`npm run lint` 在本專案 baseline 就是紅的，不能拿它當閘門）。
