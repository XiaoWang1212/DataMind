# Data Table 面板：副標文案、欄位設定即時同步、留白收緊 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修好 Data Table 面板的三件事——副標文案改成名實相符的「設定欄位型別與目標變數」；欄位設定（名稱／型別／Role）改成一改動就即時同步回父層，切換節點不再遺失 Target；收掉 #14 的多餘留白（拿掉重複標題、卡片 padding 收 0、Values 欄四種型別都有內容）。

**Architecture:** 三件事都落在 `DataTablePanel.vue`（外加一行 `workflowData.ts` 的文案），但改動性質不同，拆成四個可獨立驗證、獨立 review 的 task：Task 1 純文案；Task 2 動 `<script setup>` 的資料流（deep watch 即時 emit + 索引對位 + Reset 重新定義），這是唯一有行為風險的一刀；Task 3 動 template/CSS 的留白；Task 4 動 Values 欄的顯示邏輯。父層（`WorkflowOptionsPanel` → `WorkflowWorkspace` → `node.data.config`）的鏈路已經完好，本次**完全不需要改父層**。

**Tech Stack:** Vue 3 `<script setup lang="ts">` SFC、scoped CSS、無額外套件。

## Global Constraints

- **無自動化測試框架**：前端沒有 vitest/jest（`frontend/package.json` 沒有 `test` script）。依 `CLAUDE.md` 慣例，以「啟動 `npm run dev` 在瀏覽器手動操作」取代自動化測試。若執行者無法完成手動驗證，**必須明確說出「無法測試 UI」，不得逕自宣稱驗證通過**。
- **`npm run lint` 本來就是紅的，不要拿它當閘門**（實測 baseline：854 個問題、exit 1，多為既有的引號／分號風格錯誤）。每個 task 的驗證步驟＝
  1. `npm run build`（含 `vue-tsc` type-check）**必須 exit 0**；
  2. 用 `npx eslint <改動的檔案>` 比對改動前後的錯誤數，**不可新增**新的 lint 錯誤（既有的不用管、也不要順手修）；
  3. 該 task 指定的手動瀏覽器操作。
- **Commit 前必須先取得使用者明確同意**：完成實作、跑完 lint/build、列出手動驗證步驟後，停下來明確詢問使用者「瀏覽器手動測試沒問題了嗎？」，取得明確答覆後才能 `git add` / `git commit`。即使透過 `superpowers:subagent-driven-development` 執行，也要覆蓋掉 implementer 預設會自動 commit 的行為。
- **Commit 訊息格式**：只寫**一行**簡短標題（如 `fix: sync data table column settings to parent on change`），**不要**多段落 body，**不要**加 `Co-Authored-By` trailer。
- **本次不做的事**：不補資料列預覽功能；不改節點名稱 `Data Table`；不改父層 `WorkflowOptionsPanel.vue` / `WorkflowWorkspace.vue` / `useWorkflowExecution.ts`；不動 `.column-settings-body` 的捲動行為；不動 `.values-cell` 既有的 `max-width: 300px` + ellipsis 截斷。
- **既有的「繼續」按鈕 disabled 條件不變**：`hasTarget` 為 false 時 disabled（`DataTablePanel.vue:134-142` 的按鈕邏輯）。存檔時機改變不影響這個閘門。
- 所有面向使用者的文案維持繁體中文。
- Spec 來源：`docs/superpowers/specs/2026-07-13-data-table-panel-fixes-design.md`

---

## File Structure

| 檔案 | 職責 | 本次改動 |
|---|---|---|
| `frontend/src/constants/workflowData.ts` | 工作流節點的初始定義（icon/label/description/config） | 只改 `dataTable` 節點的 `description` 一行文案（Task 1） |
| `frontend/src/components/workflow/nodePanel/DataTablePanel.vue` | Data Table 節點面板：欄位設定表格（Column Name / Type / Role / Values）＋暫停等待選 target 的提示卡 | `<script setup>`：即時同步 + 索引對位 + Reset 重新定義（Task 2）、Values 欄顯示邏輯（Task 4）；template/CSS：拿掉重複標題、卡片 padding 收 0、合併重複的 CSS 宣告（Task 3） |
| `.claude/ux-issues.md` | 專案的 UX 問題追蹤清單 | 收尾回填三個項目的狀態（Task 5） |

兩個程式檔都已存在，不新增檔案。

**Task 之間的相依性**：Task 2 必須在 Task 4 之前完成——Task 4 的 `getColumnValueLabel()` 讀 `columnSettings[index].type`，而 Task 2 改寫了 `buildColumnSettings()` 決定 `type` 的方式。Task 1 與 Task 3 跟其他 task 互不相干，順序可調。Task 5 必須最後做。

