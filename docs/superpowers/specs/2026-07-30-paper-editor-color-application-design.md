# 論文編輯區色票套用設計

## 背景

[2026-07-29-color-theme-refresh-design.md](2026-07-29-color-theme-refresh-design.md) 與 [2026-07-30-hub-shell-color-application-design.md](2026-07-30-hub-shell-color-application-design.md) 已經完成全域 design token 定義與 Hub 外殼的套用，但盤點發現全專案仍有約 38 個檔案直接寫死顏色、沒有接上 token 系統。這是第二批，範圍鎖定「論文編輯區」（`PaperPage.vue`、`PaperEditor.vue`、`InsertChartDialog.vue` 等），因為檔案數最少（約 8 個）、使用頻率高，而且上一輪才剛修過這區的其他 bug，程式碼比較熟悉。

## 目標

- `PaperPage.vue` 的本地 CSS 變數（`--page-bg`、`--card-bg`、`--text-main`、`--text-secondary`、`--brand`）改為引用全域 `--color-*` token，取代寫死的舊藍色系配色
- `PaperPage.vue` 的裝飾性漸層背景（光暈+點陣）簡化成實心 token 背景，與其他頁面風格統一
- `PaperEditor.vue` 的編輯器工具列背景與內文/標題文字色改用 token
- `InsertChartDialog.vue` 畫面上（非匯出內容）的說明文字色改用 token

## 非目標

- **`BarChart.vue`、`RadarChart.vue` 全部維持不動**，`InsertChartDialog.vue` 裡 `handleInsert()` 組出的匯出 SVG 字串（含圖例顏色 `fill="#4a4f5c"`）也維持寫死 hex 碼——這些會被序列化成獨立的 SVG 圖片插入論文內容，脫離 App 的 DOM 後讀不到 `:root` 定義的 CSS 變數，用 `var()` 會直接讓顏色失效。這是專案先前已經踩過的坑，此次刻意避開
- `CitationPopover.vue` 整個維持不動，以及 `PaperEditor.vue` 裡的引文高亮色（`.citation-mark` 的 `#fdf0a8`/`#fae57e`）——這是刻意設計的「黃色螢光筆」引文標記主題，獨立於品牌色之外，性質類似 warning 色
- `--line`、`--line-soft`（`PaperPage.vue`）以及 `PaperEditor.vue`/`InsertChartDialog.vue` 裡的中性邊框灰階色不處理——這些是結構性分隔線，不是品牌色
- 不處理 Workflow 工作流區、Hub 各頁面內容區（留給後續批次）
- 不改動 `ModeSwitch.vue` 本身——它透過 `var(--brand, ...)`、`var(--text-secondary, ...)` 讀取 `PaperPage.vue` 定義的變數，改完段落 A 會自動連帶生效，不需要碰這個檔案

## 設計

### 段落 A：`PaperPage.vue` 本地變數

```css
/* 現在 */
.paper-page {
  --page-bg: #e4e4e8;
  --card-bg: #ffffff;
  --line: #d8dbe3;
  --line-soft: #e8ebf1;
  --text-main: #15181e;
  --text-secondary: #6f7480;
  --brand: #1058d6;
  background:
    radial-gradient(circle at 8% 12%, rgba(99, 146, 238, 0.18) 0%, transparent 38%),
    radial-gradient(circle at 91% 89%, rgba(88, 157, 255, 0.16) 0%, transparent 30%),
    linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%);
}
.paper-main {
  background:
    radial-gradient(circle, #cdd0d8 1px, transparent 1px) 0 0 / 18px 18px,
    linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%);
}
```

```css
/* 改為 */
.paper-page {
  --page-bg: var(--color-primary);
  --card-bg: var(--color-surface);
  --line: #d8dbe3;
  --line-soft: #e8ebf1;
  --text-main: var(--color-ink);
  --text-secondary: var(--color-secondary);
  --brand: var(--color-accent);
  background: var(--color-primary);
}
.paper-main {
  background: var(--color-surface);
}
```

`--line`/`--line-soft` 維持寫死不變。`.paper-main` 原本的點陣裝飾背景整個移除，改用實心 surface 背景。

`ModeSwitch.vue` 的 pill（選中狀態指示條）目前是 `background: var(--brand, #1058d6)`，`--brand` 改成 `var(--color-accent)` 後，pill 會自動變成新的琥珀色，不用改 `ModeSwitch.vue` 本身。

### 段落 B：`PaperEditor.vue`

```css
/* 現在 */
.editor-toolbar {
  background: #f7f8fb;
}
:deep(.editor-content) {
  color: #2a2f3a;
}
:deep(.editor-content h1),
:deep(.editor-content h2),
:deep(.editor-content h3) {
  color: #1c2130;
}
```

```css
/* 改為 */
.editor-toolbar {
  background: var(--color-surface);
}
:deep(.editor-content) {
  color: var(--color-ink);
}
:deep(.editor-content h1),
:deep(.editor-content h2),
:deep(.editor-content h3) {
  color: var(--color-ink);
}
```

`.editor-toolbar` 的邊框 `#d8dbe3`、表格邊框 `#d8dbe3`、引文高亮色 `#fdf0a8`/`#fae57e` 維持不變。

### 段落 C：`InsertChartDialog.vue`

```css
/* 現在 */
.empty-hint {
  color: #6f7480;
}
.picker-label {
  color: #4a4f5c;
}
```

```css
/* 改為 */
.empty-hint {
  color: var(--color-secondary);
}
.picker-label {
  color: var(--color-secondary);
}
```

`handleInsert()` 函式裡組出匯出 SVG 字串的 `fill="#4a4f5c"` 維持寫死不變（見上方非目標說明）。

## 驗證方式

- `npm run build` 確認無編譯錯誤
- 瀏覽器開啟 `/paper`，用 devtools 確認 `.paper-page`/`.paper-main` 背景色、`.editor-toolbar` 背景色、內文與標題文字色都正確解析為新 token 的 RGB 值
- 確認 `ModeSwitch` 選中狀態的 pill 顏色變成新的琥珀色（不用改 `ModeSwitch.vue` 就該生效）
- 確認引文高亮（點擊引文標記）與 `CitationPopover` 彈出卡片維持原本的黃色螢光筆配色，未被誤改
- 開啟「插入圖表」對話框，確認說明文字用新色票；實際插入一張圖表到論文內容,確認匯出的圖表圖片格線/座標軸/圖例顏色不受影響、依然正常顯示（驗證匯出 SVG 沒有被誤改成 `var()`）
