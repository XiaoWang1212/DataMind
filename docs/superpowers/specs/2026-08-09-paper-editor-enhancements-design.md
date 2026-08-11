# 論文編輯器增強設計

## 背景

論文編輯頁（`PaperEditor.vue`）目前已經有基本的富文字編輯功能（粗體/斜體/底線/刪除線、標題、清單、表格插入、圖片、圖表），但使用上有幾個缺口：

1. 使用者在欄位對應階段（`FieldMappingView.vue`）已經整理過「論文變數 → 使用者資料欄位」的對應關係，但寫論文時想在內文放一張「變數說明表」得自己手動重打一次，沒有快速帶入的方式
2. 工具列的「刪除線」圖示是 MDI 的抽象幾何圖形，跟粗體(B)、斜體(I)、底線(U)這幾顆「字母造型」圖示風格不一致，使用者看不出來這顆按鈕是做什麼的
3. 表格功能只有「插入表格」「新增/刪除列」「新增/刪除欄」，缺少合併儲存格、儲存格底色、欄列插在前面、刪除整個表格這幾個基本操作
4. 順帶發現：工具列的「底線」按鈕呼叫 `toggleUnderline()`，但 `@tiptap/extension-underline` 套件並未安裝（Tiptap v3 的 StarterKit 已不含 Underline），這顆按鈕目前很可能沒有作用

## 目標

1. 論文編輯器新增「插入變數表格」功能：讀取該專案已確認的欄位對應資料，一鍵在內文插入「變數名稱 / 定義 / 型別」三欄表格
2. 把刪除線圖示換成跟 B/I/U 同樣風格的「字母＋刪除線」圖示
3. 表格工具列補上：合併/拆分儲存格、儲存格底色、新增列/欄插在前面、刪除整個表格
4. 修正 Underline 擴充套件缺失的問題，讓「底線」按鈕真正可用

## 非目標

- 不做「定義」欄位的自動填入——目前系統完全沒有變數定義文字的資料來源，插入表格時這欄一律留空，由使用者自己在文中手動填寫
- 不做通用文字顏色、螢光筆、數學公式、智慧排版、選取浮動工具列（BubbleMenu）等其他 Tiptap 功能——這些跟這次的三個需求無關，列為未來可能的獨立需求
- 儲存格底色不做完整調色盤，只提供幾個跟專案配色一致的預設色

## 設計

### 段落 A：資料流變更——欄位對應結果保留型別資訊

`backend/models/project.py` 的 `column_mapping`（JSONB）欄位不需要改 schema，但前端存入的**內容格式**要改：

現況（`frontend/src/api/project.ts` 的 `ProjectDTO.columnMapping` / `UpdateProjectPatch.columnMapping`）：
```ts
columnMapping?: Record<string, string>   // { "AGE": "age_years", ... }
```

改為：
```ts
export interface VariableMapping {
  column: string   // 對應到的使用者資料欄位名稱
  type: string      // 對應 FieldMappingView 的 required_type
}

columnMapping?: Record<string, VariableMapping>
// { "AGE": { column: "age_years", type: "numerical" }, ... }
```

`FieldMappingView.vue` 呼叫 `updateProject(projectId, { columnMapping, variables })` 的地方，組裝 `columnMapping` 時要把 `item.required_type` 一起存進去，而不是只存 `matched_user_column`。

既有讀取 `columnMapping` 的地方（`ProjectDetailView.vue`、`ProjectsView.vue`）目前都只檢查 `columnMapping == null` 來判斷「有沒有做過欄位對應」，不會因為值的內部結構改變而壞掉，不需要修改。

### 段落 B：新增單一專案查詢 API

後端目前只有 `GET /api/projects`（列表）跟 `PATCH /api/projects/<id>`，沒有取得單一專案的端點。新增：

```
GET /api/projects/<id>
```

行為比照既有的 `list_projects()`：用 `_serialize_project()` 序列化、`@login_required`、只能查詢屬於目前使用者的專案（查不到或不屬於自己回 404）。

