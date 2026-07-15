# Data Table 面板：副標文案、欄位設定即時同步、留白收緊 設計

日期：2026-07-13
範圍：`frontend/src/constants/workflowData.ts`、`frontend/src/components/workflow/nodePanel/DataTablePanel.vue`

本次要修的三件事：

- 副標文案「上傳資料預覽」名不符實，要改一下。
- Role/Target 選擇在按「繼續」前會遺失。
- Data Table Panel 的 padding/margin 感覺偏多，整體偏空。

三件事互相獨立，但都落在同一個檔案、同一個畫面，一起做可以只走一次驗證。

> **實作階段的修正（2026-07-13）**：以下四處與原設計不同，下方各節已更新為實際落地的版本。
>
> 1. **「欄位設定」標題改為保留**（原「改動 4」作廢）。原設計要拿掉卡片內的小標，讓 Task 1 的節點副標接手說明職責。使用者在實作途中決定保留它。因為卡片 `padding` 已歸零，標題必須自己帶 `padding: 10px 12px` + `flex-shrink: 0`，否則會黏在卡片邊框上。
> 2. **卡片 padding 歸零帶出一個新的視覺 bug，一併修掉**：`.column-settings-body` 的捲軸槽（macOS 常駐捲軸下約 15px）失去了原本 16px 內縮的遮蔽，露出成右側一條白邊，且灰色 sticky 表頭在那裡斷掉，讀起來像破圖。改成細捲軸（6px、軌道透明、淺灰圓角拇指）。**沒有完全消除**——徹底消除要把 sticky `<thead>` 搬出捲動容器（兩張表的欄寬同步，脆弱），使用者接受 6px 版本。
> 3. **表格改用固定欄寬**（原設計未涵蓋）。表格原本沒有 `table-layout`，欄寬由內容決定——`<input>`/`<select>` 的固有寬度讓前三欄搶走空間，Values 撿剩下的，換一份 CSV 寬度就會跑掉。改成 `table-layout: fixed` + 固定比例 **37 / 26 / 22 / 15**。`.values-cell` 的 `max-width: 300px` 一併移除（固定佈局下欄寬由百分比決定，留著只是兩套機制互相打架；ellipsis 截斷仍靠 `overflow: hidden` + `white-space: nowrap`）。
> 4. **數字格式改用有效位數處理小數**（原設計的 `toFixed(3)` 有 bug）。`toFixed(3)` 會把絕對值小於 0.0005 的數壓成 `0`——一欄值是 `0.0001 / 0.0002 / 0.0003` 的資料會顯示成 `0 – 0`，看起來像「這欄沒有變異」，是**會說謊的顯示**。改成：絕對值小於 1 時用 `toPrecision(3)`，否則維持 `toFixed(3)`。

## 背景

### 副標文案名不符實

`workflowData.ts:31` 把 `dataTable` 節點的 `description` 寫成「上傳資料預覽」。這行字會由 `WorkflowOptionsPanel.vue` 的 `.panel-header p` 顯示在面板標題底下。但這個面板裡**沒有任何資料列預覽**——它從頭到尾只有一張「欄位設定」表（Column Name / Type / Role / Values），使用者在這裡做的事是設定欄位型別與指定目標變數。文案與實際功能不符。

本次**不**補資料列預覽功能，節點名稱 `Data Table` 也不動，只改副標文案。

### Role/Target 選擇會遺失

`DataTablePanel.vue` 的 `columnSettings`（Column Name / Type / Role 的可編輯狀態）只存在元件本地。唯一把它同步回父層的路徑是 `applyColumnSettings()`（314-318 行），而那只在使用者按下「繼續」時才會被呼叫：

```ts
function applyColumnSettings (): void {
  emitColumnConfig()          // ← 只有這裡會 emit
  originalColumnSettings.value = cloneSettings(columnSettings.value)
  emit('apply-column-config')
}
```

