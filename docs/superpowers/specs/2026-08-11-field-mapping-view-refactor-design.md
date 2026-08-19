# FieldMappingView 重構：拆成元件與 composable

## 背景

`frontend/src/views/hub/FieldMappingView.vue` 有 1381 行（template 224 行、script 610 行、style 543 行），是全專案最大的檔案。它把六種不相干的職責混在同一個檔案裡：對映表格、資料預覽、AI 對話面板、undo/redo 快照、localStorage 草稿、以及頁面層級的載入與送出流程。

檔案大小本身不是 bug——功能都正常，寫法也是現代 Vue（`<script setup>` + TypeScript strict）。問題是維護成本：要改對映表格的一個樣式，得在 1381 行裡找；要理解 undo/redo 怎麼運作，得先跳過幾百行畫面程式碼。

## 目標

- 把檔案拆成數個各有單一職責的檔案，每個都能單獨讀懂
- **行為完全不變**——這是重構，不是重新設計。使用者看到的畫面與互動結果必須與拆分前一致
- 拆完後的邊界也讓之後套用設計系統（改樣式）時比較好下手，但這是附帶效果，不是切邊界的依據

## 非目標

- **不改任何視覺樣式**。CSS 只是換檔案放，不調整數值
- **不改頁面位置**。`views/hub/` 是正確的位置：Hub 底下「深入某個 project 做一件事」的頁面（`CreateProjectView`、`ExtractFrameworkView`、`ProjectDetailView`、`ResultView`）都有相同的 `back-link` 返回模式，欄位對映是建立 project 流程的一環，屬於同一類，抽成獨立 view 反而會打破既有規律
- **不啟用 `features/` 目錄**。`frontend/src/README.md` 描述了 `features/`、`app/`、`services/` 的功能導向架構，但這三個目錄實際上不存在，現況是依類型分層。要不要改成功能導向是全專案的架構決策，不該夾在這次重構裡順手做掉
- **不處理其他過大檔案**。`WorkflowWorkspace.vue`(972)、`SettingsPanel.vue`(808)、`WorkflowOptionsPanel.vue`(802)、`DataTablePanel.vue`(768)、`ResultView.vue`(766) 之後可以照這次確立的規則各自排，每支都是獨立可驗收的工作

## 檔案結構

| 動作 | 路徑 | 職責 |
|---|---|---|
| 新增 | `components/hub/fieldMapping/MappingTable.vue` | 對映表格：每列的變數名、下拉選單、候選 chip、狀態徽章與操作按鈕 |
| 新增 | `components/hub/fieldMapping/DatasetPreview.vue` | 資料預覽表（前 N 筆） |
| 新增 | `components/hub/fieldMapping/MappingChatPanel.vue` | AI 對話面板：訊息串、輸入框、送出 |
| 新增 | `composables/fieldMapping/useMappingHistory.ts` | undo/redo 快照堆疊與鍵盤快捷鍵 |
| 新增 | `composables/fieldMapping/useMappingDraft.ts` | localStorage 草稿存讀 |
| 修改 | `views/hub/FieldMappingView.vue` | 協調者 |
| 修改 | `types/fieldMapping.ts` | 新增 `SKIP_VALUE` 常數 |

目錄位置沿用既有慣例：元件放在 `components/hub/` 底下開子資料夾（比照 `components/workflow/nodePanel/`），composable 開子資料夾（比照 `composables/workflow/`）。

`SKIP_VALUE`（下拉選單「資料表中沒有此變數」的哨兵值，目前是 page 內的區域常數）移到 `types/fieldMapping.ts`，因為拆分後 page（`applySelection` 判斷）與 `MappingTable`（`optionsFor`/`selectionKey`）都需要它。該檔案的開頭註解已經在說明 `SKIPPED` 狀態的語意，放在一起是內聚的。

## 元件介面

三個元件一律 props down / emits up，**子元件不修改 props**——所有資料變更都由 page 執行。這是行為不變的關鍵：變更邏輯不搬家，只是改由 emit 觸發而非直接呼叫。

### `MappingTable.vue`

```ts
props: {
  items: MappingItem[]        // 未排序的原始陣列
  userColumns: UserColumn[]
  targetName: string
  flashed: Set<string>        // 需要閃爍提示的變數名
}
emits: {
  'update:selection': [item: MappingItem, value: string]   // value 為欄位名或 SKIP_VALUE
  'confirm': [item: MappingItem]
  'unconfirm': [item: MappingItem]
}
```

元件內部持有這些純衍生邏輯（都只依賴 props，不需要 page 傳進來）：target 置頂的排序、`optionsFor`、`selectionKey`、`isTarget`、`STATUS_LABEL`、`STATUS_HINT`。

**樣式要帶走兩個區塊**：表格自己的 scoped CSS，以及檔案末端那個非 scoped 的全域區塊（`FieldMappingView.vue:1375-1381`）。後者存在的原因是 `v-tooltip` 會 teleport 到元件外，scoped 樣式管不到——它是表格的 tooltip，必須跟著表格走。SFC 允許同時有 scoped 與非 scoped 兩個 `<style>` 區塊。

### `DatasetPreview.vue`

```ts
props: { columns: string[], rows: string[][] }
```

沒有 emits，純呈現。

### `MappingChatPanel.vue`