---

## Task 1: 副標文案改成「設定欄位型別與目標變數」

**Files:**
- Modify: `frontend/src/constants/workflowData.ts:31`

**Interfaces:**
- Consumes: 無。
- Produces: 無新介面。這行 `description` 由 `WorkflowOptionsPanel.vue:9`（`<p>{{ selectedNode.data.description }}</p>`）顯示在面板標題區。Task 3 會拿掉卡片內重複的「欄位設定」小標，仰賴這行文案接手說明職責——**Task 3 的實作者要知道這行字已經在了**。

- [ ] **Step 1: 改掉 description 文案**

`frontend/src/constants/workflowData.ts`，`dataTable` 節點（21-34 行）。把：

```ts
  {
    id: "dataTable",
    type: "iconNode",
    position: { x: 60, y: 290 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-table",
      label: "Data\nTable",
      colorClass: "node-pending",
      description: "上傳資料預覽",
      fields: [],
      config: {},
    },
  },
```

改成（**只有 `description` 那一行變動，`label` 維持 `"Data\nTable"` 不要動**）：

```ts
  {
    id: "dataTable",
    type: "iconNode",
    position: { x: 60, y: 290 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-table",
      label: "Data\nTable",
      colorClass: "node-pending",
      description: "設定欄位型別與目標變數",
      fields: [],
      config: {},
    },
  },
```

- [ ] **Step 2: 跑 lint 與 build**

```bash
cd frontend && npm run lint && npm run build
```

Expected: 兩者都 exit 0，沒有 error。

- [ ] **Step 3: 手動驗證**

```bash
cd frontend && npm run dev
```

在瀏覽器開 `http://localhost:3000/workflow`，上傳一份 CSV，點 Data Table 節點打開抽屜。

Expected: 面板標題「Data Table」底下那行小字顯示「設定欄位型別與目標變數」，不再是「上傳資料預覽」。畫布上的節點名稱仍是兩行的「Data Table」。

- [ ] **Step 4: 詢問使用者手動驗證結果，取得同意後才 commit**

先問使用者：「Task 1 的副標文案在瀏覽器上看起來對嗎？可以 commit 嗎？」等到明確答覆再執行：

```bash
git add frontend/src/constants/workflowData.ts
git commit -m "fix: correct data table node subtitle to match actual function"
```

---

## Task 2: 欄位設定即時同步回父層（含索引對位與 Reset 重新定義）

這是唯一有行為風險的一刀。三個改動**缺一不可**：只做即時同步而不改對位方式的話，使用者一旦改過欄位名稱，設定仍然會被吃掉（Step 7 的手動驗證第 3 項就是專門用來抓這個情況）。

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:211`（刪除 `originalColumnSettings`）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:256-267`（刪除 `cloneColumnSetting` / `cloneSettings`）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:269-293`（`buildColumnSettings`）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:306-318`（`resetColumnSettings` / `applyColumnSettings`）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:332-360` 附近（新增 deep watch）

**Interfaces:**
- Consumes: 既有的 `props.columnConfig`（型別 `ColumnConfig[] | undefined`，`ColumnConfig = { name: string; type: ColumnType; role: ColumnRole }`）、既有的 `emit('update-column-config', payload: ColumnConfig[])` 與 `emit('apply-column-config')`、既有的 `emitColumnConfig()`（295-304 行）、既有的 `previewColumns` / `previewDataRows` / `columnSettings` refs。全部既有，**不新增任何 props 或 emits**。
- Produces:
  - `buildColumnSettings(useExisting = true): void` — 新增一個布林參數。傳 `true`（預設）＝從 `props.columnConfig` 依**索引**還原既有設定；傳 `false`＝忽略既有設定，純粹從 CSV 重新推斷。**Task 4 的實作者要知道 `columnSettings[i].type` 是由這個函式決定的。**
  - `originalColumnSettings`、`cloneColumnSetting()`、`cloneSettings()` **不再存在**——後續 task 不可引用。

- [ ] **Step 1: 刪除 `originalColumnSettings` ref 與兩個 clone helper**

`DataTablePanel.vue:211`，刪除這一行：

```ts
  const originalColumnSettings = ref<ColumnSetting[]>([])
```

（**保留**下一行的 `const nameMaxLength = 32`。）

`DataTablePanel.vue:256-267`，刪除這兩個函式：

```ts
  function cloneColumnSetting (item: ColumnSetting): ColumnSetting {
    return {
      name: item.name,
      type: item.type,
      role: item.role,
      availableTypes: [...item.availableTypes],
    }
  }

  function cloneSettings (settings: ColumnSetting[]): ColumnSetting[] {
    return settings.map(setting => cloneColumnSetting(setting))
  }