`WorkflowOptionsPanel.vue` 的 template 是用 `v-if="selectedNode.id === 'dataTable'"` 掛載這個面板（13-22 行），所以切到別的節點時元件會被**卸載**，本地的 `columnSettings` 隨之銷毀。切回來時重新掛載、重跑 `loadFile()` → `buildColumnSettings()`，只能從 `props.columnConfig` 還原——但那份 config 從未被寫入過，於是 Role 全部回到預設的 `feature`，Target 消失。

父層的鏈路其實是完好的：`WorkflowOptionsPanel.handleColumnConfigChange()`（322-329 行）收到 `update-column-config` 後就會往上 `emit('update-config')`，`WorkflowWorkspace.handleUpdateConfig()` 再寫進 `node.data.config.columnConfig`，那是跨節點切換仍然存活的持久層。問題純粹是**這條鏈從來沒被觸發過**，不是鏈斷了。

還有第二條會導致同樣症狀的路徑：`buildColumnSettings()`（269-293 行）是用**欄位名稱**去比對已存的 config：

```ts
const existingMap = new Map((props.columnConfig ?? []).map(c => [c.name, c]))
// ...
const existing = existingMap.get(header)   // header 來自 CSV 表頭
```

但 Column Name 是可編輯的 `<input>`。使用者若把 `died` 改成「是否死亡」並設為 Target，存下來的是 `{ name: "是否死亡", role: "target" }`；切回來時面板從 CSV 讀到的表頭仍是 `died`，拿 `died` 去 map 裡找不到「是否死亡」，該欄被當成沒設定過，名稱與 Role 一起被重置。**只做即時同步、不改對位方式，改過名稱的欄位仍然會被吃掉。**

### #14 留白偏多

單看 CSS 數值不算誇張，實際開瀏覽器比對後發現：「空」的最大來源不是間距數值，而是 **Values 欄整排都是「—」**：`getColumnValueLabel()`（320-330 行）只對 `categorial` 型別回傳內容，其餘型別一律回 `'—'`。一份以數值欄為主的資料集，整張表最右欄會是一長排破折號，視覺上就是一大塊空白。

另外兩個較小的來源：面板標題區已經有「Data Table」大標，卡片裡又有一個「欄位設定」小標（45 行），語意重複且多佔一行；白卡片本身還有 `padding: 14px 16px` 的內縮。

## 改動 1：副標文案

`frontend/src/constants/workflowData.ts:31`，`dataTable` 節點的 `description`：

```diff
       icon: "mdi-table",
       label: "Data\nTable",
       colorClass: "node-pending",
-      description: "上傳資料預覽",
+      description: "設定欄位型別與目標變數",
```

這行字顯示在面板標題區，正好接手「改動 4」要拿掉的那個「欄位設定」小標的說明職責——資訊沒有損失，只是不再重複兩次。

## 改動 2：欄位設定即時同步回父層

### 2a. 對 `columnSettings` 下 deep watch

`DataTablePanel.vue`，新增：

```ts
watch(
  columnSettings,
  () => {
    emitColumnConfig()
  },
  { deep: true },
)
```

一個掛勾覆蓋全部三個可編輯控制項（名稱 `<input>`、Type `<select>`、Role `<select>`），未來表格再加欄位也不必補新的 handler。

**為什麼不會跟 `props.columnConfig` 的 watcher 形成無窮迴圈**：那個 watcher（350-360 行）只在 `!areColumnConfigsEqual(value, columnSettings.value)` 時才呼叫 `buildColumnSettings()`。我們 emit 出去的值經父層寫回 `node.data.config` 再以 prop 回來，內容必然與當下的 `columnSettings` 相等，比對為 true → 不重建 → 迴圈在一輪內收斂。

**採用 deep watch 而非在三個控制項各綁 `@change` 的理由**：後者沒有迴圈疑慮，但要求每個控制項都記得補上，漏掉任何一個就是同一個 bug 再發生一次；而迴圈疑慮已經被既有的相等比對擋掉了。也不採用「把 `columnSettings` 狀態整個上提到父層或 store」——父層已經有 `node.data.config` 這個持久層，再提一次等於同一份狀態存兩份。

