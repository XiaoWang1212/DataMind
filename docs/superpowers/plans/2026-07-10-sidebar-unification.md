# Sidebar 統一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `HubLayout.vue` 內建的側邊欄抽成共用元件 `HubSidebar.vue`,讓 `/workflow`、`/results`、`/paper` 三個頁面改用它,取代各自原本的做法(`ResultsPage`/`PaperPage` 的假資料 `Sidebar.vue`、`WorkflowPage` 目前完全沒有側邊欄),並移除舊的 `Sidebar.vue` 與其展示路由。

**Architecture:** 純前端重構,不涉及後端與資料流。`HubSidebar.vue` 從 `HubLayout.vue` 的 `<aside class="hub-sidebar">` 區塊原封不動搬出(markup + 對應 CSS + `collapsed` 狀態 + `navItems`),`HubLayout.vue` 改為引用它,行為不變。`WorkflowPage.vue`、`ResultsPage.vue`、`PaperPage.vue` 各自加入 `<HubSidebar />` 作為版面第一個 flex 子項目。最後刪除 `Sidebar.vue` 與 `/sidebar` 路由。

**Tech Stack:** Vue 3 `<script setup lang="ts">` + Vuetify(`v-icon`)+ vue-router + scoped CSS。

## Global Constraints

- 本專案**沒有測試框架**(`frontend/package.json` 無 vitest/jest)。每個 task 用 `npm run type-check` 與 `npm run lint` 驗證(在 `frontend/` 目錄下執行),不要為此計畫引入測試框架。
- 導覽項目內容維持現狀(儀表板/框架庫/專案/設定),**不新增** `/workflow`/`/results`/`/paper` 的導覽連結。
- 元件風格:`<template>` 在前、`<script setup lang="ts">` 在後、`<style scoped>` 最後,縮排 2 空格。
- 介面文案使用繁體中文。
- Commit message 使用英文、慣例式前綴(refactor:/feat:/chore:),不加 Co-Authored-By 以外的尾註。

---

### Task 1: 抽出 HubSidebar.vue,HubLayout.vue 改用它

**Files:**
- Create: `frontend/src/components/hub/HubSidebar.vue`
- Modify: `frontend/src/layouts/HubLayout.vue`(整個檔案改寫,見下方)

**Interfaces:**
- Consumes: 無(元件內部自管 `collapsed` 狀態與 `navItems`,無 props/emits)
- Produces: 元件 `HubSidebar`(預設匯出,`<script setup>`),供 `HubLayout.vue`(本 task)與後續 task 2–4(`ResultsPage.vue`/`PaperPage.vue`/`WorkflowPage.vue`)引用:`import HubSidebar from '@/components/hub/HubSidebar.vue'`

- [ ] **Step 1: 建立 `frontend/src/components/hub/HubSidebar.vue`**

```vue
<template>
  <aside :class="['hub-sidebar', { 'hub-sidebar--collapsed': collapsed }]">
    <div class="hub-sidebar-header">
      <div v-if="!collapsed" class="hub-brand">
        <div class="hub-brand-title">研究中心</div>
        <div class="hub-brand-sub">框架分析系統</div>
      </div>
      <button class="hub-toggle-btn" @click="collapsed = !collapsed">
        <v-icon :icon="collapsed ? 'mdi-chevron-right' : 'mdi-chevron-left'" size="15" />
      </button>
    </div>

    <nav class="hub-nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="hub-nav-item"
        :class="{ 'hub-nav-item--active': route.path.startsWith(item.to) }"
      >
        <v-icon :icon="item.icon" size="19" />
        <span v-if="!collapsed" class="hub-nav-label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div v-if="!collapsed" class="hub-sidebar-footer">
      <div>版本 1.0.0</div>
      <div>© 2026 研究中心</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'

const route = useRoute()
const collapsed = ref(false)

const navItems = [
  { to: '/hub/dashboard', icon: 'mdi-home-outline', label: '儀表板' },
  { to: '/hub/library', icon: 'mdi-book-open-outline', label: '框架庫' },
  { to: '/hub/projects', icon: 'mdi-folder-outline', label: '專案' },
  { to: '/hub/settings', icon: 'mdi-cog-outline', label: '設定' },
]
</script>

<style scoped>
.hub-sidebar {
  width: 210px;
  min-width: 210px;
  background: #ffffff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease, min-width 0.2s ease;
  overflow: hidden;
  position: sticky;
  top: 0;
  height: 100vh;
}

.hub-sidebar--collapsed {
  width: 56px;
  min-width: 56px;
}

.hub-sidebar-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 14px 14px;
  gap: 8px;
}

.hub-brand {
  overflow: hidden;
  flex: 1;
}

.hub-brand-title {
  font-size: 14.5px;
  font-weight: 700;
  color: #111827;
  white-space: nowrap;
  line-height: 1.3;
}

.hub-brand-sub {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 3px;
  white-space: nowrap;
  line-height: 1.4;
}

.hub-toggle-btn {
  width: 22px;
  height: 22px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #ffffff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #9ca3af;
  transition: background 0.15s;
  margin-top: 2px;
}

.hub-toggle-btn:hover {
  background: #f5f5f5;
}

.hub-nav {
  flex: 1;
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.hub-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 7px;
  text-decoration: none;
  color: #4b5563;
  font-size: 13.5px;
  font-weight: 500;
  transition: background 0.12s;
  white-space: nowrap;
}

.hub-nav-item:hover {
  background: #f5f5f5;
}

.hub-nav-item--active {
  background: #2347c5;
  color: #ffffff;
}

.hub-nav-label {
  overflow: hidden;
}

.hub-sidebar-footer {
  padding: 12px 14px;
  font-size: 10.5px;
  color: #9ca3af;
  line-height: 1.7;
  border-top: 1px solid #f0f0f0;
}
</style>
```