```

這三者原本只服務「Reset 回到上次存檔狀態」的快照機制，Step 3 重新定義 Reset 之後就沒有呼叫點了。刪完之後檔案裡不該再有 `originalColumnSettings` / `cloneSettings` / `cloneColumnSetting` 這三個字串（Step 5 會驗證）。

- [ ] **Step 2: `buildColumnSettings()` 改用索引對位，並加上 `useExisting` 參數**

把 `DataTablePanel.vue:269-293` 整個函式：

```ts
  function buildColumnSettings (): void {
    const existingMap = new Map(
      (props.columnConfig ?? []).map(config => [config.name, config]),
    )

    columnSettings.value = previewColumns.value.map((header, index) => {
      const columnValues = previewDataRows.value.map(row => row[index] ?? '')
      const availableTypes = getColumnTypeCandidates(columnValues)
      const existing = existingMap.get(header)
      const selectedType
        = existing && availableTypes.includes(existing.type)
          ? existing.type
          : (availableTypes[0] ?? 'text')
      const selectedRole = existing?.role ?? 'feature'

      return {
        name: header,
        type: selectedType,
        role: selectedRole,
        availableTypes,
      }
    })

    originalColumnSettings.value = cloneSettings(columnSettings.value)
  }
```

改成：

```ts
  function buildColumnSettings (useExisting = true): void {
    columnSettings.value = previewColumns.value.map((header, index) => {
      const columnValues = previewDataRows.value.map(row => row[index] ?? '')
      const availableTypes = getColumnTypeCandidates(columnValues)
      // 用索引對位而非名稱：Column Name 是可編輯的，改過名字之後
      // CSV 表頭跟存下來的 name 就對不上，會讓整欄設定被重置
      const existing = useExisting ? props.columnConfig?.[index] : undefined
      const selectedType
        = existing && availableTypes.includes(existing.type)
          ? existing.type
          : (availableTypes[0] ?? 'text')
      const selectedRole = existing?.role ?? 'feature'

      return {
        name: existing?.name ?? header,
        type: selectedType,
        role: selectedRole,
        availableTypes,
      }
    })
  }
```

三處變動：函式簽名多了 `useExisting = true`；`existingMap.get(header)` 換成 `props.columnConfig?.[index]`；`name: header` 換成 `name: existing?.name ?? header`（這樣改過的名稱才還原得回來）。尾巴的 `originalColumnSettings.value = ...` 一併移除。

若使用者換了一份欄位數不同的 CSV，`props.columnConfig?.[index]` 超出範圍時回 `undefined`，該欄自然退回自動推斷的預設值——這正是換檔案時該有的行為，不需要額外處理。

- [ ] **Step 3: 重寫 `resetColumnSettings()`，簡化 `applyColumnSettings()`**

把 `DataTablePanel.vue:306-318` 這兩個函式：

```ts
  function resetColumnSettings (): void {
    if (originalColumnSettings.value.length === 0) {
      buildColumnSettings()
      return
    }
    columnSettings.value = cloneSettings(originalColumnSettings.value)
  }

  function applyColumnSettings (): void {
    emitColumnConfig()
    originalColumnSettings.value = cloneSettings(columnSettings.value)
    emit('apply-column-config')
  }
```

改成：

```ts
  // Reset ＝ 回到自動推斷的預設（名稱回 CSV 表頭、型別回自動偵測、Role 全回 feature）
  // 即時同步之後「上次存檔」不再是一個有意義的狀態，每次改動本身就是存檔
  function resetColumnSettings (): void {
    buildColumnSettings(false)
  }

  // 「繼續」只剩「往下一步走」的職責，存檔已由 Step 4 的 deep watch 即時完成
  function applyColumnSettings (): void {
    emit('apply-column-config')
  }
```

`resetColumnSettings()` 不需要手動 emit——它把 `columnSettings.value` 整個換掉，會觸發 Step 4 的 deep watch，同步自然發生。

- [ ] **Step 4: 新增 deep watch，一改動就 emit**

在 `DataTablePanel.vue` 既有的兩個 `watch`（`props.file` 與 `props.columnConfig`，332-360 行）**後面**，新增第三個 watch：

```ts
  // 欄位設定一有變動就即時同步回父層，不再等按「繼續」才 emit。
  // 切到別的節點會讓這個面板被卸載（父層是 v-if 掛載），本地 columnSettings
  // 隨之銷毀，只能靠父層 node.data.config 還原——所以必須即時寫回去。
  watch(
    columnSettings,
    () => {
      emitColumnConfig()
    },
    { deep: true },
  )