**檔案載入時就會 emit 一次自動推斷的預設值**（`buildColumnSettings()` 整個換掉 `columnSettings` → 觸發 deep watch），使用者還沒動手，`node.data.config.columnConfig` 就已經有一份 Role 全為 `feature` 的預設。**這是安全的，不需要加防呆**：能不能往下跑的閘門是 `useWorkflowExecution.ts:49-52` 的 `canRun`，它同時要求 `dataTableApplied.value` 為 true，而 `dataTableApplied` 只在 `WorkflowWorkspace.handleApplyColumnConfig()`（286 行）——也就是按下「繼續」時——才會被設為 true。提早寫入 config 不會讓流程提早變成可執行，只是讓「切走再切回」有東西可以還原。

### 2b. `buildColumnSettings()` 改用索引對位

`DataTablePanel.vue:269-293`：

```diff
-function buildColumnSettings (): void {
-  const existingMap = new Map(
-    (props.columnConfig ?? []).map(config => [config.name, config]),
-  )
-
+function buildColumnSettings (useExisting = true): void {
   columnSettings.value = previewColumns.value.map((header, index) => {
     const columnValues = previewDataRows.value.map(row => row[index] ?? '')
     const availableTypes = getColumnTypeCandidates(columnValues)
-    const existing = existingMap.get(header)
+    const existing = useExisting ? props.columnConfig?.[index] : undefined
     const selectedType
       = existing && availableTypes.includes(existing.type)
         ? existing.type
         : (availableTypes[0] ?? 'text')
     const selectedRole = existing?.role ?? 'feature'

     return {
-      name: header,
+      name: existing?.name ?? header,
       type: selectedType,
       role: selectedRole,
       availableTypes,
     }
   })
-
-  originalColumnSettings.value = cloneSettings(columnSettings.value)
 }
```

`columnConfig` 本來就是從同一個 CSV、同一個順序產生的，索引保證對得上，改過名稱的欄位因此也能正確還原 `name` / `type` / `role`。

`useExisting` 參數供「改動 3」的 Reset 使用：傳 `false` 時忽略已存的 config，純粹從 CSV 重新推斷。

**索引對位的前提**：`columnConfig` 與 CSV 欄位順序、數量一致。若使用者換了一份欄位數不同的 CSV，`props.columnConfig?.[index]` 在超出範圍時回 `undefined`，該欄退回自動推斷的預設值——與換檔案時該有的行為一致，不需額外處理。

**移除 `originalColumnSettings`**：這個快照原本只服務 Reset，「改動 3」重新定義 Reset 之後它不再有用途，連同 `cloneColumnSetting()` / `cloneSettings()` 兩個 helper 一起刪除（確認無其他呼叫點）。

## 改動 3：Reset 重新定義為「回到自動推斷的預設」

即時同步之後，「上次存檔」這個概念不存在了——每一次改動都已經是存檔。Reset 因此改為「重來一次」：名稱回 CSV 表頭、型別回自動偵測、Role 全部回 `feature`（Target 清空），並立刻同步出去。

`DataTablePanel.vue:306-312`：

```diff
 function resetColumnSettings (): void {
-  if (originalColumnSettings.value.length === 0) {
-    buildColumnSettings()
-    return
-  }
-  columnSettings.value = cloneSettings(originalColumnSettings.value)
+  buildColumnSettings(false)
 }
```

不需要在這裡手動 emit——`columnSettings` 被整個換掉會觸發改動 2a 的 deep watch，同步自然發生。

「繼續」按鈕（`applyColumnSettings()`）保留，但只剩「往下一步走」的職責，不再負責存檔：

```diff
 function applyColumnSettings (): void {
-  emitColumnConfig()
-  originalColumnSettings.value = cloneSettings(columnSettings.value)
   emit('apply-column-config')
 }
```

`hasTarget` 為 false 時「繼續」仍然 disabled（134-142 行的按鈕既有邏輯不動）——沒有目標變數就不該往下走，這與存檔時機無關。

## 改動 4：「欄位設定」標題 —— 保留（原設計要刪，已作廢）

原設計要刪掉卡片內的 `.column-settings-title`，理由是面板標題區的「Data Table + 設定欄位型別與目標變數」已經說明了這張表是什麼。**使用者在實作途中決定保留它。**

