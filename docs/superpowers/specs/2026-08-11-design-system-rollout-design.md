# 設計系統全站套用（Design system rollout）

日期：2026-08-11

## 目標

把 `docs/DESIGN_SYSTEM.md` 的視覺規範套到 DataMind 前端的所有頁面。Phase 1（token 基礎層）已完成 — `plugins/vuetify.ts` 定義語意色票、`styles/tailwind.css` 橋接成 `--color-* / --radius-* / --shadow-* / --dur-* / --ease-* / --content-*`、`styles/main.scss` 鋪好頁面漸層與 `prefers-reduced-motion`。這一輪是 Phase 2：把這些 token 與 §5–§8 的元件、動效、版面規格實際套進畫面。

改動深度定在「規格 + 動效，版面不重設」：色彩、圓角、陰影、字級、圖示、元件形態、互動回饋、容器寬度上限全部對齊規範；資訊架構與欄位配置維持現狀，只在明顯違反 §8.2 或 §7 時順手修。

## 現況

- 約 30 個 `.vue` 檔仍有硬寫 hex，最多的是 `WorkflowBuilder.vue`(41)、`ResultView.vue`(26)、`MappingTable.vue`(26)、`CreateProjectView.vue`(24)。
- 按鈕分裂成兩套：61 處 `v-btn`、61 處原生 `<button>`。§7.1 的四變體與 §6.2 的邊緣反光 hover 都還沒有實作。
- 表單元件幾乎不用 Vuetify（`v-text-field` 1 處、`v-select` 1 處、`v-table` 0 處），專案本來就大量自刻。
- `views/hub/DashboardView.vue` 與 `layouts/HubLayout.vue` 已經改完但未 commit，可作為頁面層的轉換範本。
- `views/StyleGuideView.vue` 是 dev-only 的 token 核對頁，已存在。

## 做法

### 共用層

新開 `frontend/src/components/ui/`，放設計系統原語，與既有的 `components/common/`（有業務邏輯的共用元件，如 `CustomSelect`）區隔。

| 產出 | 形式 | 內容 |
|---|---|---|
| `ui/AppButton.vue` | 元件 | §7.1 四變體（primary / secondary / ghost / danger）、pill 形狀、`:active scale(0.96)`、內建 §6.2 邊緣反光 hover。以原生 `<button>` 實作，支援 `loading`、`disabled`、icon-only |
| `composables/useSpecularHover.ts` | composable | `pointermove` 更新 `--mx/--my` CSS 變數與 proximity 感應。獨立成檔，讓手感參數只有一處可調 |
| `ui/StatusBadge.vue` | 元件 | §7.5 兩種呈現（`variant="dot"` / `variant="badge"`）× 三狀態（success / warning / danger）。圓點色與文字色照 §2.2 分開取值 |
| `ui/PageHeader.vue` | 元件 | h1（22px/500）+ 副標（13px）+ 右側 action slot |
| `ui/TableShell.vue` + `.ds-table` | 元件 + 全域 class | §7.4。`TableShell` 只負責容器（`--color-surface` + `--radius-md` + `--shadow-card` + `overflow: hidden`）；表身樣式做成全域 class 套在既有 `<table>` 上，不接管欄位渲染邏輯 |
| `styles/glass.css` | 全域 class | `.glass-panel`（浮動面板、彈窗）與 `.glass-menu`（下拉選單），含 `-webkit-backdrop-filter` 前綴與 `@supports` fallback |
| `views/StyleGuideView.vue` | 擴充 | 上述元件全部列入，作為元件層的對照基準 |

刻意不抽的：

- **卡片 / 面板** — 只是三行 CSS（surface + radius-md + shadow-card），包成元件反而多一層間接。
- **輸入框** — 全站自刻且形態各異，等 Batch 1 走完再評估有沒有真的重複。
- **完整 DataTable 元件** — `MappingTable` 這類表格有自己的互動與欄位邏輯，硬包成資料驅動元件會打架。