```ts
props: {
  history: ChatMessage[]
  pending: boolean
  available: boolean     // 目前的 aiAvailable
  loading: boolean
}
emits: { 'send': [message: string] }
```

元件內部持有：草稿文字、textarea ref、自動長高、Enter 送出（Shift+Enter 換行、輸入法組字中不送出）、捲到底、開場白常數 `CHAT_OPENER`。

**這是行為實作上唯一有實質搬動的地方**：目前「清空輸入框、重設 textarea 高度、捲到底」由 page 的 `sendMessage` 執行；拆分後改由面板自己做——清空與重設高度在 emit 送出時做，捲到底改成監看 `history` 長度與 `pending` 變化。使用者看到的結果一致（送出後輸入框清空回單行、訊息捲到最新一則），但實作位置從 page 移到元件內。這樣切是因為那些都是面板自己的 DOM，page 不該伸手進去操作子元件的內部元素。

## Composable 介面

### `useMappingHistory({ items, locked, onRestore })`

```ts
export function useMappingHistory (deps: {
  items: Ref<MappingItem[]>
  locked: Ref<Set<string>>
  onRestore: () => void
}): { pushHistory: () => void }
```

包含快照堆疊（上限 50）、`snapshot`/`restore`、`undo`/`redo`、鍵盤監聽（Ctrl+Z、Ctrl+Shift+Z、Ctrl+Y，焦點在 input/textarea/contenteditable 時不攔截），以及自己的 `onMounted`/`onBeforeUnmount` 註冊與解除（目前在 `FieldMappingView.vue:769-770`）。

`onRestore` 是還原後的回呼，page 傳入「清掉 `saveError` + 存草稿」。這樣 composable 不需要知道草稿或錯誤訊息的存在。

回傳只有 `pushHistory` 一個函式——undo/redo 由 composable 自己的鍵盤監聽觸發，page 不需要也不該直接呼叫。

快照必須同時包含 `items` 與 `locked`：現有程式碼有一段註解說明過原因（只還原 `items` 的話，那一列看起來回到未對應，但它還留在 `locked` 裡，之後所有 AI 建議都會被靜默忽略）。這個行為必須完整保留。

### `useMappingDraft({ projectId, items, locked, aiAvailable, userColumns })`

```ts
export function useMappingDraft (deps: {
  projectId: Ref<number>
  items: Ref<MappingItem[]>
  locked: Ref<Set<string>>
  aiAvailable: Ref<boolean>
  userColumns: Ref<UserColumn[]>
}): {
  saveDraft: () => void
  loadDraft: () => boolean
  clearDraft: () => void
}
```

包含 `draftKey`、`columnSignature`（換資料集後舊草稿失效的判斷依據）、以及三個對外函式。`loadDraft` 回傳是否成功載入，與現況一致。

## Page 留下什麼

- 路由參數（`projectId`）、`loading`/`loadError` 狀態
- 載入流程：`ensureStoresLoaded`、`buildPaperVariables`、`loadDataset`、`initFieldMapping` 呼叫、`onMounted` 主流程
- 所有會改動 mapping 資料的邏輯：`applySelection`、`confirmRow`、`unconfirmRow`、`confirmAll`、`applyActions`、`flash`
- `sendMessage`：這是協調函式（呼叫 API、推快照、改資料、存草稿、存聊天記錄），不是面板的職責
- `confirmAndRun`：改寫表頭後交給 workflow
- 頁面殼的 template 與 CSS：`back-link`、`page-header`（含進度與全部確認按鈕）、`load-error`、`mapping-layout`、`mapping-footer`、`confirm-btn`、`mapping-loading`

**預期結果**：page 從 1381 行降到約 450-500 行。它不會變得很小，因為協調本來就是它的工作，但它會只剩協調這一件事。其餘分散為 `MappingTable` ~450、`MappingChatPanel` ~300、`DatasetPreview` ~80、兩個 composable 合計 ~150。這些數字是預估，不是驗收門檻——驗收看的是職責是否切乾淨、行為是否不變。

## 驗收

專案沒有自動化測試，所以驗收是 `npm run build`（含 `vue-tsc` 型別檢查）通過、eslint 沒有新增問題，加上人工檢查清單。清單每一項都對應一個跨越新邊界的互動：

1. 下拉選單指定欄位 → 該列變「已確認」；若該欄位原本屬於另一列，原持有者退回「未對應」且該列閃爍提示
2. 下拉選「資料表中沒有此變數」→ 該列變「不使用」
3. 「可能是」候選 chip 一鍵選取
4. 待確認列的勾選按鈕 → 變已確認；已確認列的復原按鈕 → 退回待確認
5. 「全部確認」一次處理所有待確認列
6. Ctrl+Z 復原、Ctrl+Shift+Z 與 Ctrl+Y 重做；**焦點在聊天輸入框時打 Ctrl+Z 不會觸發表格復原**（應該是輸入框自己的復原）
7. 復原一個被 AI 改過的列後，該列能再次接受 AI 建議（驗證 `locked` 有跟著快照還原）
8. AI 對話送出訊息 → 套用建議、被改動的列閃爍；使用者手動確認過的列不被 AI 覆蓋
9. 送出後輸入框清空並回到單行高度、訊息捲到最新一則
10. 重新整理頁面 → 編輯中的對映還在（草稿）
11. 換一個資料集 → 舊草稿失效，重新自動配對
12. 「確認並執行」→ 依對映改寫表頭後跳轉 workflow
