# Hub Sidebar 浮動化改版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 `HubSidebar.vue`（全站共用的側邊欄元件）以四邊留白的浮動卡片呈現，移除持續播放的光帶動畫，收合狀態下 hover 圖示可看到頁面名稱，修正 header 對齊與圖示尺寸，品牌文字改為 DataMind。

**Architecture:** 單一元件（`frontend/src/components/hub/HubSidebar.vue`）純 CSS/樣板調整，不引入新依賴、不動任何宿主頁面。改動分五個獨立可驗證的階段：容器浮動化 → header 對齊與品牌/收合鈕圖示 → nav 尺寸間距 → 移除光帶動畫 → 收合 hover tooltip。

**Tech Stack:** Vue 3 `<script setup>`、Vuetify `<v-icon>`（`@mdi/font`）、既有 CSS custom property token 系統（`--radius-*` / `--shadow-*` / `--dur-*` / `--ease-*`）。

## Global Constraints

- 只改 `frontend/src/components/hub/HubSidebar.vue` 這一個檔案，不動 `HubLayout.vue`、`PaperPage.vue`、`WorkflowPage.vue`、`ResultsPage.vue`、`PaperSourcesView.vue`。
- 不改 `position: sticky` 為 `fixed`。
- 選中狀態維持現行「半透明白底 + Medium 字重」（DESIGN_SYSTEM.md §7.2），不引入新指示樣式。
- dev-only 玻璃深/淺切換鈕（`hub-glass-toggle`）與兩版玻璃並存邏輯保留不動；但本次新增/修改的樣式（floating card、tooltip）必須同時覆蓋 `.hub-sidebar--glass-light` 與 `.hub-sidebar--glass-dark` 兩種變體。
- 動畫使用專案既有 token：`--dur-fast`（120ms）、`--ease-out`（`cubic-bezier(0.22, 1, 0.36, 1)`）。
- 圓角用 `--radius-lg`（16px），陰影用 `--shadow-float`（`0 16px 40px rgba(14,30,66,0.16)`）。
- 圖示庫沿用 `@mdi/font`；找不到 outline 版本的純符號圖示（如 `mdi-dock-left`）直接使用本身即可。
- 專案無自動化測試，每個 task 的驗證用 `npx eslint`（在 `frontend/` 下）與 `npm run build`，加上手動瀏覽器檢查。

---

### Task 1: 側邊欄浮動化（容器）

**Files:**
- Modify: `frontend/src/components/hub/HubSidebar.vue`（`<style scoped>` 內的 `.hub-sidebar` 規則，約第 99-114 行）

**Interfaces:**
- Consumes: 無（純 CSS，無跨檔案依賴）
- Produces: `.hub-sidebar` 的新盒模型（`margin` + `height: calc(100vh - 32px)` + `--radius-lg` + `--shadow-float`），後續 Task 一律沿用這個盒模型，不再修改 `position`/`margin`/`height`。

- [ ] **Step 1: 修改 `.hub-sidebar` 的定位與尺寸**

把現有：

```css
.hub-sidebar {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  width: 220px;
  min-width: 220px;
  height: 100vh;
  overflow: hidden;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-left: none;
  transition: width var(--dur-base) var(--ease-in-out),
    min-width var(--dur-base) var(--ease-in-out);
}
```

改成：

```css
.hub-sidebar {
  position: sticky;
  top: 16px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  width: 220px;
  min-width: 220px;
  height: calc(100vh - 32px);
  margin: 16px 0 16px 16px;
  overflow: hidden;
  border-radius: var(--radius-lg);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-left: none;
  transition: width var(--dur-base) var(--ease-in-out),
    min-width var(--dur-base) var(--ease-in-out);
}
```

（`top` 從 `0` 改成 `16px`：因為現在上下都有 margin，`sticky` 的黏著基準點要跟著往下移，否則往上捲動到底時側邊欄會頂到視窗最上緣、吃掉上方的留白。）

- [ ] **Step 2: 把兩個玻璃變體的陰影換成 `--shadow-float`**

找到 `.hub-sidebar--glass-light` 規則（約第 347-356 行），把：

```css
.hub-sidebar--glass-light {
  background: rgba(255, 255, 255, 0.42);
  border: 1.5px solid rgba(255, 255, 255, 0.9);
  border-left: none;
  box-shadow:
    inset 1px 1px 0 rgba(255, 255, 255, 0.55),
    inset 0 0 0 1px rgba(255, 255, 255, 0.35),
    inset -12px -12px 24px -20px rgba(0, 0, 0, 0.15),
    4px 0 24px rgba(28, 33, 48, 0.1);
}
```

最後一行 `4px 0 24px rgba(28, 33, 48, 0.1)` 改成 `var(--shadow-float)`，其餘 inset 陰影（模擬玻璃受光邊）保留：