```

一個掛勾覆蓋全部三個可編輯控制項（名稱 `<input>`、Type `<select>`、Role `<select>`）。

**為什麼不會跟 `props.columnConfig` 的 watcher 形成無窮迴圈**：那個 watcher（350-360 行）只在 `!areColumnConfigsEqual(value, columnSettings.value)` 時才呼叫 `buildColumnSettings()`。我們 emit 出去的值經父層寫回 `node.data.config` 再以 prop 回來，內容必然與當下的 `columnSettings` 相等 → 比對為 true → 不重建 → 一輪收斂。**不要**為了「保險」再加額外的旗標或防抖，那只會讓資料流更難理解。

**檔案載入時就會 emit 一次自動推斷的預設值**（`buildColumnSettings()` 換掉整個 `columnSettings` → 觸發這個 watch），使用者還沒動手，`node.data.config.columnConfig` 就已經有一份 Role 全為 `feature` 的預設。**這是預期行為，不要加防呆擋掉它**：能不能往下跑的閘門是 `useWorkflowExecution.ts:49-52` 的 `canRun`，它同時要求 `dataTableApplied.value` 為 true，而該旗標只在 `WorkflowWorkspace.handleApplyColumnConfig()`（286 行，即按下「繼續」時）才會被設為 true。提早寫入 config 不會讓流程提早變成可執行。

- [ ] **Step 5: 確認死碼已清乾淨**

```bash
cd frontend && grep -n "originalColumnSettings\|cloneSettings\|cloneColumnSetting" src/components/workflow/nodePanel/DataTablePanel.vue
```

Expected: **沒有任何輸出**（grep exit code 1）。若還有輸出，表示 Step 1 沒刪乾淨。

- [ ] **Step 6: 跑 lint 與 build**

```bash
cd frontend && npm run lint && npm run build
```

Expected: 兩者都 exit 0。特別注意 `vue-tsc` 不該報 `ColumnSetting` 型別未使用之類的錯——`ColumnSetting` interface 仍被 `columnSettings` ref 使用，不要順手刪掉它。

- [ ] **Step 7: 手動驗證（六項，這是本 task 的核心）**

```bash
cd frontend && npm run dev
```

開 `http://localhost:3000/workflow`，上傳 CSV，跑到 Data Table 節點暫停處。逐項確認：

1. **即時同步（未改名）**：把某欄 Role 選成 Target → **不要按「繼續」** → 切到 Distribution 節點 → 再切回 Data Table。
   Expected: Target 仍在該欄，藍色指示卡已轉綠（顯示「已選定目標變數『X』」）。

2. **即時同步（改過名）**：把某欄名稱改掉（例如 `died` → `是否死亡`）並選成 Target → **不要按「繼續」** → 切走 → 切回。
   Expected: 名稱與 Target **都還在**。（這一項專門用來抓「只做了 Step 4、沒做 Step 2 索引對位」的情況——那種情況下這一項會失敗，但第 1 項會過。）

3. **Type 也要保住**：把某欄型別從 Numeric 改成 Categorical → 切走 → 切回。
   Expected: 仍是 Categorical。

4. **Reset**：改了名稱、型別、Role 之後按 Reset。
   Expected: 三者全部回到剛載入檔案時的樣子，Target 清空，「繼續」按鈕變回灰色 disabled。**接著切走再切回**——Expected: 仍是重置後的狀態（這證明 Reset 有同步出去，不只是視覺上的重置）。

5. **「繼續」行為不變**：選好 Target 按「繼續」。
   Expected: 流程往 Settings 節點前進，跟現在的行為一致。

6. **沒有無窮迴圈**：上述操作過程中打開瀏覽器 DevTools Console。
   Expected: 沒有 `Maximum recursive updates exceeded` 之類的 Vue 警告，頁面沒有卡住。

- [ ] **Step 8: 詢問使用者手動驗證結果，取得同意後才 commit**

