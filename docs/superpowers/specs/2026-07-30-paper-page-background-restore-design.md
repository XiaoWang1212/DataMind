# PaperPage 裝飾性背景復原（重新配色）

## 背景

[2026-07-30-paper-editor-color-application-design.md](2026-07-30-paper-editor-color-application-design.md) 把 `PaperPage.vue` 的裝飾性漸層背景（兩個模糊光暈 + 點陣圖案，藍灌色系）簡化成實心 `primary`/`surface` 背景。使用者事後決定想保留原本的裝飾形式，只是顏色要換成新色票，而不是完全拿掉。

## 目標

把 `.paper-page`、`.paper-main` 的光暈與點陣裝飾效果加回來,形狀、位置、大小維持原本數值，顏色改用新色票（`--color-accent`、`--color-secondary`）取代舊的藍灌色，並疊在 Task 1 已套用的 `primary`/`surface` 實心底色之上。

## 非目標

- 不改變光暈的位置（`8% 12%`、`91% 89%`）、大小（`38%`、`30%`）、點陣間距（`18px`）等既有數值
- 不影響 `PaperPage.vue` 其他部分（本地變數、文字色等，已在上一輪完成）

## 設計

沿用專案已建立的 `color-mix()` 技巧（跟 Hub 側邊欄 hover 修正同一套手法），把舊的 `rgba(99, 146, 238, ...)` 藍色光暈換成淡琥珀色（`--color-accent`），點陣改用淡灰藍色（`--color-secondary`）：

```css
/* .paper-page 背景（現在） */
background: var(--color-primary);

/* 改為 */
background:
  radial-gradient(circle at 8% 12%, color-mix(in oklab, var(--color-accent) 18%, transparent) 0%, transparent 38%),
  radial-gradient(circle at 91% 89%, color-mix(in oklab, var(--color-accent) 16%, transparent) 0%, transparent 30%),
  var(--color-primary);
```

```css
/* .paper-main 背景（現在） */
background: var(--color-surface);

/* 改為 */
background:
  radial-gradient(circle, color-mix(in oklab, var(--color-secondary) 8%, transparent) 1px, transparent 1px) 0 0 / 18px 18px,
  var(--color-surface);
```

## 驗證方式

- `npm run build` 確認無編譯錯誤
- 瀏覽器開啟 `/paper`，目視確認左上、右下各有一個淡琥珀色光暈，卡片區域外可見淡灰藍色點陣紋理，底色維持米白/白色