```css
.hub-sidebar--glass-light {
  background: rgba(255, 255, 255, 0.42);
  border: 1.5px solid rgba(255, 255, 255, 0.9);
  border-left: none;
  box-shadow:
    inset 1px 1px 0 rgba(255, 255, 255, 0.55),
    inset 0 0 0 1px rgba(255, 255, 255, 0.35),
    inset -12px -12px 24px -20px rgba(0, 0, 0, 0.15),
    var(--shadow-float);
}
```

同樣地，`.hub-sidebar--glass-dark` 規則（約第 359-364 行）把：

```css
.hub-sidebar--glass-dark {
  background: rgba(16, 32, 66, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-left: none;
  box-shadow: 4px 0 24px rgba(14, 30, 66, 0.28);
}
```

改成：

```css
.hub-sidebar--glass-dark {
  background: rgba(16, 32, 66, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-left: none;
  box-shadow: var(--shadow-float);
}
```

- [ ] **Step 3: Lint 與 build 驗證**

```bash
cd frontend
npx eslint src/components/hub/HubSidebar.vue
npm run build
```

Expected: 兩者皆無錯誤。

- [ ] **Step 4: 手動瀏覽器檢查**

啟動 `npm run dev`，開任一 Hub 頁面（如 `/hub/dashboard`），確認：
- 側邊欄上下左三邊可看到底色透出的留白（右邊緊貼主內容，這是預期行為，因為 flex 沒有額外 gap）
- 往下捲動頁面（若該頁內容夠長）時側邊欄仍黏在視窗頂端、上方留白不消失
- 圓角、陰影比原本更明顯，呈現浮起來的感覺
- 深/淺玻璃切換鈕（右下角 dev 按鈕）切兩版都正常

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/hub/HubSidebar.vue
git commit -m "style(sidebar): 側邊欄改為四邊留白的浮動卡片"
```

---

### Task 2: Header 對齊、品牌文字、收合鈕圖示

**Files:**
- Modify: `frontend/src/components/hub/HubSidebar.vue`（`<template>` 的品牌區塊與收合鈕，約第 15-23 行；`<style scoped>` 的 `.hub-sidebar-header` / `.hub-nav`，約第 179-187 行、237-245 行）

**Interfaces:**
- Consumes: Task 1 的 `.hub-sidebar` 盒模型（不變更）
- Produces: header 與 nav 共用的水平內距值（`10px`），Task 3 會在同一個 nav-item padding 基礎上再調整

- [ ] **Step 1: 品牌文字改為 DataMind**

把：

```html
<div class="hub-brand-title">研究中心</div>
```

改成：

```html
<div class="hub-brand-title">DataMind</div>
```

副標 `<div class="hub-brand-sub">框架分析系統</div>` 不動。

- [ ] **Step 2: 收合鈕圖示換成側邊面板圖示**

把：

```html
<button class="hub-toggle-btn" @click="collapsed = !collapsed">
  <v-icon :icon="collapsed ? 'mdi-chevron-right' : 'mdi-chevron-left'" size="15" />
</button>
```

改成：

```html
<button class="hub-toggle-btn" @click="collapsed = !collapsed">
  <v-icon :icon="collapsed ? 'mdi-dock-right' : 'mdi-dock-left'" size="15" />
</button>
```

- [ ] **Step 3: 修正 header 與 nav 的水平對齊**

把 `.hub-sidebar-header` 的 padding：

```css
.hub-sidebar-header {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 18px 14px 14px;
}
```

改成左右內距對齊 nav 的 `10px`：

```css
.hub-sidebar-header {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 18px 10px 14px;
}
```

`.hub-nav` 的 padding 已經是 `6px 10px`（第 237-245 行），數值本來就對，不用改，這一步只是把 header 的 `14px` 改成一致的 `10px`，讓兩者左邊界對齊。

- [ ] **Step 4: Lint 與 build 驗證**

```bash
cd frontend
npx eslint src/components/hub/HubSidebar.vue
npm run build
```

Expected: 兩者皆無錯誤。

- [ ] **Step 5: 手動瀏覽器檢查**

- 側邊欄品牌區顯示「DataMind」、副標「框架分析系統」不變
- 收合鈕跟下方第一個 nav icon 的左邊界對齊（用瀏覽器 DevTools 的對齊輔助線確認，或肉眼比對）
- 點擊收合鈕，圖示在展開/收合兩態間正確切換方向

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/hub/HubSidebar.vue
git commit -m "style(sidebar): 品牌文字改為 DataMind、修正 header 對齊、換收合鈕圖示"
```

---

### Task 3: Nav 圖示尺寸與間距

**Files:**
- Modify: `frontend/src/components/hub/HubSidebar.vue`（`<template>` 的 `v-icon`，約第 33 行；`<style scoped>` 的 `.hub-nav-item` 與收合置中 padding，約第 247-266 行）

