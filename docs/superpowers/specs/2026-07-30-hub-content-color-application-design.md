# Hub 頁面內容區色票套用設計

## 背景

第一批（[2026-07-30-hub-shell-color-application-design.md](2026-07-30-hub-shell-color-application-design.md)）套用了 Hub 外殼（側邊欄/外層容器）的新色票；第二批（[2026-07-30-paper-editor-color-application-design.md](2026-07-30-paper-editor-color-application-design.md)）套用了論文編輯區。這是第三批，範圍是 `frontend/src/views/hub/` 底下 8 個頁面內容檔案：`DashboardView.vue`、`ProjectsView.vue`、`FrameworkLibraryView.vue`、`CreateProjectView.vue`、`ExtractFrameworkView.vue`、`SettingsView.vue`、`ProjectDetailView.vue`、`ResultView.vue`。

盤點發現這 8 個檔案的顏色高度一致（同一組色碼幾乎逐字複製到每個檔案），沒有內建局部 CSS 變數系統，可以直接全域替換。全部 8 檔共用的實質強調色目前是舊藍色 `#2347c5`（CTA 按鈕、選中狀態、focus 邊框，共 25+ 處），而不是新色票的琥珀色 `accent`。

另外發現 `ResultView.vue` 已經有一個「對話氣泡」UI（`.chat-bubble--user`/`.chat-bubble--model`），這正好是專案很早之前為未來聊天功能預先定義、但一直沒有實際使用者的 `--color-chat-user`/`--color-chat-system` token 的第一個真實用途。

## 目標

- 把全部 8 檔共用的 CTA/強調藍色（`#2347c5` 及其 hover 態）改成 `var(--color-accent)`
- 把主標題/次要說明等文字色改成 `var(--color-ink)`/`var(--color-secondary)`（含 `ResultView.vue` 自成一套但語意相同的灰階，套用相同語意對照後會自動與其他 7 檔統一）
- `ResultView.vue` 的對話氣泡改用 `--color-chat-user`/`--color-chat-system`/`--color-ink`/`--color-inverted`
- 順手統一成功綠、錯誤紅各自重複的兩個色碼（不套用品牌色，純粹合併重複值）

## 非目標

- 不處理中性邊框/分隔線灰階色（`#e8e8e8`、`#e5e7eb`、`#f0f0f0` 等）
- 不處理裝飾性功能圖示色塊（靠藍 `#4f46e5`/`#c7d2fe`、橘黃 `#f59e0b`/`#fed7aa`、靛紫等）——性質類似先前排除在外的圖表分類色盤，用於區分不同卡片類型,非品牌色
- 不處理 `.badge--running` 的琥珀警告色（狀態色，語意獨立於品牌色之外，剛好色相類似 accent 純屬巧合）
- 不處理 Workflow 工作流區（留給後續批次）
- 不新增聊天功能的其他部分（訊息傳送邏輯、AI 串接等），只套用既有 UI 的顏色

## 設計

### 段落 A：CTA / 強調色

所有 8 個檔案裡的 `#2347c5`（含 hover 態 `#1b3ca0`）→ `var(--color-accent)`；選中卡片/輸入框 focus 的淺藍底 `#f0f4ff` → `color-mix(in oklab, var(--color-accent) 12%, var(--color-surface))`。適用範圍包含所有 CTA 按鈕（`.new-btn`、`.upload-btn`、`.use-btn`、`.next-btn`、`.extract-btn`、`.save-btn`、`.open-workflow-btn`、`.chat-send-btn` 等）、`.step-circle--active/done`、`.fw-card--selected`/`.fw-select-card--selected` 邊框、`.drop-zone--over` 背景。

`ProjectsView.vue`/`ProjectDetailView.vue` 的 `.badge--completed` 目前用同一個藍色 `#2347c5`/`#1d4ed8` 當「已完成」狀態的文字色——這個維持藍色系（狀態色，不隨 CTA 一起改成 accent），只統一成同一個色碼避免兩檔不一致（見段落 D）。

### 段落 B：文字色

| 現在 | 改成 | 出現範圍 |
|---|---|---|
| `#111827` | `var(--color-ink)` | 全 8 檔的主標題、統計數字等 |
| `#9ca3af` | `var(--color-secondary)` | 全 8 檔的次要說明文字 |
| `#6b7280` / `#374151` | `var(--color-secondary)` | ProjectsView、FrameworkLibraryView、CreateProjectView、ProjectDetailView、ExtractFrameworkView 的中層文字 |
| `#20232a` / `#2a2f39` / `#1f2532`（僅 ResultView） | `var(--color-ink)` | ResultView 專屬灰階，套用同語意對照後自動與其他 7 檔統一 |
| `#4b5160` / `#6f7480`（僅 ResultView） | `var(--color-secondary)` | 同上 |

`#9ca3af` 明顯比 `--color-secondary`（`#334155`）淺很多，套用後次要文字會變得更深、更醒目——這是刻意的視覺變化，已與使用者確認。

### 段落 C：ResultView 對話氣泡

```css
/* 現在 */
.chat-bubble--user {
  background: #2347c5;
  color: #ffffff;
}
.chat-bubble--model {
  background: #f4f5f8;
  color: #1f2532;
}
```

```css
/* 改為 */
.chat-bubble--user {
  background: var(--color-chat-user);
  color: var(--color-inverted);
}
.chat-bubble--model {
  background: var(--color-chat-system);
  color: var(--color-ink);
}
```

`.chat-bubble--failed` 的錯誤外框 `#d64545`、`.chat-bubble-failed-hint` 文字 `#ffd7d7` 屬於狀態色，處理方式見段落 D（統一色碼,不套用品牌色）。`.chat-send-btn` 是 CTA 按鈕,併入段落 A 一起改成 accent，不使用 chat-user token（氣泡背景代表「這是使用者的訊息」的身分色，送出按鈕是操作型 CTA，兩者语意不同,分開處理）。

### 段落 D：狀態色色碼統一（不套用品牌色）

| 狀態 | 現在（兩個不同色碼） | 統一為 |
|---|---|---|
| 成功 | `#16a34a`（SettingsView）／`#18a836`（ResultView） | `#16a34a` |
| 錯誤 | `#ef4444`/`#b91c1c`（ExtractFrameworkView）／`#d64545`（ResultView） | `#ef4444` |

`.badge--completed` 的藍色系（`#2347c5`/`#1d4ed8`）統一為 `#2347c5`。這些都只是合併重複色碼，不是套用品牌 token。

## 驗證方式

- `npm run build` 確認無編譯錯誤
- 逐一開啟 8 個頁面（`/hub/dashboard`、`/hub/projects`、`/hub/library`、`/hub/projects/new`、`/hub/library/extract`、`/hub/settings`、`/hub/projects/:id`、`/hub/projects/:id/result`），用 devtools 抽查幾個 CTA 按鈕與標題文字確認顏色正確解析為新 token
- `/hub/projects/:id/result` 頁面確認對話氣泡：使用者訊息顯示深色底淺色字（chat-user/inverted）、系統回覆顯示淺色底深色字（chat-system/ink）
- 確認裝飾性圖示色塊、中性邊框、`badge--running` 警告色維持原樣未被誤改
