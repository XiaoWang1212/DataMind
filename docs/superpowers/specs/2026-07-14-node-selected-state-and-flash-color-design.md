# 節點選取狀態與增刪閃色 設計

日期：2026-07-14
範圍：`frontend/src/composables/workflow/useWorkflowNodes.ts`、`frontend/src/components/workflow/IconNode.vue`

對應 `.claude/ux-issues.md`：

- 問題 **#4**「無法辨識目前點在哪個節點的 panel」
- 問題 **#8**「現在的綠色 highlight 很醜」

兩題都落在畫布節點的視覺回饋上，改動集中在同兩個檔案，一起做只需走一次驗證。

## 背景

### #4：畫布上沒有「選取中」的視覺回饋

點節點會開啟 drawer 顯示該節點的 panel，但**畫布這一側完全沒有回饋**——被點到的節點看起來跟其他節點一模一樣。切幾個節點之後就分不清目前這個 panel 是誰的。

Panel 那一側其實已經有身分資訊了：`WorkflowOptionsPanel.vue:7-10` 的 `.panel-header` 會顯示 `selectedNode.data.label` 與 `description`。所以缺的純粹是畫布端的對應，**不需要動 panel**。

`IconNode.vue` 目前只讀三種視覺狀態：

- `colorClass`：`node-pending`（灰 `#ced3e9`）／`node-purple`（藍漸層 `#005dff`→`#4c8cff`）／`node-yellow`（已完成 `#f0e274`）
- `highlighted`：Settings 步驟的黃色脈動外框（`.node-highlighted`）
- `flashType`：增刪時的閃色疊層（`.flash-add` / `.flash-remove`）

沒有任何一項代表「使用者現在點在這顆」。

**Vue Flow 的 `props.selected` 用不了**：`WorkflowCanvas.vue:19` 設了 `:elements-selectable="false"`，所以 Vue Flow 內建的選取狀態永遠是 `false`；`useWorkflowNodes.ts:63` 又把每個節點的 `class` 硬設成 `''`。這個 app 真正的選取事實來源是 `WorkflowWorkspace.vue:147` 的 `selectedNodeId`，而它**已經被傳進 `useWorkflowNodes()`**（第 16 行參數），目前只用來算步驟高亮。

### #8：綠色閃光跟藍色系不搭

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

## 改動 2：`IconNode.vue` 套用選取樣式

讀出旗標：

```ts
// 目前點選中的節點（來自 selectedNodeId，非 Vue Flow 內建的 selected）
const isSelected = computed(() => Boolean(props.data?.isSelected))
```

掛上 class（`IconNode.vue:23`）：

```diff
-      :class="[colorClass, { 'node-highlighted': highlighted, 'flash-add': flashType === 'add', 'flash-remove': flashType === 'remove' }]"
+      :class="[colorClass, { 'node-selected': isSelected, 'node-highlighted': highlighted, 'flash-add': flashType === 'add', 'flash-remove': flashType === 'remove' }]"
```

樣式：

```css
.node-selected {
  box-shadow:
    0 0 0 3px #f8fbff,                 /* 間隙：與畫布底色同色 */
    0 0 0 5px #a8c6ff,                 /* 淡藍細環 */
    0 4px 10px rgba(15, 23, 42, 0.12); /* 柔投影 */
}
```

**設計決策**：

- **只有外環，標籤不變色**。節點跑完會變黃底（`node-yellow`），若再把標籤染藍，畫面上同一顆節點就有三個顏色在打架。
- **淡藍 `#a8c6ff`** 是主色 `#005dff` 的淡版——保留品牌感，但不會強到跟「藍＝預設狀態、黃＝已完成」的狀態語意混淆。
- **間隙用 `#f8fbff` 而非白色**：畫布底色是 `#f8fbff` + 淡藍點陣（`WorkflowCanvas.vue:214-219`）。用純白會在節點外圈出現一條比背景亮的白邊；用同色才讀得像「空隙」。
- **靜態、不脈動**。`.node-highlighted` 是會脈動的黃框，選取環在「會不會動」這一項上就先跟它分開了。

**跟現有效果的關係**：

- `.node-highlighted` 也用 `box-shadow`，但**兩者不會落在同一顆節點上**：`getHighlightedIds()`（45-53 行）只在 `selectedNodeId === 'settings'` 時發出高亮，且對象是**其他**節點（preprocessor / featureEngineering / `model-*` / computeCi）。被選取的那顆（settings）自己永遠不在高亮集合裡。
- 閃色是 `::before` 疊層（`.icon-node` 有 `overflow: hidden`，疊層被裁在圓形內），`box-shadow` 畫在圓形外，兩者不互相覆蓋。

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

1. **選取環**：依序點 File / Data Table / Settings / Test & Score 各節點 → 被點到的那顆出現淡藍細環＋淺投影，切到下一顆時前一顆的環消失。
2. **取消選取**：點畫布空白處（`@pane-click`）→ drawer 關閉、環一併消失。
3. **跟黃色脈動框並存**：選 Settings、切到步驟 ①～④ → 畫面上同時有「Settings 的靜態淡藍環」與「被引導節點的黃色脈動框」，兩者一眼分得出來、不會誤認。
4. **黃底節點上仍可讀**：跑完流程（節點變 `node-yellow`）後點 Test & Score → 選取環在黃底上仍清楚。
5. **閃色**：Settings ③ 加一個模型 → 新的 model 節點閃**青色**兩下；刪掉一個模型 → 閃紅色兩下。在 ①／② 增刪前處理/特徵工程步驟導致 preprocessor / featureEngineering 節點增刪時同理。
6. **重新整理後**：`selectedNodeId` 由 localStorage 還原（`WorkflowWorkspace.vue:487`），重整後仍選在同一顆節點上，環也還在。
7. `npm run build` 通過，改動過的檔案沒有新增 lint 錯誤（`npm run lint` 在本專案 baseline 就是紅的，不能拿它當閘門）。

## 收尾要回填的文件

實作完成後更新 `.claude/ux-issues.md`：

- 問題 **#4** 勾選為已修，註明做法是從 `selectedNodeId` 算 `isSelected` 傳進 `data`（沒有開啟 Vue Flow 的 `elements-selectable`），畫布端補上淡藍靜態外環。
- 問題 **#8** 勾選為已修，註明綠 `#10b981` → 青 `#06b6d4`，刪除紅不動。
- 第 76 行的「現況」統計（已解決 6 項／未解決 6 項）同步更新。