保留的話有一件事必須一起做：改動 5 把卡片 `padding` 收成 `0`，標題若不自己帶內距就會黏在卡片邊框上。所以：

```css
.column-settings-title {
  flex-shrink: 0;
  padding: 10px 12px;
  font-size: 13px;
  color: #475569;
  font-weight: 600;
}
```

（原本是 `margin-bottom: 10px`，現在由 `padding` 取代；`flex-shrink: 0` 防止它在 flex column 裡被壓扁。）

## 改動 5：白卡片 padding 收成 0

`DataTablePanel.vue` 的 `.data-table-column-settings`（562-572 行）：

```diff
   .data-table-column-settings {
     display: flex;
     flex-direction: column;
-    padding: 14px 16px;
+    padding: 0;
     border-radius: 12px;
     border: 1px solid rgba(0, 93, 255, 0.12);
     background: #ffffff;
     flex: 1 1 380px;
     min-height: 380px;
     overflow: hidden;
   }
```

表格因此貼齊卡片邊框，sticky 表頭的 `#f8fafc` 底色也一路延伸到邊框，整張卡片讀起來像一張完整的表。

`.column-settings-actions` 需要自己補回內距，否則按鈕會黏在邊框上。注意這個 class 在檔案裡被**宣告了兩次**（588-597 行、637-642 行，後者覆蓋前者的 `margin-top` 與部分屬性）——這次順手合併成一份，只留下方這個較完整的版本：

```css
.column-settings-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
  padding: 10px 12px;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0), #ffffff 70%);
  flex-shrink: 0;
}
```

`.column-settings-body` 維持 `overflow-y: auto`，捲動區不受影響。

### 副作用：捲軸槽變成右側一條白邊

卡片 padding 歸零之後，`.column-settings-body` 的捲軸佔位（macOS 設定為常駐捲軸時約 15px）失去了原本 16px 內縮的遮蔽，露出成右側一條白邊；更糟的是灰色 sticky 表頭在那裡斷掉，整體讀起來像破圖。

改成細捲軸，讓那條縫縮到 6px 並且讀起來像捲軸而不是排版 bug：

```css
.column-settings-body {
  /* …既有屬性… */
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.5) transparent;
}

.column-settings-body::-webkit-scrollbar {
  width: 6px;
}

.column-settings-body::-webkit-scrollbar-track {
  background: transparent;
}

.column-settings-body::-webkit-scrollbar-thumb {
  border-radius: 3px;
  background: rgba(148, 163, 184, 0.5);
}
```

**這條縫不會完全消失**——捲軸一定要佔空間。要徹底消除，必須把 sticky `<thead>` 搬出捲動容器（表頭固定在外、只讓資料列捲動），代價是兩張表的欄寬同步，容易脆化。不值得，維持 6px 版本。

### 表格改用固定欄寬

表格原本沒有指定 `table-layout`，瀏覽器用 auto layout 依內容分配欄寬：Column Name / Type / Role 裡塞的是 `<input>` 和 `<select>`（有原生的固有寬度，input 預設約 20 字元寬），所以這三欄搶走大部分空間，Values 撿剩下的。結果是**欄寬取決於內容而非設計**，換一份 CSV（長欄名、多類別值）寬度就會跑掉。

```css
.column-settings-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.column-settings-table th:nth-child(1),
.column-settings-table td:nth-child(1) { width: 37%; }

.column-settings-table th:nth-child(2),
.column-settings-table td:nth-child(2) { width: 26%; }

.column-settings-table th:nth-child(3),
.column-settings-table td:nth-child(3) { width: 22%; }

.column-settings-table th:nth-child(4),
.column-settings-table td:nth-child(4) { width: 15%; }
```

同時**移除** `.values-cell` 的 `max-width: 300px`：固定佈局下欄寬由百分比決定，留著 max-width 只是兩套機制互相打架；ellipsis 截斷仍由 `overflow: hidden` + `white-space: nowrap` 負責。

## 改動 6：Values 欄四種型別都要有內容

這是 #14「感覺空」的主因。`getColumnValueLabel()`（320-330 行）重寫，依 `column.type` 分派：

