# Sidebar 統一設計

日期:2026-07-10
狀態:已與使用者確認方向,待寫實作計畫

## 背景

目前專案中有兩套側邊欄：

1. `frontend/src/components/Sidebar.vue` — 假資料通用側邊欄(歷史項目清單、新增按鈕、使用者資訊),被 `ResultsPage.vue`、`PaperPage.vue` 使用,另外有一條 `/sidebar` 展示路由直接掛載它。
2. `HubLayout.vue` 內建的 `<aside class="hub-sidebar">` — 真正在用的導覽側邊欄,含 Logo/收合按鈕/導覽項目(儀表板、框架庫、專案、設定)/版本 footer,目前只服務 `/hub/*` 底下的巢狀路由。

本次目標:讓 `/workflow`、`/results`、`/paper` 三個頁面改用 `HubLayout` 的側邊欄樣式與行為,取代各自原本的做法(`ResultsPage`/`PaperPage` 的假資料 Sidebar、`WorkflowPage` 目前完全沒有側邊欄)。導覽項目內容維持現狀,不新增項目。

## 決策摘要

- **抽成共用元件。** 把 `HubLayout.vue` 內的側邊欄 markup 抽到獨立元件 `frontend/src/components/hub/HubSidebar.vue`,`HubLayout.vue` 改為引用它,`/hub/*` 行為不變。
- **導覽項目不變。** `HubSidebar` 沿用現有四個導覽項目(儀表板、框架庫、專案、設定),不加入 `/workflow`/`/results`/`/paper` 的導覽連結。
- **三頁全部加上 HubSidebar。** `WorkflowPage.vue`(目前無側邊欄)、`ResultsPage.vue`、`PaperPage.vue`(目前用假資料 Sidebar)都改為渲染 `<HubSidebar />`。
- **舊 Sidebar 直接刪除。** 刪除 `frontend/src/components/Sidebar.vue` 與 router 中的 `/sidebar` 展示路由,不保留相容垃圾。

## 1. 元件拆分

```
frontend/src/components/hub/HubSidebar.vue   共用側邊欄(從 HubLayout.vue 抽出)
```

**HubSidebar.vue 內容(從現有 HubLayout.vue 搬移,行為不變):**
- Logo/品牌區塊(研究中心 / 框架分析系統)
- 收合按鈕與 `collapsed` 狀態(元件內部自管,無 props/emits)
- 導覽項目清單(寫死於元件內,同現有 `navItems`):
  - `/hub/dashboard` 儀表板
  - `/hub/library` 框架庫
  - `/hub/projects` 專案
  - `/hub/settings` 設定
- active 狀態邏輯沿用現有 `route.path.startsWith(item.to)`
- Footer(版本號 / © 2026 研究中心)

**HubLayout.vue 變更:**
- 移除內聯的 `<aside class="hub-sidebar">...</aside>`,改為 `<HubSidebar />`
- `.hub-sidebar` 相關 CSS 隨 markup 一併搬到 `HubSidebar.vue` 的 `<style scoped>`
- `.hub-wrap`、`.hub-main` 等外層樣式留在 `HubLayout.vue`

## 2. 頁面整合

**WorkflowPage.vue**(目前:單一 `<section class="workflow-page">` 內只有 `WorkflowWorkspace`,`height: 100vh; overflow: hidden`):
- 改為 flex row:`<HubSidebar />` + 一個包住原本 `.workflow-page__workspace` 的容器
- 保持 `WorkflowWorkspace` 現有的填滿高度行為(容器需給 `flex: 1; min-width: 0; height: 100%` 一類設定,不改動 `WorkflowWorkspace` 內部)

**ResultsPage.vue / PaperPage.vue**(目前:已是 flex row,`<Sidebar />` + 主內容):
- 直接把 `<Sidebar />` 換成 `<HubSidebar />`,移除 `import Sidebar from '@/components/Sidebar.vue'`,改 import `HubSidebar`
- 其餘 toolbar/內容/CSS 不動

## 3. 清理

- 刪除 `frontend/src/components/Sidebar.vue`
- 刪除 `frontend/src/router/index.ts` 中 `path: "/sidebar"` 該筆路由定義

## 4. 不在本次範圍

- 不新增/調整 hub 導覽項目內容(未來若要把 `/workflow`/`/results`/`/paper` 納入同一份導覽清單,另開設計)。
- 不處理 `/workflow → /results → /paper` 之間真實資料串接(另一子專案)。
- 不處理 arXiv 文獻檢索與正式論文生成 API(另一子專案)。
