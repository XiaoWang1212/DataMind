# Hub 外殼色彩套用設計

## 背景

[2026-07-29-color-theme-refresh-design.md](2026-07-29-color-theme-refresh-design.md) 完成後，使用者反映「改完顏色後沒有什麼太大區別，底色也長得差不多」。

調查發現根因：上一輪任務範圍明確限定在「全域 design token + 已經在用 token 系統的地方」，但專案裡有 **38 個檔案**直接寫死顏色 hex 碼，完全沒有接上 token 系統，改 token 對這些地方零效果。其中影響最大的兩個：

- `frontend/src/layouts/HubLayout.vue`：`.hub-wrap` 背景寫死 `#f5f5f5`，跟新的主色 `#f6f5f2` 是兩個毫不相干的顏色，只是剛好都很淺，肉眼幾乎分不出來
- `frontend/src/components/hub/HubSidebar.vue`：整個側邊欄（每個 Hub 頁面都看得到）的背景、文字色、選中狀態強調色全部寫死，選中項目用的是舊藍色 `#2347c5`，完全沒有換成新的琥珀色 `accent`

這兩個檔案構成 Hub 區域（儀表板、框架庫、專案、設定）的常駐外殼，是使用者最常看到的畫面，因此是本輪修復的第一優先。

## 目標

把 `HubLayout.vue` 與 `HubSidebar.vue` 裡寫死的顏色改成引用 `frontend/src/styles/tailwind.css` 已定義的 `--color-*` CSS 變數（primary/secondary/accent/surface/ink/inverted），讓這兩個最常密見的外殼元件真正套用新色調。

## 非目標

- 不處理其餘 36 個仍寫死顏色的檔案（`HelloWorld.vue` 首頁英雄區、`PaperPage.vue` 局部樣式、`WorkflowBuilder.vue`/`WorkflowCanvas.vue`/各 node panel、`hub/*View.vue` 各頁面內容區等）——這些留給後續批次，各自需要獨立盤點
- 不改動中性 UI 邊框色與輔助說明文字色（如 `#9ca3af` 淡灰說明文字、`#e5e7eb`/`#f0f0f0` 邊框線）——這些是通用灰階，不是品牌色，維持原樣以避免範圍不必要擴大
- 不改動側邊欄的排版、間距、互動邏輯（展開/收合等）
- 不新增 dark mode 支援

## 色彩對照

沿用既有 `<style scoped>` 結構，把寫死的 hex 碼改成 `var(--color-*)` 引用（`--color-*` 變數已由上一輪任務定義在 `frontend/src/styles/tailwind.css` 的 `@theme` 區塊，任何一般 CSS 都能透過 `var()` 直接使用，不限於 Tailwind utility class）。

### `HubLayout.vue`

| 位置 | 現在 | 改成 |
|---|---|---|
| `.hub-wrap` 背景 | `#f5f5f5` | `var(--color-primary)` |
| `.hub-wrap` 文字色 | `#111827` | `var(--color-ink)` |

### `HubSidebar.vue`

| 位置 | 現在 | 改成 |
|---|---|---|
| `.hub-sidebar` 背景 | `#ffffff` | `var(--color-surface)` |
| `.hub-brand-title` 文字 | `#111827` | `var(--color-ink)` |
| `.hub-nav-item` 文字 | `#4b5563` | `var(--color-secondary)` |
| `.hub-nav-item:hover` 背景 | `#f5f5f5` | `var(--color-primary)` |
| `.hub-toggle-btn:hover` 背景 | `#f5f5f5` | `var(--color-primary)` |
| `.hub-nav-item--active` 背景 | `#2347c5` | `var(--color-accent)` |
| `.hub-nav-item--active` 文字 | `#ffffff` | `var(--color-ink)` |

**對比度考量**：`.hub-nav-item--active` 原本是白字配舊藍色背景，白字對比度足夠。換成 `accent`（`#e8a33d`，中亮度琥珀色）後若維持白字，對比度只剩約 2.25:1，遠低於 WCAG AA 文字對比標準（4.5:1）；改用 `ink`（深色文字）則對比度約 7.1:1，達 AAA 等級。因此選中項目的文字色明確從白字改為 `ink`，這是刻意的無障礙修正，不是延續原設計。

**維持不動**（避免範圍擴大）：`.hub-brand-sub` 淡灰說明文字（`#9ca3af`）、`.hub-toggle-btn` 邊框（`#e5e7eb`）、`.hub-sidebar-footer` 文字與邊框（`#9ca3af` / `#f0f0f0`）——這些是中性 UI 邊框/輔助文字色，不是品牌色。

## 驗證方式

- `npm run build`（`vue-tsc --build --force` + `vite build`）確認無編譯錯誤
- `npm run lint` 確認沒有在這兩個檔案新增 lint 錯誤
- 瀏覽器 devtools：對 `.hub-wrap`、`.hub-sidebar` 元素跑 `getComputedStyle(...).backgroundColor`，確認分別解析為 `rgb(246,245,242)`（primary）與 `rgb(255,255,255)`（surface）
- 瀏覽器 devtools：點擊任一側邊欄導覽項目使其進入 active 狀態，確認 `.hub-nav-item--active` 的 `backgroundColor` 為 `rgb(232,163,61)`（accent）、`color` 為 `rgb(28,33,48)`（ink），而非白色