按鈕的收斂方式是自刻 `AppButton` 逐批取代 `v-btn` 與原生 `<button>`，不採用「全域 CSS class + Vuetify defaults 覆寫」— 後者要跟 Vuetify 的 ripple、內距、字重打架，反光 hover 也得穿透 overlay 層。

一個例外：`components/auth/GoogleSignInButton.vue` 不換成 `AppButton`。Google 對登入按鈕的樣式（配色、字體、圖標比例）有品牌規範，套自家按鈕變體會違反規範。該檔只做 token 化與圖示檢查。

### 每頁的套用清單

每一頁跑同一份檢查：

1. 硬寫 hex → §2.2 語意 token
2. 圓角 → `--radius-sm/md/lg` 或 pill；陰影 → `--shadow-card/float`
3. 字級字重 → §3 階層表；清掉所有 600/700，只留 400/500
4. 圖示 → outline 版（§3.5）；同語意全站統一同一個圖示
5. 按鈕（`v-btn` 與原生 `<button>`）→ `AppButton`
6. 狀態顯示 → `StatusBadge`
7. 表格 → `TableShell` + `.ds-table`
8. 過場 → `--dur-*` / `--ease-*`；同類元件的 hover 回饋統一（卡片上浮 1–2px、列換 `--color-surface-alt` 底）
9. 容器寬度 → 一般頁 `--content-max-width`、論文閱讀區 `--content-measure`、資料密集頁 `--content-max-width-wide`
10. 浮動層（彈窗 / 下拉 / chat 面板）→ `.glass-panel` / `.glass-menu`
11. 進場動畫 → `--dur-slow` + `--ease-out` 輕微上移淡入；列表 stagger 30–40ms、總長 ≤250ms
12. 既有的轉圈 loading → skeleton。只換已經有 loading 狀態的地方，不新增 loading 狀態
13. 文字對比掃一次，確保過 WCAG AA

## 批次

每批完成後先給 user 在瀏覽器確認，通過才進下一批。commit 一律等 user 點頭。

### Batch 0 — 共用層

只建上表的原語與 StyleGuideView 擴充，不改任何頁面。

### Batch 1 — Hub + 認證 + 介紹頁

- `layouts/HubLayout.vue`、`components/hub/HubSidebar.vue`
- `views/hub/`：`DashboardView`（已改，併入本批驗收）、`FrameworkLibraryView`、`ExtractFrameworkView`、`ProjectsView`、`CreateProjectView`、`ProjectDetailView`、`FieldMappingView`、`ResultView`、`SettingsView`
- `components/hub/fieldMapping/`：`DatasetPreview`、`MappingChatPanel`、`MappingTable`
- `views/`：`LoginView`、`RegisterView`、`ForgotPasswordView`、`ResetPasswordView`
- `components/auth/GoogleSignInButton.vue`、`components/common/CustomSelect.vue`
- `views/TutorialPage.vue` → `components/Introduction.vue`

### Batch 2 — Paper

- `views/PaperPage.vue`、`views/PaperSourcesView.vue`
- `components/paper/`：`PaperEditor`、`PaginatedPaperView`、`ReferencesSection`、`CitationPopover`、`InsertChartDialog`、`JournalScoreDialog`、`JournalScorePanel`、`ScoreRing`、`ModeSwitch`、`StrikethroughIcon`、`charts/BarChart`、`charts/RadarChart`
- `components/paper/paperContentTypography.css`

### Batch 3 — Workflow

- `views/WorkflowPage.vue`、`views/ResultsPage.vue`
- `components/WorkflowBuilder.vue`
- `components/workflow/`：`WorkflowCanvas`、`WorkflowWorkspace`、`WorkflowOptionsPanel`、`UploadDialog`、`IconNode`
- `components/workflow/nodePanel/` 全部九個
- 節點語意改動（見下節）：`types/workflow.ts`、`composables/workflow/useWorkflowNodes.ts`、`composables/workflow/useWorkflowImport.ts`、`constants/workflowData.ts`