先問使用者：「Task 2 的六項手動驗證（特別是第 2 項『改過名字再切走切回』）在瀏覽器上都過了嗎？可以 commit 嗎？」等到明確答覆再執行：

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "fix: sync data table column settings to parent on every change"
```

---

## Task 3: 收掉留白——拿掉重複標題、卡片 padding 收 0、合併重複 CSS

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:45`（template，刪除 `.column-settings-title`）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:562-572`（style，`.data-table-column-settings`）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:574-579`（style，刪除 `.column-settings-title`）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:588-597` 與 `:637-642`（style，合併重複宣告的 `.column-settings-actions`）

> **行號提醒**：若 Task 2 已經先做完，`<script setup>` 區塊會少掉約 20 行，上述 style 區塊的行號會整體往前位移。**請用 class 名稱搜尋定位，不要死認行號。**

**Interfaces:**
- Consumes: Task 1 產出的 `description` 文案（「設定欄位型別與目標變數」）已顯示在面板標題區——這正是拿掉卡片內「欄位設定」小標之後，接手說明職責的那行字。
- Produces: 無新介面。`.column-settings-title` 這個 class 之後**不再存在**。`.column-settings-actions` 之後只有**一份**宣告。

- [ ] **Step 1: 刪除 template 裡重複的「欄位設定」標題**

`DataTablePanel.vue:44-46`。把：

```html
      <div v-if="columnSettings.length > 0" class="data-table-column-settings">
        <div class="column-settings-title">欄位設定</div>
        <div class="column-settings-body">
```

改成（只刪中間那一行）：

```html
      <div v-if="columnSettings.length > 0" class="data-table-column-settings">
        <div class="column-settings-body">
```

- [ ] **Step 2: 卡片 padding 收成 0**

搜尋 `.data-table-column-settings`（原 562-572 行）。把：

```css
  .data-table-column-settings {
    display: flex;
    flex-direction: column;
    padding: 14px 16px;
    border-radius: 12px;
    border: 1px solid rgba(0, 93, 255, 0.12);
    background: #ffffff;
    flex: 1 1 380px;
    min-height: 380px;
    overflow: hidden;
  }
```

改成（只有 `padding` 那一行變動，其餘**原樣保留**——`overflow: hidden` 尤其重要，它負責把貼邊的表格裁進圓角裡）：

```css
  .data-table-column-settings {
    display: flex;
    flex-direction: column;
    padding: 0;
    border-radius: 12px;
    border: 1px solid rgba(0, 93, 255, 0.12);
    background: #ffffff;
    flex: 1 1 380px;
    min-height: 380px;
    overflow: hidden;
  }
```

- [ ] **Step 3: 刪除 `.column-settings-title` 的 CSS**

搜尋 `.column-settings-title`（原 574-579 行），刪除整個規則：

```css
  .column-settings-title {
    margin-bottom: 10px;
    font-size: 13px;
    color: #475569;
    font-weight: 600;
  }
```

- [ ] **Step 4: 合併重複宣告的 `.column-settings-actions`，並補回內距**

`.column-settings-actions` 在這個檔案裡被宣告了**兩次**（原 588-597 行與 637-642 行，後者覆蓋前者部分屬性）。這次合併成一份。

先刪掉**第二份**（原 637-642 行）：

```css
  .column-settings-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 14px;
  }
```

再把**第一份**（原 588-597 行）：

```css
  .column-settings-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 14px;
    padding-top: 10px;
    border-top: 1px solid rgba(148, 163, 184, 0.12);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0), #ffffff 70%);
    flex-shrink: 0;
  }
```

改成（`padding-top: 10px` 換成四邊都有的 `padding: 10px 12px`——卡片 padding 歸零之後，按鈕必須靠這個內距才不會黏在卡片邊框上）：

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

- [ ] **Step 5: 確認 CSS 沒有殘留重複宣告**

```bash
cd frontend && grep -c "\.column-settings-actions {" src/components/workflow/nodePanel/DataTablePanel.vue
```

Expected: 輸出 `1`（只剩一份宣告；若輸出 `2` 表示 Step 4 沒刪掉重複的那一份）。

```bash
cd frontend && grep -n "column-settings-title" src/components/workflow/nodePanel/DataTablePanel.vue
```

Expected: **沒有任何輸出**（`column-settings-title` 在 template 與 style 都已不存在）。

- [ ] **Step 6: 跑 lint 與 build**

```bash
cd frontend && npm run lint && npm run build
```

Expected: 兩者都 exit 0。

- [ ] **Step 7: 手動驗證**

```bash
cd frontend && npm run dev
```

開 Data Table 節點面板。Expected:

1. 白卡片裡**沒有**「欄位設定」這個小標題（面板標題區的「Data Table / 設定欄位型別與目標變數」還在）。
2. 表格**貼齊**白卡片邊框，sticky 表頭的淺灰底色一路延伸到左右邊框，圓角有把表格裁乾淨（沒有直角溢出）。
3. 底部按鈕列（Reset / 繼續）**沒有黏在邊框上**，上下左右都有適當內距。
4. 表格內容超過卡片高度時**仍然可以在卡片內部捲動**，捲動時表頭固定不動（`.column-settings-body` 的 `overflow-y: auto` 與 sticky thead 沒被破壞）。
5. drawer 的三段高度（collapsed / expanded / full）都拉一次看看，排版沒有破。

- [ ] **Step 8: 詢問使用者手動驗證結果，取得同意後才 commit**

先問使用者：「Task 3 的留白調整在瀏覽器上看起來對嗎？可以 commit 嗎？」等到明確答覆再執行：

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "style: tighten data table panel whitespace"
```

