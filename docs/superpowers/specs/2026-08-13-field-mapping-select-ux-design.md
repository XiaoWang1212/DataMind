# 欄位對齊下拉選單 UX 修正 Design Spec

## 背景

欄位對齊頁（`FieldMappingView.vue`）左側對映表有三欄：論文變數、你的欄位（`CustomSelect` 下拉選單）、狀態。實際使用時出現兩個問題：

1. **已被占用的欄位選項看不出來**：`optionsFor()`（`FieldMappingView.vue:375-392`）已經會把「被別的論文變數占用的使用者欄位」標上 `hint: '已對應至 XXX'`，但目前只在選項下方多一行小灰字，選項本身文字顏色跟未占用的選項一樣，掃過選單時不容易一眼分辨。
2. **文字過長時版面被撐開**：`.mapping-table` 沒有設 `table-layout: fixed`，瀏覽器在 auto layout 下計算欄寬時，會用儲存格內文字「完整換算後的寬度」去撐開該欄——即使已經寫了 `text-overflow: ellipsis`，只要文字是 `white-space: nowrap`，這個完整寬度仍然會被算進欄寬計算。實際後果：
   - 左側「論文變數」欄（`.var-name`）目前完全沒有截斷邏輯，過長的變數名稱會撐開該欄
   - `CustomSelect` 收合狀態顯示的已選欄位名稱（`.cs-label`）雖然已經有 `overflow:hidden` + `ellipsis` 的 CSS，但因為外層 table 欄寬沒鎖死，同樣會被撐開
   - 兩者都會擠壓右側固定寬度的「狀態」欄，導致狀態標籤被迫換行或變形

## 範圍

- `CustomSelect.vue`：新增選項弱化顯示能力
- `FieldMappingView.vue`：套用弱化顯示、修正表格版面撐開問題
- 不動欄位對映的資料邏輯（`applySelection`/`optionsFor` 的配對規則不變，只加一個新旗標）
- 不影響 `CustomSelect` 在其他頁面（`DataTablePanel.vue`、`SettingsPanel.vue`、`FeatureImportancePanel.vue`）的使用——那些呼叫端都沒有傳 `hint`，新增的 `muted` 是選填欄位，預設不啟用

## 設計

### 1. 已被占用的選項弱化顯示

`CustomSelect.vue` 的 `Option` 介面新增 `muted?: boolean`（跟 `hint` 分開的獨立語意欄位，只代表「文字要弱化」，不綁定「有 hint 就要弱化」，避免未來其他頁面用 `hint` 做別的用途時被連帶影響樣式）。

```ts
interface Option { value: string, label: string, hint?: string, disabled?: boolean, muted?: boolean }
```

- `<li class="cs-option">` 的 class binding 加 `'is-muted': opt.muted`
- CSS 新增：

```css
.cs-option.is-muted .cs-option-label {
  color: #94a3b8; /* 沿用 .cs-option.is-disabled 的灰階色號 */
}
```

- 維持可點擊（不加 `cursor: not-allowed`、不擋 `@click`）：選了會照現有邏輯把欄位從原本的論文變數手上搶過來，這個行為不變，只是視覺上先提示「這個已經有人用了」

`FieldMappingView.vue` 的 `optionsFor()` 在組 `taken` 欄位時，同時給 `hint` 和 `muted: true`：

```ts
const options = userColumns.value.map(column => ({
  value: column.name,
  label: column.name,
  hint: taken.has(column.name) ? `已對應至 ${taken.get(column.name)}` : undefined,
  muted: taken.has(column.name),
}))
```

### 2. 表格欄寬鎖定 + 文字截斷

**`.mapping-table` 加 `table-layout: fixed`**，並把兩個側欄的固定 px 寬度改成「比例寬 + px 下限」，這樣視窗變寬時三欄能跟著比例縮放，不會讓側欄停在固定大小、把多出來的空間都丟給論文變數欄；縮到很窄時卡在下限，觸發水平捲動（`.mapping-scroll` 本來就有 `overflow-x: auto`），不會硬擠壓文字：

```css
.mapping-table {
  table-layout: fixed;
}

.col-col {
  width: 38%;
  min-width: 260px; /* 原本的固定值改當下限 */
}

.col-status {
  width: 18%;
  min-width: 124px; /* 原本的固定值改當下限 */
}

/* .col-var 不特別設寬，table-layout:fixed 底下自動吃掉剩餘空間 */
```

**`.var-name` 加上截斷邏輯**。目前 `★ 徽章 + 變數名 + ℹ️ 圖示` 是行內排列，沒有 flex 容器沒辦法正確裁切一個成員的寬度，需要包一層 flex 容器（做法比照既有的 `.status-cell`）：

```html
<td class="col-var">
  <div class="var-name-row">
    <span v-if="isTarget(item)" ...>★</span>
    <span class="var-name" :title="item.paper_variable">{{ item.paper_variable }}</span>
    <v-tooltip v-if="item.definition" ...>...</v-tooltip>
  </div>
  <span class="var-type">{{ item.required_type || '型態未指定' }}</span>
</td>
```

```css
.var-name-row {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.var-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

`.var-name` 加原生 `title` 屬性，滑鼠移上去可看完整名稱（不用另外做元件）。

**`CustomSelect.vue` 不需要改動**：`.cs-label` 原本的 `overflow:hidden; text-overflow:ellipsis; white-space:nowrap` 已經是對的寫法，先前失效純粹是因為外層表格沒鎖死欄寬；`table-layout: fixed` 生效後這段 CSS 就會正常截斷收合狀態的已選欄位名稱。

## 錯誤處理 / 相容性

- `muted` 是選填欄位，其他頁面呼叫 `CustomSelect` 沒傳就是 `undefined`，樣式不受影響
- target 變數（★ 徽章那列）一樣會被截斷；`title` 屬性同樣涵蓋，不用特別處理
- 這是純前端顯示層修正，不影響 `applySelection`/`optionsFor` 既有的搶欄位、鎖定等邏輯

## 測試

- 前端無 vitest，一律用 `npm run type-check` + 人工瀏覽器驗證：
  - 建一個論文變數名稱很長（例如超過 20 個字元）的框架，走到欄位對齊頁，確認左側文字被截斷成「...」，滑鼠移上去看得到完整名稱，狀態欄不被擠壓
  - 選取一個使用者欄位給某個論文變數後，打開另一個論文變數的下拉選單，確認該欄位選項文字變灰、仍可點擊選取（選取後會搶欄位，原本那列變回「未對應」）
  - 用一個欄位名稱很長的資料集測試，確認選取後收合狀態的 `CustomSelect` 顯示會正確截斷、不擠壓狀態欄
  - 縮放瀏覽器視窗寬度，確認「你的欄位」「狀態」兩欄會隨視窗比例縮放，縮到很窄時整張表水平捲動而不是把文字擠爆