- [ ] **Step 2: 改寫 `frontend/src/layouts/HubLayout.vue`**

把整個檔案內容換成:

```vue
<template>
  <div class="hub-wrap">
    <HubSidebar />

    <main class="hub-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import HubSidebar from '@/components/hub/HubSidebar.vue'
</script>

<style scoped>
.hub-wrap {
  display: flex;
  min-height: 100vh;
  background: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color-scheme: light;
  color: #111827;
}

.hub-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 32px 36px;
}
</style>
```

- [ ] **Step 3: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過,無新錯誤

- [ ] **Step 4: 目視驗證 `/hub/*` 行為不變**

Run: `npm run dev`(在 `frontend/` 下),開啟 `/hub/dashboard`
Expected:
1. 側邊欄外觀與行為與重構前一致(Logo、四個導覽項目、收合按鈕、footer)
2. 點收合按鈕 → 側邊欄縮成窄版,只剩圖示
3. 切換到 `/hub/library`、`/hub/projects`、`/hub/settings` → 對應導覽項目呈現 active 樣式

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/hub/HubSidebar.vue frontend/src/layouts/HubLayout.vue
git commit -m "refactor: extract HubSidebar component from HubLayout"
```

---

### Task 2: ResultsPage.vue 改用 HubSidebar

**Files:**
- Modify: `frontend/src/views/ResultsPage.vue:1-4`(template 的 `<Sidebar />`)、`frontend/src/views/ResultsPage.vue:97-99`(import)

**Interfaces:**
- Consumes: `HubSidebar`(來自 task 1,`@/components/hub/HubSidebar.vue`,無 props)
- Produces: 無(頁面元件,無其他 task 依賴)

- [ ] **Step 1: 修改 template,將 `<Sidebar />` 換成 `<HubSidebar />`**

`frontend/src/views/ResultsPage.vue` 第 1–4 行,原本:

```vue
<template>
  <section class="results-page">

    <Sidebar />
```

改為:

```vue
<template>
  <section class="results-page">

    <HubSidebar />
```

- [ ] **Step 2: 修改 import**

`frontend/src/views/ResultsPage.vue` 第 97–99 行,原本:

```ts
  import { onMounted, ref } from 'vue'
  import Sidebar from '@/components/Sidebar.vue'

```

改為:

```ts
  import { onMounted, ref } from 'vue'
  import HubSidebar from '@/components/hub/HubSidebar.vue'

```

- [ ] **Step 3: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過,無 `Sidebar` 未使用或找不到模組的錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/ResultsPage.vue
git commit -m "refactor: use HubSidebar on ResultsPage"
```

---

### Task 3: PaperPage.vue 改用 HubSidebar

**Files:**
- Modify: `frontend/src/views/PaperPage.vue:1-3`(template 的 `<Sidebar />`)、`frontend/src/views/PaperPage.vue:41-46`(import)

**Interfaces:**
- Consumes: `HubSidebar`(來自 task 1,`@/components/hub/HubSidebar.vue`,無 props)
- Produces: 無

- [ ] **Step 1: 修改 template**

`frontend/src/views/PaperPage.vue` 第 1–3 行,原本:

```vue
<template>
  <section class="paper-page">
    <Sidebar />
```

改為:

```vue
<template>
  <section class="paper-page">
    <HubSidebar />
```

- [ ] **Step 2: 修改 import**

`frontend/src/views/PaperPage.vue` 第 41–46 行,原本:

```ts
  import { onMounted, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import CitationPanel from '@/components/paper/CitationPanel.vue'
  import PaperSection from '@/components/paper/PaperSection.vue'
  import Sidebar from '@/components/Sidebar.vue'
  import { mockPaperReport } from '@/constants/reportData'
```