---

## Task 4: Values 欄四種型別都要有內容

**前置**：必須在 Task 2 之後做（`getColumnValueLabel()` 讀 `columnSettings[index].type`，而 Task 2 改寫了決定 `type` 的 `buildColumnSettings()`）。

這是 #14「整體偏空」的**主因**：現在 `getColumnValueLabel()` 只對 `categorial` 回傳內容，其餘型別一律回 `'—'`，所以一份以數值欄為主的資料集，最右欄會是一整排破折號。

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:320-330`（`getColumnValueLabel`）

> **行號提醒**：Task 2 做完後行號會往前位移，請用函式名稱搜尋定位。

**Interfaces:**
- Consumes: `columnSettings`（其 `type` 由 Task 2 的 `buildColumnSettings()` 決定）、`previewDataRows`、既有的 `ColumnType` 型別（`'numeric' | 'categorial' | 'text' | 'datetime'`）。
- Produces: `getColumnValueLabel(index: number): string`（簽名不變，template 的呼叫點 `{{ getColumnValueLabel(index) }}` 不用動）；新增兩個模組內 helper：`formatNumericValue(value: number): string`、`getColumnRawValues(index: number): string[]`。

顯示規則：

| 型別 | 顯示 | 例 |
|---|---|---|
| `numeric` | `min – max` | `18 – 79` |
| `datetime` | `最早 – 最晚`（**原始字串**，不重新格式化） | `2024-01-03 – 2024-12-28` |
| `categorial` | 前 6 個唯一值，`, ` 相連（維持現狀） | `male, female` |
| `text` | 前 3 個唯一值當範例 | `chest pain, fatigue, dizziness` |

- [ ] **Step 1: 重寫 `getColumnValueLabel()` 並補上兩個 helper**

搜尋 `function getColumnValueLabel`（原 320-330 行）。把整個函式：

```ts
  function getColumnValueLabel (index: number): string {
    const column = columnSettings.value[index]
    if (!column || column.type !== 'categorial') return '—'

    const values = previewDataRows.value
      .map(row => row[index] ?? '')
      .map(value => value.trim())
      .filter(value => value.length > 0)
    const uniqueValues = Array.from(new Set(values))
    return uniqueValues.slice(0, 6).join(', ')
  }
```

替換成：

```ts
  // 取某欄所有非空的原始字串值
  function getColumnRawValues (index: number): string[] {
    return previewDataRows.value
      .map(row => row[index] ?? '')
      .map(value => value.trim())
      .filter(value => value.length > 0)
  }

  // 整數原樣輸出；小數最多留 3 位並去掉尾隨的 0，避免 18.000000000000004 這種浮點雜訊
  function formatNumericValue (value: number): string {
    return Number.isInteger(value)
      ? String(value)
      : String(Number(value.toFixed(3)))
  }

  function getColumnValueLabel (index: number): string {
    const column = columnSettings.value[index]
    if (!column) return '—'

    const values = getColumnRawValues(index)
    if (values.length === 0) return '—'

    if (column.type === 'numeric') {
      let min = Number.POSITIVE_INFINITY
      let max = Number.NEGATIVE_INFINITY
      for (const value of values) {
        const parsed = Number(value)
        if (Number.isNaN(parsed)) continue
        if (parsed < min) min = parsed
        if (parsed > max) max = parsed
      }
      if (min === Number.POSITIVE_INFINITY) return '—'
      return `${formatNumericValue(min)} – ${formatNumericValue(max)}`
    }

    if (column.type === 'datetime') {
      // 顯示原始字串而非重新格式化，避免時區轉換讓畫面上的日期跟 CSV 差一天
      let minText = ''
      let maxText = ''
      let minTime = Number.POSITIVE_INFINITY
      let maxTime = Number.NEGATIVE_INFINITY
      for (const value of values) {
        const time = Date.parse(value)
        if (Number.isNaN(time)) continue
        if (time < minTime) {
          minTime = time
          minText = value
        }
        if (time > maxTime) {
          maxTime = time
          maxText = value
        }
      }
      if (!minText || !maxText) return '—'
      return `${minText} – ${maxText}`
    }

    const uniqueValues = Array.from(new Set(values))
    const limit = column.type === 'categorial' ? 6 : 3
    return uniqueValues.slice(0, limit).join(', ')
  }