| 型別 | 顯示 | 例 |
|---|---|---|
| `numeric` | `min – max` | `18 – 79` |
| `datetime` | `最早 – 最晚` | `2024-01-03 – 2024-12-28` |
| `categorial` | 前 6 個唯一值，`, ` 相連（維持現狀） | `male, female` |
| `text` | 前 3 個唯一值當範例 | `chest pain, fatigue, dizziness` |

規則細節：

- **分隔符**：en dash 前後各一個半形空格（`' – '`），與逗號分隔的唯一值列表在視覺上區隔開來。
- **數字格式**：整數原樣輸出。小數則分兩種情況——絕對值小於 1 時用 `toPrecision(3)`（有效位數），否則用 `toFixed(3)`（小數位數），兩者都再包一層 `Number()` 去掉尾隨的 0。避免 `18.000000000000004` 這種浮點雜訊曝在畫面上。
  **為什麼不能一律用 `toFixed(3)`**：它會把絕對值小於 0.0005 的數壓成 `0`。一欄值是 `0.0001 / 0.0002 / 0.0003` 的資料會顯示成 `0 – 0`，看起來像「這欄沒有變異」——那是**會說謊的顯示**。`toPrecision(3)` 對這種值會給 `0.0001 – 0.0003`。
- **日期格式**：**直接顯示原始字串**，不重新格式化。做法是對 `Date.parse()` 得到的 timestamp 取 min/max，記住是哪兩列，輸出那兩列的原始儲存格文字。這樣不會因為時區轉換讓畫面上的日期跟 CSV 裡的日期差一天。
- **空欄位**：過濾掉空白後若沒有任何值可用（整欄皆空、或 `numeric` 欄位解析不出任何數字），仍然顯示 `'—'`。
- **型別是使用者當下選的**：這個函式讀 `columnSettings[index].type` 而非重新推斷，所以使用者把某欄從 Numeric 改成 Categorical 時，Values 欄會立刻跟著換成唯一值列表。

`.values-cell` 既有的 `max-width: 300px` + `text-overflow: ellipsis`（630-635 行）不動，過長的內容仍會被截斷。

## 驗收

實際開 dev server（`npm run dev`）走 Data Table 節點：

1. **副標**：面板標題底下顯示「設定欄位型別與目標變數」。
2. **即時同步（未改名）**：選一欄為 Target → **不按「繼續」** → 切到 Distribution 節點 → 切回 Data Table → Target 仍在，藍色指示卡已轉綠。
3. **即時同步（改過名）**：改某欄名稱並設為 Target → 不按「繼續」 → 切走再切回 → 名稱與 Target 都還在（這一項會抓到只做 2a、沒做 2b 的情況）。
4. **Type 也要保住**：把某欄型別從 Numeric 改成 Categorical → 切走切回 → 仍是 Categorical。
5. **Reset**：改了名稱、型別、Role 之後按 Reset → 三者全部回到剛載入檔案時的樣子，Target 清空、「繼續」變回 disabled；此時切走再切回，仍是重置後的狀態（證明 Reset 有同步出去，不只是視覺上的重置）。
6. **「繼續」仍照舊**：選好 Target 按「繼續」 → 流程往 Settings 前進，行為與現在一致。
7. **Values 欄**：載入一份含數值、類別、日期欄的 CSV → 四種型別都有內容，沒有整排「—」；日期顯示的字串與 CSV 內容一致（沒有差一天）；一欄極小數值（如 `0.0001 / 0.0002 / 0.0003`）顯示 `0.0001 – 0.0003` 而非 `0 – 0`。
8. **留白**：「欄位設定」小標仍在但不黏邊框；表格貼齊卡片邊框；按鈕列有適當內距、沒有黏邊；右側捲軸是細的（6px），不是一條顯眼的白邊。
9. **欄寬**：換不同的 CSV（長中文欄名、多類別值），四欄寬度維持 37/26/22/15 不變。
10. `npm run build` 通過，且改動過的檔案沒有新增 lint 錯誤（`npm run lint` 在本專案 baseline 就是紅的，不能拿它當閘門）。
