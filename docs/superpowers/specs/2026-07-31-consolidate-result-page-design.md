# 統一結果頁面：把「生成論文」流程收斂到 Hub 的 ResultView

## 背景

專案裡目前有兩個功能重疊的「結果頁」：

- `frontend/src/views/ResultsPage.vue`（路由 `/results`，用 query string `?project=` 帶專案 ID）——獨立於 Hub 之外的舊流程頁面，從 `/workflow` 執行完流程後的「查看結果」按鈕會導到這裡。這頁有「生成論文」按鈕，點擊導向 `/paper/sources` 選文獻。
- `frontend/src/views/hub/ResultView.vue`（路由 `/hub/projects/:id/result`，用路由參數帶專案 ID）——Hub 專案卡片點進去看到的結果頁，有指標卡片、模型比較表、AI 結構化分析、AI 對話功能，但目前沒有「生成論文」入口。

使用者希望以 `ResultView.vue` 為主要結果頁，把「生成論文」按鈕與其後續流程（`/paper/sources` 選文獻 → 生成論文）從 `ResultsPage.vue` 移過去，並確認：

- `/workflow` 執行完的「查看結果」按鈕也一併改導向 `ResultView.vue`，讓所有入口收斂到同一頁
- `ResultsPage.vue` 上原本的「生成論文」按鈕移除，避免兩處都有生成論文入口造成混淆

## 目標

1. `ResultView.vue` 新增「生成論文」按鈕，導向 `/paper/sources?project=${projectId}`（沿用 `PaperSourcesView.vue` 既有的 query-string 介面，不改它的輸入規格）
2. `ResultsPage.vue` 移除「生成論文」按鈕與對應的 `.generate-paper-btn` CSS
3. `WorkflowWorkspace.vue` 的 `.view-results-btn` 改導向 `/hub/projects/${projectId}/result`，不再導向 `/results`
4. `PaperSourcesView.vue` 的「返回」按鈕、以及「找不到探勘結果」空狀態的「回到 /results」按鈕與文字，改導向 `/hub/projects/${projectId}/result`，讓整段來回路徑（Result → Sources → 回 Result）一致收斂到 Hub 頁面

## 非目標

- 不刪除 `ResultsPage.vue` 這個檔案或 `/results` 路由本身——只移除生成論文按鈕，其餘指標卡片、AI 洞察、模型比較表維持原樣可用
- 不修改 `PaperSourcesView.vue`、`PaperPage.vue` 的資料流邏輯（arXiv 搜尋、生成論文、儲存報告）——只改導覽目標
- 不處理 `ResultsPage.vue` 的頁籤（`toolbar-tabs`「報告」/「程式碼」）——與本次變更無關，維持原樣
- 不改變 `ResultView.vue` 既有的 AI 結構化分析、AI 對話功能

## 設計

### 段落 A：`ResultView.vue` 新增「生成論文」按鈕

在 `page-header` 區塊（目前只有標題與副標題）加入一顆按鈕，樣式比照既有的 `.open-workflow-btn`（accent 底色、白字），只在有結果時顯示（`summary.length > 0`，也就是走到 `v-else` 分支才會渲染的那個區塊之前）：

```html
<div v-if="project" class="page-header">
  <div class="page-header-top">
    <div>
      <h1 class="page-title">{{ project.name }}</h1>
      <p class="page-sub">結果總覽 · 框架：{{ project.frameworkName }}</p>
    </div>
    <RouterLink
      v-if="summary.length > 0"
      class="generate-paper-btn"
      :to="`/paper/sources?project=${projectId}`"
    >
      生成論文
    </RouterLink>
  </div>
</div>
```

對應樣式：

```css
.page-header-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.generate-paper-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 18px;
  height: 38px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s;
}

.generate-paper-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}
```

用 `RouterLink` 而非 `v-btn`/`@click` 導覽，與檔案裡既有的 `.open-workflow-btn`、`.back-link` 一致（都是用 `RouterLink` + `:to`）。

### 段落 B：`ResultsPage.vue` 移除「生成論文」按鈕

移除 `results-toolbar` 裡的這個按鈕：

```html
<v-btn
  class="generate-paper-btn bg-accent"
  color="accent"
  size="small"
  @click="router.push(`/paper/sources?project=${projectId}`)"
>
  生成論文
</v-btn>
```

以及對應的 `.generate-paper-btn { margin-left: 12px; }` CSS 規則。`results-toolbar` 裡其餘的 `back-btn`、`toolbar-tabs` 維持不動。

### 段落 C：`WorkflowWorkspace.vue` 「查看結果」導覽目標

```html
<!-- 現在 -->
<button
  v-if="workflowResult"
  class="view-results-btn"
  type="button"
  @click="router.push(`/results?project=${projectId}`)"
>
  查看結果
</button>
```

```html
<!-- 改為 -->
<button
  v-if="workflowResult"
  class="view-results-btn"
  type="button"
  @click="router.push(`/hub/projects/${projectId}/result`)"
>
  查看結果
</button>
```

### 段落 D：`PaperSourcesView.vue` 返回路徑改為 Hub

```html
<!-- 現在：頂部返回按鈕 -->
<v-btn
  class="back-btn"
  icon="mdi-arrow-left"
  size="small"
  variant="text"
  @click="router.push(`/results?project=${projectId}`)"
/>
```

```html
<!-- 改為 -->
<v-btn
  class="back-btn"
  icon="mdi-arrow-left"
  size="small"
  variant="text"
  @click="router.push(`/hub/projects/${projectId}/result`)"
/>
```

```html
<!-- 現在：找不到探勘結果的空狀態 -->
<section v-else-if="!miningResults" class="sources-status">
  <p>找不到這個專案的探勘結果,請先從 /results 頁面進入。</p>
  <v-btn class="bg-accent" color="accent" size="small" @click="router.push(`/results?project=${projectId}`)">
    回到 /results
  </v-btn>
</section>
```

```html
<!-- 改為 -->
<section v-else-if="!miningResults" class="sources-status">
  <p>找不到這個專案的探勘結果,請先從結果頁進入。</p>
  <v-btn class="bg-accent" color="accent" size="small" @click="router.push(`/hub/projects/${projectId}/result`)">
    回到結果頁
  </v-btn>
</section>
```

`projectId`（`computed(() => route.query.project as string | undefined)`）、`miningResults`、arXiv 搜尋與生成論文的邏輯完全不動，只改這兩處導覽目標與對應的顯示文字。

## 驗證方式

- `npm run build` 確認無編譯錯誤
- 從 Hub 專案列表點進一個有結果的專案 → 確認 `ResultView.vue` 的「生成論文」按鈕出現、可點擊、導向 `/paper/sources?project=<id>`
- 在 `/paper/sources` 頁面點「返回」→ 確認回到 `/hub/projects/<id>/result`
- 從 `/workflow` 執行完一個流程 → 點「查看結果」→ 確認導向 `/hub/projects/<id>/result` 而非 `/results`
- 確認 `ResultsPage.vue`（`/results`）不再顯示「生成論文」按鈕，但指標卡片、AI 洞察、模型比較表仍正常顯示
- 確認沒有結果的專案在 `ResultView.vue` 上不會顯示「生成論文」按鈕（`summary.length === 0` 時走 empty-state 分支）