```

三個實作細節，**不要自作主張改掉**：

- **分隔符是 en dash 前後各一個半形空格**（`' – '`，U+2013），不是 hyphen、不是全形破折號。這樣才跟逗號分隔的唯一值列表在視覺上區隔開來。
- **min/max 用 for 迴圈算，不要用 `Math.min(...numbers)`**。`previewDataRows` 存的是整份 CSV 的所有列（`loadFile()` 裡是 `lines.slice(1)`，沒有截斷），大檔案展開成函式引數會超過引數數量上限而爆掉。
- **`values.length === 0` 才回 `'—'`**（整欄皆空）；`numeric` 欄若一個數字都解析不出來，也回 `'—'`。

- [ ] **Step 2: 跑 lint 與 build**

```bash
cd frontend && npm run lint && npm run build
```

Expected: 兩者都 exit 0。

- [ ] **Step 3: 準備一份四種型別都有的測試 CSV**

```bash
cat > /tmp/values-check.csv <<'EOF'
age,visit_date,sex,notes,score
18,2024-01-03,male,chest pain,3.5
79,2024-12-28,female,fatigue,9.25
45,2024-06-15,male,dizziness,7.125
EOF
```

- [ ] **Step 4: 手動驗證**

```bash
cd frontend && npm run dev
```

上傳 `/tmp/values-check.csv`，打開 Data Table 節點。Expected（Values 欄）：

1. `age`（Numeric）顯示 `18 – 79`。
2. `score`（Numeric，小數）顯示 `3.5 – 9.25`——小數點後**沒有**一長串浮點雜訊。
3. `visit_date`（Datetime）顯示 `2024-01-03 – 2024-12-28`——字串跟 CSV 裡的**完全一致**，沒有差一天。
4. `sex`（Categorical）顯示 `male, female`。
5. `notes`（Text 或 Categorical，看自動推斷結果）有內容，不是 `—`。
6. **整張表沒有任何一欄是 `—`**（這就是 #14「感覺空」的主因被解掉的證據）。
7. **型別切換要連動**：手動把 `age` 的 Type 從 Numeric 改成 Categorical → Values 欄立刻變成 `18, 79, 45` 這種唯一值列表；再改回 Numeric → 變回 `18 – 79`。

- [ ] **Step 5: 詢問使用者手動驗證結果，取得同意後才 commit**

先問使用者：「Task 4 的 Values 欄在瀏覽器上四種型別都有內容了嗎？可以 commit 嗎？」等到明確答覆再執行：

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "feat: show value range for numeric and datetime columns"
```

---

## Task 5: 回填 `.claude/ux-issues.md`

**前置**：Task 1-4 全部完成並 commit 之後才做。

**Files:**
- Modify: `.claude/ux-issues.md:31`（Role/Target 遺失的「⚠️ 新發現待處理」）
- Modify: `.claude/ux-issues.md:153-156`（問題 #14）
- Modify: `.claude/ux-issues.md:192`（副標題待辦）

**Interfaces:**
- Consumes: Task 1-4 的實際 commit hash（`git log --oneline -5` 取得）。
- Produces: 無程式介面。

- [ ] **Step 1: 取得本次的 commit hash**

```bash
git log --oneline -5
```

記下 Task 1-4 四個 commit 的 hash，下面填進文件時要用。

- [ ] **Step 2: 更新第 31 行的 Role/Target 待處理項**

把（`.claude/ux-issues.md:31`）：

```markdown
> ⚠️ 新發現待處理（2026-07-10）：Role/Target 選擇在使用者按下「繼續」之前只存在 `DataTablePanel.vue` 元件本地狀態；若選好 Target 後、按繼續前就切去別的節點，面板重建會讓選擇遺失（`hasTarget` 重新變 false，暫停指示卡與圈圈也會跟著重新出現，行為上正確但體驗上等於選擇被吃掉）。修法可能是 Role/Type 改變時即時同步回父層，而非等按「繼續」才 emit；屬於資料流改動，範圍較大，本次不處理。
```

改成（`<hash>` 換成 Task 2 的實際 commit hash）：