**Interfaces:**
- Consumes: Task 2 的 nav-item 對齊基準
- Produces: 無（本 task 為葉節點樣式調整，後續 task 不依賴其產出）

- [ ] **Step 1: 放大 nav icon**

把：

```html
<v-icon :icon="item.icon" size="19" />
```

改成：

```html
<v-icon :icon="item.icon" size="22" />
```

- [ ] **Step 2: 加大 nav-item 的間距**

把：

```css
.hub-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  font-size: 13.5px;
  font-weight: 400;
  color: var(--color-ink-soft);
  text-decoration: none;
  white-space: nowrap;
  transition: background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out),
    padding var(--dur-base) var(--ease-in-out);
}
```

改成：

```css
.hub-nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 11px 12px;
  border-radius: var(--radius-sm);
  font-size: 13.5px;
  font-weight: 400;
  color: var(--color-ink-soft);
  text-decoration: none;
  white-space: nowrap;
  transition: background-color var(--dur-fast) var(--ease-out),
    color var(--dur-fast) var(--ease-out),
    padding var(--dur-base) var(--ease-in-out);
}
```

（多加的 `position: relative` 是為了 Task 5 的 tooltip 能以 `position: absolute` 相對 nav-item 定位，這裡先鋪好，Task 5 不用再改這條規則。）

- [ ] **Step 3: 調整收合狀態下的置中 padding**

把：

```css
/* 收合後把圖示推到 72px 寬度的中間 */
.hub-sidebar--collapsed .hub-nav-item {
  padding-inline: 16px;
}
```

改成（收合寬度 72px，icon 22px + 新左右 padding 需重新置中；`(72 - 22) / 2 = 25px`，扣掉 icon 本身占的空間後取整數）：

```css
/* 收合後把圖示推到 72px 寬度的中間 */
.hub-sidebar--collapsed .hub-nav-item {
  padding-inline: 15px;
}
```

- [ ] **Step 4: Lint 與 build 驗證**

```bash
cd frontend
npx eslint src/components/hub/HubSidebar.vue
npm run build
```

Expected: 兩者皆無錯誤。

- [ ] **Step 5: 手動瀏覽器檢查**

- 展開狀態下 icon 明顯變大、每個 nav 項目之間的呼吸感變足
- 收合狀態下（點擊收合鈕）icon 置中在 72px 寬的欄位裡，沒有偏左或偏右
- 選中項目（目前所在頁面）仍是半透明白底 + 粗體，樣式沒有跑掉

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/hub/HubSidebar.vue
git commit -m "style(sidebar): 放大 nav 圖示並加大項目間距"
```

---

### Task 4: 移除光帶掃過動畫

**Files:**
- Modify: `frontend/src/components/hub/HubSidebar.vue`（`<style scoped>`：刪除 `.hub-sidebar::before` 規則約第 121-133 行、刪除 `@keyframes hub-sidebar-shine` 約第 408-415 行）

**Interfaces:**
- Consumes: 無
- Produces: 無

- [ ] **Step 1: 刪除 `::before` 光帶規則**

刪除整段：

```css
.hub-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
  width: 70%;
  height: 220%;
  background: linear-gradient(115deg, transparent 35%, rgba(255, 255, 255, 0.7) 50%, transparent 65%);
  transform: translate(-160%, -20%) rotate(12deg);
  animation: hub-sidebar-shine 4.5s ease-in-out infinite;
  pointer-events: none;
}
```

- [ ] **Step 2: 刪除對應的 keyframes**

刪除整段（在檔案最尾端）：

```css
@keyframes hub-sidebar-shine {
  0%, 25% {
    transform: translate(-160%, -20%) rotate(12deg);
  }
  65%, 100% {
    transform: translate(160%, -20%) rotate(12deg);
  }
}
```

- [ ] **Step 3: 確認 orb 裝飾未被誤刪**

檢查 `.hub-sidebar-orbs`、`.orb`、`.orb-1`、`.orb-2`、`.orb-3` 規則（約第 135-177 行）仍完整保留，這些是靜態裝飾，不在本次移除範圍內。

- [ ] **Step 4: Lint 與 build 驗證**

```bash
cd frontend
npx eslint src/components/hub/HubSidebar.vue
npm run build
```

Expected: 兩者皆無錯誤。

- [ ] **Step 5: 手動瀏覽器檢查**

打開任一 Hub 頁面，盯著側邊欄看 5-10 秒，確認不再有白色光帶由左上往右下掃過；三顆模糊光暈裝飾仍靜靜待在原本位置。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/hub/HubSidebar.vue
git commit -m "style(sidebar): 移除側邊欄光帶掃過動畫"
```

---

### Task 5: 收合狀態 Hover Tooltip

