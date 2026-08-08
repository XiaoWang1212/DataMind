# 移除首頁、預設導向 Hub

## 背景

專案根路徑 `/` 目前指向 `frontend/src/views/HomePage.vue`（渲染 `frontend/src/components/HelloWorld.vue` 的語音助手風格英雄區首頁），跟實際在用的 Hub 區域（`/hub/dashboard` 等）是兩套完全獨立的介面。使用者希望移除這個獨立首頁，改用 Hub 儀表板作為預設進入頁面。

## 目標

- `HomePage.vue` 刪除
- `HelloWorld.vue`（只被 `HomePage.vue` 引用，刪除後會變成死代碼）一併刪除
- 根路徑 `/` 改為導向 Hub 儀表板

## 非目標

- 不改動 `/hub` 路徑本身（繼續保留）與其底下的子路由結構
- 不改動 `/tutorial`、`/workflow`、`/results`、`/paper`、`/paper/sources` 等其他既有路由
- 不改動 Hub 儀表板（`DashboardView.vue`）的內容或版面

## 影響確認

- 搜尋確認 `HelloWorld.vue` 在專案中僅被 `HomePage.vue` 引用（`import HelloWorld from '@/components/HelloWorld.vue'`），刪除後不會留下斷掉的引用
- 搜尋確認沒有其他程式碼透過 route name `"home"` 或字面路徑 `"/"` 連結到首頁（僅 `router/index.ts` 自身定義這個路由），改動不會弄壞其他頁面的導覽連結

## 設計

`frontend/src/router/index.ts` 中，把：

```ts
{
  path: "/",
  name: "home",
  component: () => import("@/views/HomePage.vue"),
},
```

改成（比照現有 `/hub` 的 redirect 寫法）：

```ts
{
  path: "/",
  redirect: "/hub/dashboard",
},
```

同時刪除 `frontend/src/views/HomePage.vue` 與 `frontend/src/components/HelloWorld.vue` 這兩個檔案。

## 驗證方式

- `npm run build` 確認無編譯錯誤（尤其確認沒有殘留對已刪除檔案的 import）
- 瀏覽器開啟 `/`，確認網址列自動變成 `/hub/dashboard` 且畫面正確顯示儀表板
- 確認 `/tutorial`、`/workflow`、`/results`、`/paper`、`/hub` 等其他既有路由仍可正常訪問