```markdown
> ✅ 已修（`<hash>`，2026-07-13）：Role/Target 選擇改成「一改動就即時同步回父層」——`DataTablePanel.vue` 對 `columnSettings` 加 deep watch，任何改動立刻 `emit('update-column-config')` 寫進 `node.data.config`，不再等按「繼續」才 emit。同時發現第二條會造成同樣症狀的路徑：`buildColumnSettings()` 原本用**欄位名稱**比對已存的 config，但 Column Name 是可編輯的，使用者改過名字後 CSV 表頭就對不上，整欄設定仍會被重置——一併改成用**索引**對位。附帶影響：「上次存檔」不再是有意義的狀態，Reset 因此重新定義為「回到自動推斷的預設」（名稱回 CSV 表頭、型別回自動偵測、Role 全回 feature），「繼續」則只剩「往下一步走」的職責。
```

- [ ] **Step 3: 把問題 #14 標記為已修**

把（`.claude/ux-issues.md:153-156`）：

```markdown
- [ ] **#14 Data Table Panel 的 padding/margin 感覺偏多，整體偏空**
  - 現象：整個 panel 有不必要的留白感。
  - 現況（2026-07-11）：**未完全確認**。程式碼層級檢查 `DataTablePanel.vue` 目前的間距值本身不算誇張（`.data-table-panel` gap 14px、`.data-table-column-settings` padding 14px 16px、表格 cell padding 10-12px），單看數值沒有明顯異常，但「感覺空」是視覺整體觀感問題，光看 CSS 數字無法下定論，需要實際在瀏覽器打開比對。
  - 待辦：實際開 dev server 走一次 Data Table 節點，比對 collapsed / expanded / full 三段 drawer 高度下的實際留白觀感，再決定要不要收緊。
```

改成（`<hash3>`、`<hash4>` 換成 Task 3、Task 4 的實際 commit hash）：

```markdown
- [x] **#14 Data Table Panel 的 padding/margin 感覺偏多，整體偏空**
  - 現象：整個 panel 有不必要的留白感。
  - ✅ 已修（`<hash3>`、`<hash4>`，2026-07-13）：**「感覺空」的主因不是間距數值，而是 Values 欄整排「—」**。`getColumnValueLabel()` 原本只對 `categorial` 型別回傳內容，其餘一律回 `'—'`，所以以數值欄為主的資料集最右欄會是一長排破折號。改成四種型別都有內容：numeric 顯示 `min – max`、datetime 顯示「最早 – 最晚」（原始字串，避免時區差一天）、categorial 維持前 6 個唯一值、text 顯示前 3 個唯一值當範例。另外兩刀：拿掉卡片內重複的「欄位設定」小標（面板標題區的副標已經說明了這張表是什麼），白卡片 `padding` 從 `14px 16px` 收成 `0` 讓表格貼齊邊框（按鈕列自己補 `padding: 10px 12px`），並順手合併了 `.column-settings-actions` 重複宣告兩次的 CSS。
```

- [ ] **Step 4: 勾掉第 192 行的副標題待辦**

把（`.claude/ux-issues.md:192`）：

```markdown
  - [ ] Data table 的副標題是「上傳資料預覽」是不是要改一下
```

改成（`<hash1>` 換成 Task 1 的實際 commit hash）：

```markdown
  - [x] Data table 的副標題是「上傳資料預覽」是不是要改一下 — ✅ 已改（`<hash1>`，2026-07-13）：面板裡根本沒有資料列預覽，副標名不符實。改成「設定欄位型別與目標變數」，如實描述這個面板實際在做的事。節點名稱 `Data Table` 不動，也不補預覽功能。
```

- [ ] **Step 5: 詢問使用者，取得同意後才 commit**

先問使用者：「文件回填好了，可以 commit 嗎？」等到明確答覆再執行：

```bash
git add .claude/ux-issues.md
git commit -m "docs: mark data table panel issues as fixed"
```

---

## 完成標準

全部 task 做完後，下列每一項都要成立：

- [ ] 面板副標顯示「設定欄位型別與目標變數」。
- [ ] 選好 Target（**不按「繼續」**）切走再切回，Target 還在；**改過欄位名稱**的情況下也還在。
- [ ] 改過的 Type 切走切回也還在。
- [ ] Reset 回到自動推斷的預設，且該重置有同步出去（切走切回仍是重置後的狀態）。
- [ ] 「繼續」的流程行為與改動前一致（`hasTarget` 為 false 時 disabled；按下後往 Settings 前進）。
- [ ] Values 欄四種型別都有內容，沒有整排「—」；日期字串與 CSV 一致。
- [ ] 卡片內沒有重複的「欄位設定」標題；表格貼齊邊框；按鈕列沒有黏邊；卡片內部捲動與 sticky 表頭仍正常。
- [ ] `npm run build` 通過，且改動過的檔案沒有新增 lint 錯誤。
- [ ] `.claude/ux-issues.md` 的三個項目都已回填。