**不處理**：`views/PyCaretTestPage.vue` — 它 import 的 `components/PyCaretApiTester.vue` 不存在，也沒掛路由，是死檔。

## 三個特別決策

### 側邊欄：兩版並存後再選

`docs/DESIGN_SYSTEM.md` §7.2 寫的是深藏青玻璃（`rgba(16,32,66,0.5~0.7)`、選中項用較亮的半透明白底），但 `HubSidebar.vue` 現在是淺色玻璃（白底 0.42 + 白色受光邊 + 內陰影 + 掃光），做得相當細緻。

做法：`HubSidebar` 同時實作兩版，用一個 dev-only 切換（localStorage flag）在瀏覽器互相對照。兩版共用同一份 DOM 結構與收合動畫，差別只在 tint、邊框、文字與選中態顏色。user 選定後刪掉落選那版，並把 §7.2 改寫成定案的規格。

### 玻璃套齊 §5.3

套玻璃：側邊欄（核對參數是否落在 §5.2 範圍）、AI 對話面板（`MappingChatPanel`、`ResultView` 的分析跟談）、彈窗（`UploadDialog`、`InsertChartDialog`、`JournalScoreDialog`）、下拉選單（`CustomSelect`、`CitationPopover`）。

一般資料卡片與表格維持實色 `--color-surface`，這條嚴格遵守。

### Workflow 節點：底色表類型、外圈表狀態

現況 `colorClass` 混用了兩種語意 — 值是 `node-pending` / `node-yellow` / `node-purple`，但 `useWorkflowNodes.ts` 是用 `status === 'finished'` 在切換它，實際表達的是執行狀態，不是 §2.3 講的功能類型。

改成兩個獨立欄位：

- `nodeType`：`data` / `ai` / `manual` / `done`，對應 §2.3 四色，決定節點底色。色值一律引用既有 token（`--color-node-data`、`--color-node-ai`、`--color-warning`、`--color-success`），不在元件裡硬寫 hex。
- `status`：`pending` / `running` / `finished`，走節點外圈 — pending 無外圈、running 沿用現有 spinner 改成轉動進度環、finished 加綠色勾勾角標。

節點形狀維持現狀（圓形 58px + 白色 icon + 下方 label），本來就符合 §7.6。

這是整輪唯一動到資料結構的改動，排在 Batch 3 最後，並拆成兩步：先加 `nodeType`（給預設值讓畫面不變），再切狀態顯示。

## 風險

- **節點語意改動**會影響匯入與執行時的節點狀態流。靠上述兩步拆分降低風險，每步各自可驗。
- **61 處 `v-btn` 換成 `AppButton`** 容易漏掉 `loading`、`disabled`、icon-only 的行為差異。每批換完要逐一比對按鈕的互動狀態，不能只看外觀。
- **玻璃疊動畫**在低階機器會卡。§6.3 已規定不要同時 animate 多個 `backdrop-filter`，實作時遵守。

## 驗收

- 每批完成後附一份清單：改了哪幾頁、每頁動了什麼，user 自己跑 docker 點過。
- `StyleGuideView` 隨 Batch 0 更新，之後每批若新增共用樣式也一併補上。
- 沒有自動化測試可依賴，驗收以人工檢視為主；`npm run build`（含 `vue-tsc`）與 `npm run lint` 每批都要過。

## 回寫設計系統文件

這輪會定案 `docs/DESIGN_SYSTEM.md` 附錄裡的兩個待驗證項目，完成後回寫：

- 側邊欄深色 / 淺色玻璃 → 改寫 §7.2。
- specular 按鈕的 proximity 距離與反光強度 → 實測後把定案數值補進 §6.2。

§2.3 節點色表在 Batch 3 定案後同步更新，記錄 `nodeType` 四值與色碼的對應。