前端 `frontend/src/api/project.ts` 新增對應的 `getProject(id: number): Promise<ProjectDTO>`。

### 段落 C：插入變數表格

`PaperEditor.vue` 工具列在「插入表格」按鈕旁邊新增「插入變數表格」按鈕（`icon="mdi-table-account"` 或類似圖示）：

- 點擊時用 `projectId`（元件既有的 prop）呼叫 `getProject(projectId)`，取得 `columnMapping`
- 若 `columnMapping` 為空／專案還沒做過欄位對應，按鈕停用（`disabled`），`data-tooltip` 顯示「尚未完成欄位對應」
- 有資料時，組出一個 3 欄 HTML 表格字串（表頭：`變數名稱` / `定義` / `型別`；每個變數一列，`定義` 欄留空），透過 `editor?.chain().focus().insertContent(html).run()` 插入游標位置——沿用 Table 擴充套件既有的渲染方式，不需要新的套件

### 段落 D：刪除線圖示

新增一個小型元件 `frontend/src/components/paper/StrikethroughIcon.vue`：置中顯示字母「S」，中間疊一條橫線（用 CSS `text-decoration: line-through` 或一個簡單的 inline SVG 都可以），大小跟 `v-icon size="small"` 的其他按鈕一致。`PaperEditor.vue` 的刪除線按鈕改用這個元件取代 `icon="mdi-format-strikethrough"`，視覺風格會跟 B/I/U 一致。

### 段落 E：表格功能增強

都是 Tiptap Table 擴充套件既有的指令，工具列補按鈕即可，不需要新裝套件（除了儲存格底色）：

- **合併儲存格**：選取多個儲存格時顯示（`editor?.can().mergeCells()` 為 true 才顯示），呼叫 `editor?.chain().focus().mergeCells().run()`
- **拆分儲存格**：游標在合併過的儲存格時顯示（`editor?.can().splitCell()` 為 true 才顯示），呼叫 `splitCell()`
- **新增列/欄插在前面**：在現有「新增列」「新增欄」按鈕旁各加一顆，呼叫 `addRowBefore()` / `addColumnBefore()`
- **刪除整個表格**：`editor?.isActive('table')` 時顯示，呼叫 `deleteTable()`
- **儲存格底色**：擴充 `TableCell`、`TableHeader` 兩個擴充套件，各自用 `addAttributes()` 加一個 `backgroundColor` 屬性（對應 `style="background-color: ..."`，會隨內容 JSON 一起存檔／讀檔）。工具列加一顆「儲存格底色」按鈕，點開小色盤選單，提供 4-5 個跟專案配色一致的預設色（橘、灰藍、淡黃、淡綠、無底色），呼叫 `editor?.chain().focus().setCellAttribute('backgroundColor', color).run()`

### 段落 F：修正 Underline 套件缺失

`frontend/package.json` 新增 `@tiptap/extension-underline`；`PaperEditor.vue` 的 extensions 陣列加入 `Underline`。「底線」按鈕程式碼不需要改，問題純粹是套件沒裝。

## 驗證方式

- `npm run type-check` / `npm run build` 確認無編譯錯誤
- 手動在瀏覽器測試：
  - 完成一次欄位對應後，到論文編輯頁點「插入變數表格」，確認表格內容（變數名稱、型別）正確、定義欄是空的
  - 沒做過欄位對應的專案，按鈕應該是停用狀態
  - 點刪除線按鈕，確認圖示變成 S̶ 造型，功能仍正常（選字後套用刪除線）
  - 點底線按鈕，確認選取文字真的有加底線（修正前的 bug）
  - 表格內選多個儲存格測試合併、合併後測試拆分
  - 測試新增列/欄插在前面、刪除整個表格、儲存格底色
  - 儲存論文後重新整理頁面，確認表格底色、合併儲存格狀態都有正確存回來
