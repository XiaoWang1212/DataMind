# 字體統一與論文編輯頁背景調整

## 背景

透過視覺化 mockup 比較後，使用者確認保留現有整體視覺風格（不做大改版），但點出兩個具體問題：

1. **字體不統一**：`HubLayout.vue`（`/hub/*` 底下所有頁面，佔全站大多數）使用系統字體堆疊 `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`；但獨立於 Hub 之外的 `PaperPage.vue`、`PaperSourcesView.vue`、`ResultsPage.vue` 三個頁面各自寫死了不同的 `'Noto Sans TC', 'Segoe UI', sans-serif`，造成同一個網站在不同頁面呈現不同字體。
2. **論文編輯頁（`PaperPage.vue`）的背景**：目前欄寬（760px）使用者確認不用改，但背景想調整——網格底（`.paper-main`，白底＋點狀網點紋理）想改成米色；外層光暈背景（`.paper-page`，accent 色的 radial-gradient 光暈）想拿掉，改成跟其他頁面一樣的純色背景。

## 目標

1. `PaperPage.vue`、`PaperSourcesView.vue`、`ResultsPage.vue` 的 `font-family` 從 `'Noto Sans TC', 'Segoe UI', sans-serif` 改成 `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`，對齊 `HubLayout.vue` 已經在用、涵蓋全站多數頁面的字體堆疊
2. `PaperPage.vue` 的 `.paper-main` 背景：底色從 `var(--color-surface)`（白）改成 `var(--color-primary)`（米色），點狀網點紋理（`radial-gradient(circle, color-mix(in oklab, var(--color-secondary) 8%, transparent) 1px, transparent 1px) 0 0 / 18px 18px`）維持不變
3. `PaperPage.vue` 的 `.paper-page` 背景：拿掉 accent 光暈的 radial-gradient，改成單純的 `var(--color-primary)`

## 非目標

- 不調整 `.paper-sheet`（中間白色「紙張」卡片）的寬度或任何樣式——使用者確認欄寬不用改，紙張本身維持白底
- 不處理 `PaperSourcesView.vue`、`ResultsPage.vue` 的背景光暈——這兩頁在前一批 Workflow 色票工作中新加了跟 `PaperPage.vue` 相同的光暈背景，使用者這次只針對 `PaperPage.vue` 提出要拿掉，暫不擴大範圍到這兩頁（會造成三個頁面背景處理不一致，但這是使用者這次明確的範圍，如果之後想比照辦理可以再開一輪）
- 不處理 `WorkflowPage.vue`（`/workflow`，同樣獨立於 Hub 之外）目前沒有 explicit font-family 宣告、吃 Vuetify 預設值的狀況——不在使用者這次提出的三個頁面範圍內
- 不變更 `HubLayout.vue` 本身的字體堆疊——它是這次要對齊的目標，不是要修改的對象

## 設計

### 段落 A：三個頁面的字體堆疊對齊

```css
/* 現在（PaperPage.vue、PaperSourcesView.vue、ResultsPage.vue 各自都有這行） */
font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
```

```css
/* 改為 */
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

三個檔案的這行都在各自 `<style scoped>` 區塊的最外層容器規則裡（`PaperPage.vue` 的 `.paper-page`、`PaperSourcesView.vue` 的 `.sources-page`、`ResultsPage.vue` 的 `.results-page`），因為是 CSS 繼承屬性，子元素會自動套用，不需要逐一修改內部元素。

### 段落 B：`PaperPage.vue` 網格底改米色

```css
/* 現在 */
.paper-main {
  ...
  background:
    radial-gradient(circle, color-mix(in oklab, var(--color-secondary) 8%, transparent) 1px, transparent 1px) 0 0 / 18px 18px,
    var(--color-surface);
  ...
}
```

```css
/* 改為 */
.paper-main {
  ...
  background:
    radial-gradient(circle, color-mix(in oklab, var(--color-secondary) 8%, transparent) 1px, transparent 1px) 0 0 / 18px 18px,
    var(--color-primary);
  ...
}
```

只換網點紋理疊加的底色（第二層），網點紋理本身（第一層 radial-gradient）不變。

### 段落 C：`PaperPage.vue` 外層光暈拿掉

```css
/* 現在 */
.paper-page {
  ...
  background:
    radial-gradient(circle at 8% 12%, color-mix(in oklab, var(--color-accent) 18%, transparent) 0%, transparent 38%),
    radial-gradient(circle at 91% 89%, color-mix(in oklab, var(--color-accent) 16%, transparent) 0%, transparent 30%),
    var(--color-primary);
  ...
}
```

```css
/* 改為 */
.paper-page {
  ...
  background: var(--color-primary);
  ...
}
```

拿掉兩層 accent 光暈的 radial-gradient，只留底色。

## 驗證方式

- `npm run build` 確認無編譯錯誤
- 開啟 `/paper`、`/paper/sources`、`/results` 三頁，用瀏覽器字體檢視工具確認三頁字體堆疊一致，且跟 `/hub/dashboard` 等 Hub 頁面視覺上一致（不再是明顯不同的字體）
- 開啟 `/paper` 確認：`.paper-main` 底色是米色（`--color-primary`，非白色）、點狀網格紋理仍然可見、中間白色紙張卡片維持白底不受影響、外層不再有 accent 色光暈效果