改為:

```ts
  import { onMounted, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import CitationPanel from '@/components/paper/CitationPanel.vue'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import PaperSection from '@/components/paper/PaperSection.vue'
  import { mockPaperReport } from '@/constants/reportData'
```

- [ ] **Step 3: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "refactor: use HubSidebar on PaperPage"
```

---

### Task 4: WorkflowPage.vue 加上 HubSidebar

**Files:**
- Modify: `frontend/src/views/WorkflowPage.vue`(整個檔案改寫,見下方)

**Interfaces:**
- Consumes: `HubSidebar`(來自 task 1,`@/components/hub/HubSidebar.vue`,無 props)
- Produces: 無

**背景:** 目前 `WorkflowPage.vue` 是單一 `<section class="workflow-page">` 只包著 `WorkflowWorkspace`,`.workflow-page` 本身吃掉 `height: 100vh` + `padding: 16px`。加入側邊欄後,`.workflow-page` 要變成 flex row(側邊欄 + 內容容器),原本的 padding 要移到新的內容容器上,讓 `WorkflowWorkspace` 維持滿版高度的行為不變。

- [ ] **Step 1: 改寫 `frontend/src/views/WorkflowPage.vue`**

把整個檔案內容換成:

```vue
<template>
  <section class="workflow-page">
    <HubSidebar />

    <div class="workflow-page__main">
      <WorkflowWorkspace class="workflow-page__workspace" />
    </div>
  </section>
</template>

<script setup lang="ts">
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import WorkflowWorkspace from '@/components/workflow/WorkflowWorkspace.vue'
</script>

<style scoped>
.workflow-page {
  height: 100vh;
  display: flex;
  overflow: hidden;
  background-color: #f9fbff;
}

.workflow-page__main {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 16px;
  box-sizing: border-box;
  overflow: hidden;
}

.workflow-page__workspace {
  height: 100%;
  overflow: hidden;
}
</style>
```

- [ ] **Step 2: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過

- [ ] **Step 3: 目視驗證**

Run: `npm run dev`(在 `frontend/` 下),開啟 `/workflow`
Expected:
1. 左側出現側邊欄(與 `/hub` 樣式一致),右側 WorkflowWorkspace 畫布維持滿版高度、可正常拖拉節點
2. 縮放瀏覽器視窗,畫布區仍正確撐滿剩餘寬度與高度,無捲軸跑版

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/WorkflowPage.vue
git commit -m "feat: add HubSidebar to WorkflowPage"
```

---

### Task 5: 刪除舊 Sidebar.vue 與 /sidebar 路由,全頁面目視驗證

**Files:**
- Delete: `frontend/src/components/Sidebar.vue`
- Modify: `frontend/src/router/index.ts:21-27`(移除 `/sidebar` 路由)

**Interfaces:**
- Consumes: 無
- Produces: 無(收尾 task)

- [ ] **Step 1: 確認沒有其他地方還在引用 `Sidebar.vue`**

Run(在專案根目錄下):

```bash
grep -rn "components/Sidebar" frontend/src
```

Expected: 沒有任何輸出(task 2–4 已把 `ResultsPage.vue`/`PaperPage.vue`/`WorkflowPage.vue` 的引用換成 `HubSidebar`)

- [ ] **Step 2: 刪除檔案**

```bash
rm frontend/src/components/Sidebar.vue
```

- [ ] **Step 3: 移除 router 中的 `/sidebar` 路由**

`frontend/src/router/index.ts` 第 21–27 行,原本:

```ts
    {
      path: "/sidebar",
      name: "sidebar",
      component: () => import("@/components/Sidebar.vue"),
    },
    {
      path: "/results",
```

改為(刪除該路由物件,只留 `/results` 開始的部分):

```ts
    {
      path: "/results",
```

- [ ] **Step 4: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過,無「找不到模組 `@/components/Sidebar.vue`」的錯誤

- [ ] **Step 5: 全頁面目視驗證**

Run: `npm run dev`(在 `frontend/` 下),依序開啟:
1. `/hub/dashboard` → 側邊欄與導覽正常,行為與重構前一致
2. `/workflow` → 側邊欄正常顯示,畫布操作不受影響
3. `/results` → 側邊欄正常顯示,右側儀表板內容(卡片/圖表/表格)不受影響
4. `/paper` → 側邊欄正常顯示,論文內文與右側引用側欄的黃底 highlight 雙向連動仍正常運作
5. 開啟 `/sidebar` → 應該出現 404 / 找不到頁面(路由已移除)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/router/index.ts
git rm frontend/src/components/Sidebar.vue
git commit -m "chore: remove legacy Sidebar component and /sidebar route"
```