**Files:**
- Modify: `frontend/src/components/hub/HubSidebar.vue`（`<template>` 的 nav-item 內容，約第 26-36 行；新增 `<style scoped>` 規則）

**Interfaces:**
- Consumes: Task 3 產出的 `.hub-nav-item { position: relative }`
- Produces: 無（本 task 為最終葉節點功能）

- [ ] **Step 1: 在 nav-item 內加入 tooltip 元素**

把：

```html
<nav class="hub-nav">
  <RouterLink
    v-for="item in navItems"
    :key="item.to"
    class="hub-nav-item"
    :class="{ 'hub-nav-item--active': route.path.startsWith(item.to) }"
    :to="item.to"
  >
    <v-icon :icon="item.icon" size="22" />
    <span class="hub-nav-label">{{ item.label }}</span>
  </RouterLink>
</nav>
```

改成：

```html
<nav class="hub-nav">
  <RouterLink
    v-for="item in navItems"
    :key="item.to"
    class="hub-nav-item"
    :class="{ 'hub-nav-item--active': route.path.startsWith(item.to) }"
    :to="item.to"
  >
    <v-icon :icon="item.icon" size="22" />
    <span class="hub-nav-label">{{ item.label }}</span>
    <span v-if="collapsed" class="hub-nav-tooltip">{{ item.label }}</span>
  </RouterLink>
</nav>
```

（用 `v-if="collapsed"` 而不是永遠渲染再靠 CSS 隱藏：展開狀態下 tooltip 完全不需要存在，避免多餘的 DOM 節點跟不必要的 hover 判斷。）

- [ ] **Step 2: 新增 tooltip 樣式（淺色玻璃版本）**

在 `.hub-nav-label` 規則之後（約第 190-194 行之後）新增：

```css
.hub-nav-tooltip {
  position: absolute;
  left: 100%;
  top: 50%;
  z-index: 3;
  margin-left: 10px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  background: color-mix(in oklab, var(--color-surface) 92%, transparent);
  box-shadow: var(--shadow-float);
  color: var(--color-text);
  font-size: 12.5px;
  font-weight: 400;
  white-space: nowrap;
  opacity: 0;
  transform: translateY(-50%) translateX(-4px) scale(0.97);
  transition: opacity var(--dur-fast) var(--ease-out),
    transform var(--dur-fast) var(--ease-out);
  pointer-events: none;
}
```

（用 `color-mix` 混出接近 `.glass-menu` 那種「浮在不透明卡片上」的冷灰材質，因為 tooltip 展開後會蓋到主內容區——跟 DESIGN_SYSTEM.md §5.3 記載的下拉選單情境相同，不能靠純 `backdrop-filter` 玻璃，需要不透明底色保證可讀性。）

- [ ] **Step 3: 加上 hover 觸發規則**

在既有的 hover media query 區塊（約第 334-344 行，`.hub-toggle-btn:hover, .hub-nav-item:hover { ... }` 那段）內新增一條：

```css
@media (hover: hover) and (pointer: fine) {
  .hub-toggle-btn:hover,
  .hub-nav-item:hover {
    background: rgba(255, 255, 255, 0.38);
  }

  .hub-logout-btn:hover {
    background: rgba(255, 255, 255, 0.38);
    color: var(--color-text);
  }

  .hub-nav-item:hover .hub-nav-tooltip {
    opacity: 1;
    transform: translateY(-50%) translateX(0) scale(1);
  }
}
```

- [ ] **Step 4: 新增深色玻璃版本的 tooltip 樣式**

在 `.hub-sidebar--glass-dark .hub-toggle-btn, .hub-sidebar--glass-dark .hub-logout-btn` 規則之後（約第 383-388 行之後）新增：

```css
.hub-sidebar--glass-dark .hub-nav-tooltip {
  background: rgba(16, 32, 66, 0.92);
  box-shadow: var(--shadow-float);
  color: #fff;
}
```

- [ ] **Step 5: Lint 與 build 驗證**

```bash
cd frontend
npx eslint src/components/hub/HubSidebar.vue
npm run build
```

Expected: 兩者皆無錯誤。

- [ ] **Step 6: 手動瀏覽器檢查**

- 點擊收合鈕收起側邊欄
- 依序 hover 每個圖示，確認右側會滑出一個小氣泡顯示對應頁面名稱（儀表板、框架庫、專案、設定）
- 移開滑鼠 tooltip 消失，動作順暢不生硬
- 切換 dev 玻璃切換鈕到深色版本，重複上述 hover 檢查，確認深色版 tooltip 文字對比清楚可讀
- 展開狀態下（`collapsed = false`）不會出現任何 tooltip 殘留

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/hub/HubSidebar.vue
git commit -m "feat(sidebar): 收合狀態新增 hover tooltip 顯示頁面名稱"
```
