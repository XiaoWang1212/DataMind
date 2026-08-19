# 設計系統 Token 基礎層（Phase 1）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `docs/DESIGN_SYSTEM.md` 的色彩/圓角/陰影/動畫/內容寬度規範落地成 `frontend/` 的公版 CSS token（Vuetify 主題 + Tailwind `@theme` 橋接），讓之後每一頁都能直接引用，不用各自寫死數值。

**Architecture:** 延續既有「Vuetify 主題是顏色的 source of truth，Tailwind `@theme` 引用 Vuetify 產生的 `--v-theme-*` CSS 變數」架構。非顏色 token（圓角/陰影/動畫/寬度）直接定義在 Tailwind `@theme`。全域背景漸層與動畫可及性 reset 套在 `.v-application`／全域樣式層。新增一個 dev-only `/style-guide` 頁面做人工驗收（專案沒有自動化測試）。

**Tech Stack:** Vue 3 + Vuetify 4 + Tailwind CSS 4（CSS-first `@theme`）+ Vite + vue-tsc + eslint（`eslint-config-vuetify`）

## Global Constraints

- 專案沒有自動化測試，每個任務的「測試」步驟一律是：`npm run build`（含 vue-tsc 型別檢查）通過 + eslint 通過 + grep 驗證 + 人工目視檢查
- 色彩/圓角維持單一 source of truth：不在個別元件硬寫新色值，一律引用 token（來自 `docs/DESIGN_SYSTEM.md` §9）
- `--color-ink` 現有意義（深色內文文字，32 檔案/117 處引用）跟文件新規範（品牌藏青）撞名，必須先透過改名把舊用法遷移到 `--color-text`，才能讓 `--color-ink` 承接新意義——順序不可顛倒，否則會有一段「文字色未定義」或「文字色被錯誤覆蓋」的中間狀態
- `--color-accent`（167 處引用）改值不改名：底層數值從金色 `#e8a33d` 改成品牌藏青 `#1A3159`，token 名稱保留
- `--color-danger` 不新增，沿用 Vuetify 既有的 `--color-error`
- 不做按鈕邊緣反光 hover、玻璃效果共用 class/mixin、任何既有頁面的逐項套用——這些留到之後個別排隊的 phase
- 每個任務結束後 app 必須維持可建置、可運行的狀態，不留下「顏色暫時錯誤」的中間態

---

## File Structure

- **Modify** `frontend/src/plugins/vuetify.ts` — Vuetify `light` theme 的 `colors`：重新映射既有插槽（primary/secondary/accent/background/success/warning/error）+ 新增自訂顏色 key（`ink-strong`/`text`/`surface-alt`/`border`/`border-strong`/`success-bg`/`warning-bg`/`error-bg`/`node-data`/`node-ai`）
- **Modify** `frontend/src/styles/tailwind.css` — `@theme` 區塊：新增色彩橋接、替換圓角尺度（sm/md/lg，退役 xl）、新增陰影/動畫/內容寬度 token；`@utility rounded-*` 系列改用新尺度
- **Modify** `frontend/src/styles/main.scss` — 新增 `.v-application` 全域背景漸層（§5.4）與 `prefers-reduced-motion` reset（§6.3）
- **Modify** 32 個既有 `.vue` 檔案 — 機械改名 `var(--color-ink)` → `var(--color-text)`（見任務 1 的完整清單）
- **Modify** `frontend/src/components/Introduction.vue` — 唯一使用舊 `rounded-xl` 的地方，改成 `rounded-lg`
- **Modify** `frontend/src/router/index.ts` — 新增 dev-only 的 `/style-guide` 路由
- **Create** `frontend/src/views/StyleGuideView.vue` — token 展示頁

---

### Task 1: 改名騰出 `--color-ink`

現有 `--color-ink`（`#1c2130`）在 32 個檔案、117 處當「內文深色文字」用，跟即將定義的品牌藏青撞名。這個任務只做純改名（數值不變，視覺零影響），把名字讓給後面的任務用。

**Files:**
- Modify: `frontend/src/styles/tailwind.css:27`（`--color-ink: #1c2130;` → `--color-text: #1c2130;`，暫時還是 flat hex，尚未接 Vuetify）
- Modify（32 個檔案，全部把 `var(--color-ink)` 換成 `var(--color-text)`）：
  - `frontend/src/components/common/CustomSelect.vue`
  - `frontend/src/components/hub/HubSidebar.vue`
  - `frontend/src/components/paper/PaperEditor.vue`
  - `frontend/src/components/paper/ReferencesSection.vue`
  - `frontend/src/components/workflow/IconNode.vue`
  - `frontend/src/components/workflow/UploadDialog.vue`
  - `frontend/src/components/workflow/WorkflowOptionsPanel.vue`
  - `frontend/src/components/workflow/WorkflowWorkspace.vue`
  - `frontend/src/components/workflow/nodePanel/ComputeCiPanel.vue`
  - `frontend/src/components/workflow/nodePanel/DataTablePanel.vue`
  - `frontend/src/components/workflow/nodePanel/DistributionPanel.vue`
  - `frontend/src/components/workflow/nodePanel/FeatureEngineeringPanel.vue`
  - `frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue`
  - `frontend/src/components/workflow/nodePanel/PreprocessorPanel.vue`
  - `frontend/src/components/workflow/nodePanel/SettingsPanel.vue`
  - `frontend/src/components/workflow/nodePanel/TestScorePanel.vue`
  - `frontend/src/components/workflow/nodePanel/WorkflowFileUploadPanel.vue`
  - `frontend/src/layouts/HubLayout.vue`
  - `frontend/src/views/LoginView.vue`
  - `frontend/src/views/PaperPage.vue`
  - `frontend/src/views/PaperSourcesView.vue`
  - `frontend/src/views/RegisterView.vue`
  - `frontend/src/views/ResultsPage.vue`
  - `frontend/src/views/hub/CreateProjectView.vue`
  - `frontend/src/views/hub/DashboardView.vue`
  - `frontend/src/views/hub/ExtractFrameworkView.vue`
  - `frontend/src/views/hub/FieldMappingView.vue`
  - `frontend/src/views/hub/FrameworkLibraryView.vue`
  - `frontend/src/views/hub/ProjectDetailView.vue`
  - `frontend/src/views/hub/ProjectsView.vue`
  - `frontend/src/views/hub/ResultView.vue`
  - `frontend/src/views/hub/SettingsView.vue`

**Interfaces:**
- Consumes: 無（第一個任務）
- Produces: `--color-text` token 名稱（此刻仍是 flat hex `#1c2130`，任務 3 會改成透過 Vuetify 橋接）；`--color-ink` 名稱空出，任務 2/3 開始賦予新意義

- [ ] **Step 1: 改名前先確認目前引用數，記下基準值**

Run: `cd frontend && grep -rlE "color-ink\)" src --include="*.vue" | wc -l`
Expected: `32`

- [ ] **Step 2: 機械改名 32 個檔案**

```bash
cd frontend
files=(
  src/components/common/CustomSelect.vue
  src/components/hub/HubSidebar.vue
  src/components/paper/PaperEditor.vue
  src/components/paper/ReferencesSection.vue
  src/components/workflow/IconNode.vue
  src/components/workflow/UploadDialog.vue
  src/components/workflow/WorkflowOptionsPanel.vue
  src/components/workflow/WorkflowWorkspace.vue
  src/components/workflow/nodePanel/ComputeCiPanel.vue
  src/components/workflow/nodePanel/DataTablePanel.vue
  src/components/workflow/nodePanel/DistributionPanel.vue
  src/components/workflow/nodePanel/FeatureEngineeringPanel.vue
  src/components/workflow/nodePanel/FeatureImportancePanel.vue
  src/components/workflow/nodePanel/PreprocessorPanel.vue
  src/components/workflow/nodePanel/SettingsPanel.vue
  src/components/workflow/nodePanel/TestScorePanel.vue
  src/components/workflow/nodePanel/WorkflowFileUploadPanel.vue
  src/layouts/HubLayout.vue
  src/views/LoginView.vue
  src/views/PaperPage.vue
  src/views/PaperSourcesView.vue
  src/views/RegisterView.vue
  src/views/ResultsPage.vue
  src/views/hub/CreateProjectView.vue
  src/views/hub/DashboardView.vue
  src/views/hub/ExtractFrameworkView.vue
  src/views/hub/FieldMappingView.vue
  src/views/hub/FrameworkLibraryView.vue
  src/views/hub/ProjectDetailView.vue
  src/views/hub/ProjectsView.vue
  src/views/hub/ResultView.vue
  src/views/hub/SettingsView.vue
)
perl -pi -e 's/var\(--color-ink\)/var(--color-text)/g' "${files[@]}"
```

- [ ] **Step 3: 改 `tailwind.css` 的定義行**

在 `frontend/src/styles/tailwind.css` 找到：

```css
  --color-chat-system: #fbead0;
  --color-chat-user: #12213b;
  --color-ink: #1c2130;
  --color-inverted: #f1f5f9;
```

改成（只改名，數值不變）：

```css
  --color-chat-system: #fbead0;
  --color-chat-user: #12213b;
  --color-text: #1c2130;
  --color-inverted: #f1f5f9;
```

- [ ] **Step 4: 驗證沒有殘留舊引用，新引用數量正確**

Run:
```bash
grep -rlE "color-ink\)" src --include="*.vue" | wc -l
grep -rlE "color-text\)" src --include="*.vue" | wc -l
```
Expected: 第一行 `0`（`--color-ink)` 這個 pattern 已經沒有任何檔案引用），第二行 `32`

- [ ] **Step 5: 建置與型別檢查**

Run: `npm run build`
Expected: 成功，無錯誤（警告可忽略，跟現有 chunk size 警告一致，非本次改動造成）

- [ ] **Step 6: 目視確認零視覺變化**

`npm run dev`，打開 Hub 首頁跟 `/hub/projects/<任一 id>/mapping`，內文文字顏色應該跟改動前完全一樣（還是深灰黑，不是別的顏色）——因為 `--color-text` 目前還是原本的 flat hex，只是換了名字。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/styles/tailwind.css \
  frontend/src/components/common/CustomSelect.vue \
  frontend/src/components/hub/HubSidebar.vue \
  frontend/src/components/paper/PaperEditor.vue \
  frontend/src/components/paper/ReferencesSection.vue \
  frontend/src/components/workflow/IconNode.vue \
  frontend/src/components/workflow/UploadDialog.vue \
  frontend/src/components/workflow/WorkflowOptionsPanel.vue \
  frontend/src/components/workflow/WorkflowWorkspace.vue \
  frontend/src/components/workflow/nodePanel/ComputeCiPanel.vue \
  frontend/src/components/workflow/nodePanel/DataTablePanel.vue \
  frontend/src/components/workflow/nodePanel/DistributionPanel.vue \
  frontend/src/components/workflow/nodePanel/FeatureEngineeringPanel.vue \
  frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue \
  frontend/src/components/workflow/nodePanel/PreprocessorPanel.vue \
  frontend/src/components/workflow/nodePanel/SettingsPanel.vue \
  frontend/src/components/workflow/nodePanel/TestScorePanel.vue \
  frontend/src/components/workflow/nodePanel/WorkflowFileUploadPanel.vue \
  frontend/src/layouts/HubLayout.vue \
  frontend/src/views/LoginView.vue \
  frontend/src/views/PaperPage.vue \
  frontend/src/views/PaperSourcesView.vue \
  frontend/src/views/RegisterView.vue \
  frontend/src/views/ResultsPage.vue \
  frontend/src/views/hub/CreateProjectView.vue \
  frontend/src/views/hub/DashboardView.vue \
  frontend/src/views/hub/ExtractFrameworkView.vue \
  frontend/src/views/hub/FieldMappingView.vue \
  frontend/src/views/hub/FrameworkLibraryView.vue \
  frontend/src/views/hub/ProjectDetailView.vue \
  frontend/src/views/hub/ProjectsView.vue \
  frontend/src/views/hub/ResultView.vue \
  frontend/src/views/hub/SettingsView.vue
git commit -m "refactor: rename --color-ink to --color-text to free the name for the brand color"
```

---

### Task 2: Vuetify 主題色彩全量更新

**Files:**
- Modify: `frontend/src/plugins/vuetify.ts:16-26`（`theme.themes.light.colors`）

**Interfaces:**
- Consumes: 無（跟 Task 1 相互獨立，只是必須排在 Task 3 之前，因為 Task 3 要橋接的 `--v-theme-*` 變數在這裡才會存在）
- Produces: Vuetify 會產生以下 CSS 變數供 Task 3 橋接：`--v-theme-primary`、`--v-theme-secondary`、`--v-theme-accent`、`--v-theme-background`、`--v-theme-surface`、`--v-theme-success`、`--v-theme-warning`、`--v-theme-error`、`--v-theme-ink-strong`、`--v-theme-text`、`--v-theme-surface-alt`、`--v-theme-border`、`--v-theme-border-strong`、`--v-theme-success-bg`、`--v-theme-warning-bg`、`--v-theme-error-bg`、`--v-theme-node-data`、`--v-theme-node-ai`（已直接讀 Vuetify 原始碼 `genCssVariables` 確認：物件 key 會原封不動接在 `--v-theme-` 後面，kebab-case key 如 `'ink-strong'` 會產生 `--v-theme-ink-strong`，不會被轉成 camelCase 或做其他轉換）

- [ ] **Step 1: 修改 `theme.colors`**

把 `frontend/src/plugins/vuetify.ts` 裡：

```ts
      light: {
        colors: {
          primary: '#f6f5f2',
          secondary: '#334155',
          accent: '#e8a33d',
          background: '#f6f5f2',
          surface: '#ffffff',
        },
      },
```

改成：

```ts
      light: {
        colors: {
          // 品牌藏青（docs/DESIGN_SYSTEM.md §2.2 ink）：主要按鈕、選中、重點
          primary: '#1A3159',
          // ink-soft：次要文字、說明、icon
          secondary: '#626B7E',
          // accent 名稱保留給尚未遷移的既有頁面用（167 處引用），數值已從金色改成品牌藏青，
          // 之後個別頁面遷移時應改直接引用 primary，屆時再考慮拿掉這個 key
          accent: '#1A3159',
          // page：頁面底色。實際畫面會被 main.scss 的漸層蓋掉，這裡是漸層底下的純色 fallback
          background: '#E4E9ED',
          surface: '#FFFFFF',
          success: '#1F7A44',
          warning: '#C9822E',
          // docs/DESIGN_SYSTEM.md 稱這個角色為 danger，這裡沿用 Vuetify 內建的 error 插槽名稱
          error: '#C7392E',
          // 品牌藏青深一階：hover/按下、標題強調
          'ink-strong': '#12244A',
          // 內文深色文字。原本借用 primary 的位置（--color-ink），Task 1 已把舊引用改名讓出這裡
          text: '#1C2130',
          // 次級底：表頭、hover 背景、工具列
          'surface-alt': '#F6F5F2',
          // 一般分隔線
          border: '#E4E6E8',
          // 強調分隔、輸入框邊界
          'border-strong': '#D3D8DC',
          'success-bg': '#DCEDE3',
          'warning-bg': '#F5E9D8',
          'error-bg': '#F5DEDC',
          // workflow 節點分類色（docs/DESIGN_SYSTEM.md §2.3）。人工確認/完成複用 warning/success，不重複定義
          'node-data': '#5B7A9D',
          'node-ai': '#6B5B95',
        },
      },
```

- [ ] **Step 2: 建置與型別檢查**

Run: `npm run build`
Expected: 成功，無錯誤

- [ ] **Step 3: 目視確認 Vuetify 內建元件立即變色**

`npm run dev`，打開任一頁面，確認：
- 按鈕（例如登入頁的送出按鈕）從米白/金色變成藏青
- 進度條/loading spinner 變成藏青

（這是預期內、已跟使用者確認過的立即視覺變化，見 spec 的「立即可見的視覺影響」章節）

- [ ] **Step 4: Commit**

```bash
git add frontend/src/plugins/vuetify.ts
git commit -m "feat: extend Vuetify theme with design system color roles"
```

---

### Task 3: Tailwind token 橋接 + 圓角/陰影/動畫/寬度 token

**Files:**
- Modify: `frontend/src/styles/tailwind.css`（`@theme` 區塊全部、`@utility rounded-*` 系列）
- Modify: `frontend/src/components/Introduction.vue:101`（`rounded-xl` → `rounded-lg`，圓角尺度變動的唯一受影響處）

**Interfaces:**
- Consumes: Task 2 產生的 `--v-theme-*` 變數；Task 1 產生的 `--color-text` 名稱
- Produces: 所有頁面之後可以直接引用的最終 token 名稱：`--color-ink`、`--color-ink-strong`、`--color-ink-soft`、`--color-text`、`--color-surface`、`--color-surface-alt`、`--color-page`、`--color-border`、`--color-border-strong`、`--color-success`/`--color-success-bg`、`--color-warning`/`--color-warning-bg`、`--color-error`/`--color-error-bg`、`--color-accent`、`--color-node-data`、`--color-node-ai`、`--radius-sm`/`--radius-md`/`--radius-lg`、`--shadow-card`/`--shadow-float`、`--dur-fast`/`--dur-base`/`--dur-slow`、`--ease-out`/`--ease-in-out`/`--ease-spring`、`--content-measure`/`--content-max-width`/`--content-max-width-wide`；Tailwind utility class `rounded-sm`/`rounded-md`/`rounded-lg`（及 `rounded-t-*`/`rounded-b-*`/`rounded-s-*`/`rounded-e-*` 對應版本）

- [ ] **Step 1: 改寫 `@theme` 區塊**

把整個 `frontend/src/styles/tailwind.css` 換成：

```css
@import "tailwindcss/theme" layer(tailwind.theme);
@import "tailwindcss/utilities" layer(tailwind.utilities);

@config "../../tailwind.config.ts";

@theme {
  --font-heading: "Roboto", sans-serif;
  --font-body: "Roboto", sans-serif;
  --font-mono: "Roboto Mono", monospace;

  /* docs/DESIGN_SYSTEM.md §4.2。pill 用 Tailwind 內建的 rounded-full(9999px)，不另外造 token */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;

  /* §4.3 */
  --shadow-card: 0 2px 10px rgba(14, 30, 66, 0.06);
  --shadow-float: 0 16px 40px rgba(14, 30, 66, 0.16);

  /* §6.1 */
  --dur-fast: 120ms;
  --dur-base: 200ms;
  --dur-slow: 320ms;
  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

  /* §8.2。--content-max-width 文件給的範圍是 1280-1440px，先取下限，之後個別頁面覺得太窄再調 */
  --content-measure: 760px;
  --content-max-width: 1280px;
  --content-max-width-wide: 1680px;

  --color-background: rgb(var(--v-theme-background));
  --color-surface: rgb(var(--v-theme-surface));
  --color-success: rgb(var(--v-theme-success));
  --color-info: rgb(var(--v-theme-info));
  --color-warning: rgb(var(--v-theme-warning));
  --color-error: rgb(var(--v-theme-error));
  --color-primary: rgb(var(--v-theme-primary));
  --color-secondary: rgb(var(--v-theme-secondary));
  --color-accent: rgb(var(--v-theme-accent));

  --color-chat-system: #fbead0;
  --color-chat-user: #12213b;
  --color-text: rgb(var(--v-theme-text));
  --color-inverted: #f1f5f9;

  /* docs/DESIGN_SYSTEM.md §2.2 角色 token。ink 沿用既有 primary 插槽，不新增撞名 key
     （見 docs/superpowers/specs/2026-08-10-design-token-foundation-design.md） */
  --color-ink: rgb(var(--v-theme-primary));
  --color-ink-strong: rgb(var(--v-theme-ink-strong));
  --color-ink-soft: rgb(var(--v-theme-secondary));
  --color-surface-alt: rgb(var(--v-theme-surface-alt));
  --color-page: rgb(var(--v-theme-background));
  --color-border: rgb(var(--v-theme-border));
  --color-border-strong: rgb(var(--v-theme-border-strong));
  --color-success-bg: rgb(var(--v-theme-success-bg));
  --color-warning-bg: rgb(var(--v-theme-warning-bg));
  --color-error-bg: rgb(var(--v-theme-error-bg));
  --color-node-data: rgb(var(--v-theme-node-data));
  --color-node-ai: rgb(var(--v-theme-node-ai));

  --breakpoint-*: initial;
  --breakpoint-xs: 0px;
  --breakpoint-sm: 600px;
  --breakpoint-md: 840px;
  --breakpoint-lg: 1145px;
  --breakpoint-xl: 1545px;
  --breakpoint-xxl: 2138px;
}

@custom-variant light (&:where(.v-theme--light, .v-theme--light *));
@custom-variant dark (&:where(.v-theme--dark, .v-theme--dark *));

@utility rounded-0 { border-radius: 0 }
@utility rounded-sm { border-radius: var(--radius-sm) }
@utility rounded-md { border-radius: var(--radius-md) }
@utility rounded-lg { border-radius: var(--radius-lg) }

@utility rounded-t-sm { border-top-left-radius: var(--radius-sm); border-top-right-radius: var(--radius-sm) }
@utility rounded-t-md { border-top-left-radius: var(--radius-md); border-top-right-radius: var(--radius-md) }
@utility rounded-t-lg { border-top-left-radius: var(--radius-lg); border-top-right-radius: var(--radius-lg) }

@utility rounded-b-sm { border-bottom-left-radius: var(--radius-sm); border-bottom-right-radius: var(--radius-sm) }
@utility rounded-b-md { border-bottom-left-radius: var(--radius-md); border-bottom-right-radius: var(--radius-md) }
@utility rounded-b-lg { border-bottom-left-radius: var(--radius-lg); border-bottom-right-radius: var(--radius-lg) }

@utility rounded-s-sm { border-start-start-radius: var(--radius-sm); border-end-start-radius: var(--radius-sm) }
@utility rounded-s-md { border-start-start-radius: var(--radius-md); border-end-start-radius: var(--radius-md) }
@utility rounded-s-lg { border-start-start-radius: var(--radius-lg); border-end-start-radius: var(--radius-lg) }

@utility rounded-e-sm { border-start-end-radius: var(--radius-sm); border-end-end-radius: var(--radius-sm) }
@utility rounded-e-md { border-start-end-radius: var(--radius-md); border-end-end-radius: var(--radius-md) }
@utility rounded-e-lg { border-start-end-radius: var(--radius-lg); border-end-end-radius: var(--radius-lg) }
```

（跟原檔案的差異：`--radius-xl` 整組退役、新增 `--radius-md` 整組、新增陰影/動畫/內容寬度 token、新增 `--color-*` 橋接、`--color-ink`/`--color-text` 改為透過 `rgb(var(--v-theme-*))` 橋接而非 flat hex）

- [ ] **Step 2: 修正 `Introduction.vue` 的圓角尺度**

`frontend/src/components/Introduction.vue:101` 從：

```css
.v-card {
  @apply rounded-xl;
}
```

改成：

```css
.v-card {
  @apply rounded-lg;
}
```

- [ ] **Step 3: 確認沒有其他地方還在用退役的 `rounded-xl`／`--radius-xl`**

Run: `grep -rn "rounded-xl\|radius-xl" src --include="*.vue" --include="*.css"`
Expected: 沒有任何結果（`Introduction.vue` 那處已經在 Step 2 改掉）

- [ ] **Step 4: 建置與型別檢查**

Run: `npm run build`
Expected: 成功，無錯誤

- [ ] **Step 5: Lint**

`tailwind.css` 不在 eslint 檢查範圍內（專案的 eslint 設定不涵蓋 `.css`，執行會得到「File ignored」，不用執行），只檢查改到的 `.vue` 檔案：

Run: `npx eslint src/components/Introduction.vue`
Expected: 沿用 Introduction.vue 原本就有的既有 lint 狀態即可（若原本零錯誤，這次也要零錯誤；若跟改動無關的既有警告不用管）

- [ ] **Step 6: 目視確認新 token 生效**

`npm run dev`，打開任一使用 `CustomSelect` 的頁面（例如 mapping 頁），確認下拉選單 focus 邊框顏色是藏青而不是金色（來自 `--color-accent` 改值）；`Introduction.vue` 若有掛路由可看的話確認卡片圓角變小一點。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/styles/tailwind.css frontend/src/components/Introduction.vue
git commit -m "feat: bridge design system tokens into Tailwind theme"
```

---

### Task 4: 全域頁面背景漸層 + 動畫可及性 reset

**Files:**
- Modify: `frontend/src/styles/main.scss`

**Interfaces:**
- Consumes: 無新 token（漸層色值是 §5.4 給定的裝飾色，故意不綁定任何語意 token，見 spec）
- Produces: 全域 `.v-application` 背景漸層；全域 `prefers-reduced-motion` reset，之後任何頁面新增動畫都會自動遵守，不用每個元件各自處理

- [ ] **Step 1: 新增背景漸層與 reduced-motion reset**

把 `frontend/src/styles/main.scss` 從：

```scss
@layer vuetify-overrides {
  code, pre, .v-code {
    font-family: var(--font-mono);
  }
}
```

改成：

```scss
@layer vuetify-overrides {
  code, pre, .v-code {
    font-family: var(--font-mono);
  }

  // docs/DESIGN_SYSTEM.md §5.4：頁面底鋪柔和漸層，讓玻璃效果（之後階段套用）有東西可以透出來。
  // 蓋在 .v-application 而不是 body，因為 VApp 元件本身有不透明的 background
  // （node_modules/vuetify/lib/components/VApp/VApp.css），蓋在 body 上的話漸層完全看不到。
  .v-application {
    background:
      radial-gradient(720px circle at 8% 30%, rgba(90, 130, 190, 0.45), transparent 55%),
      radial-gradient(560px circle at 88% 18%, rgba(110, 143, 178, 0.20), transparent 55%),
      radial-gradient(520px circle at 25% 92%, rgba(196, 150, 130, 0.10), transparent 55%),
      linear-gradient(175deg, #EEF2F5 0%, #DCE3E9 100%);
    background-attachment: fixed;
  }
}

// docs/DESIGN_SYSTEM.md §6.3：動畫可及性。刻意不放進任何 @layer，
// CSS 規則沒有 layer 時優先權天生高於所有 layer 內的規則，確保這個 reset 一定生效。
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation: none !important;
    transition: none !important;
  }
}
```

- [ ] **Step 2: 建置**

Run: `npm run build`
Expected: 成功，無錯誤

- [ ] **Step 3: 目視確認漸層與 reduced-motion**

`npm run dev`，打開任一頁面，確認頁面背景從純色變成帶柔和漸層的底色（微微偏藍、右上角/左下角有暖色點綴）。再用瀏覽器 devtools 打開 rendering 面板、勾選「Emulate CSS prefers-reduced-motion: reduce」，確認頁面上原本的 transition/animation（例如 mapping 頁的 `row-flash`）不再播放。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/styles/main.scss
git commit -m "feat: apply global page background gradient and reduced-motion reset"
```

---

### Task 5: `/style-guide` token 展示頁

**Files:**
- Create: `frontend/src/views/StyleGuideView.vue`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: Task 2/3/4 產生的所有 token
- Produces: 無（葉節點任務，純展示頁，之後任務不依賴它）

- [ ] **Step 1: 建立展示頁**

Create `frontend/src/views/StyleGuideView.vue`：

```vue
<template>
  <div class="style-guide">
    <h1 class="sg-h1">Design tokens 展示頁</h1>
    <p class="sg-note">
      僅在 dev 模式掛路由，用來核對 docs/DESIGN_SYSTEM.md 的 token 是否套對，不會出現在 production build。
    </p>

    <section>
      <h2 class="sg-h2">色彩</h2>
      <div class="sg-swatch-grid">
        <div v-for="swatch in swatches" :key="swatch.name" class="sg-swatch">
          <div class="sg-swatch-color" :style="{ background: swatch.varRef }" />
          <div class="sg-swatch-label">{{ swatch.name }}</div>
          <div class="sg-swatch-var">{{ swatch.varRef }}</div>
        </div>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">圓角</h2>
      <div class="sg-row">
        <div class="sg-radius-box" style="border-radius: var(--radius-sm)">sm 8px</div>
        <div class="sg-radius-box" style="border-radius: var(--radius-md)">md 12px</div>
        <div class="sg-radius-box" style="border-radius: var(--radius-lg)">lg 16px</div>
        <div class="sg-radius-box rounded-full">pill</div>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">陰影</h2>
      <div class="sg-row">
        <div class="sg-shadow-box" style="box-shadow: var(--shadow-card)">shadow-card</div>
        <div class="sg-shadow-box" style="box-shadow: var(--shadow-float)">shadow-float</div>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">按鈕（Vuetify 內建色，尚未套邊緣反光 hover）</h2>
      <div class="sg-row">
        <v-btn color="primary">primary</v-btn>
        <v-btn color="secondary" variant="tonal">secondary</v-btn>
        <v-btn variant="text">ghost</v-btn>
        <v-btn color="error" variant="tonal">danger</v-btn>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">狀態徽章</h2>
      <div class="sg-row">
        <span class="sg-badge sg-badge--success">已對應</span>
        <span class="sg-badge sg-badge--warning">待確認</span>
        <span class="sg-badge sg-badge--danger">未對應</span>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">字級階層</h2>
      <div class="sg-type-sample" style="font-size: 22px; font-weight: 500;">頁面標題 h1 / 22px / 500</div>
      <div class="sg-type-sample" style="font-size: 18px; font-weight: 500;">區塊標題 h2 / 18px / 500</div>
      <div class="sg-type-sample" style="font-size: 15px; font-weight: 500;">小標 h3 / 15px / 500</div>
      <div class="sg-type-sample" style="font-size: 14px; font-weight: 400;">內文 / 14px / 400</div>
      <div class="sg-type-sample" style="font-size: 13px; font-weight: 400;">次要/說明 / 13px / 400</div>
    </section>

    <section>
      <h2 class="sg-h2">內容寬度</h2>
      <div class="sg-width-demo" style="max-width: var(--content-measure)">content-measure 760px</div>
      <div class="sg-width-demo" style="max-width: var(--content-max-width)">content-max-width 1280px</div>
      <div class="sg-width-demo" style="max-width: var(--content-max-width-wide)">content-max-width-wide 1680px</div>
    </section>
  </div>
</template>

<script lang="ts" setup>
  interface Swatch { name: string, varRef: string }

  const swatches: Swatch[] = [
    { name: 'ink（品牌藏青）', varRef: 'var(--color-ink)' },
    { name: 'ink-strong', varRef: 'var(--color-ink-strong)' },
    { name: 'ink-soft', varRef: 'var(--color-ink-soft)' },
    { name: 'text', varRef: 'var(--color-text)' },
    { name: 'surface', varRef: 'var(--color-surface)' },
    { name: 'surface-alt', varRef: 'var(--color-surface-alt)' },
    { name: 'page', varRef: 'var(--color-page)' },
    { name: 'border', varRef: 'var(--color-border)' },
    { name: 'border-strong', varRef: 'var(--color-border-strong)' },
    { name: 'success', varRef: 'var(--color-success)' },
    { name: 'success-bg', varRef: 'var(--color-success-bg)' },
    { name: 'warning', varRef: 'var(--color-warning)' },
    { name: 'warning-bg', varRef: 'var(--color-warning-bg)' },
    { name: 'error（danger）', varRef: 'var(--color-error)' },
    { name: 'error-bg', varRef: 'var(--color-error-bg)' },
    { name: 'node-data', varRef: 'var(--color-node-data)' },
    { name: 'node-ai', varRef: 'var(--color-node-ai)' },
  ]
</script>

<style scoped>
.style-guide {
  max-width: var(--content-max-width-wide);
  margin: 0 auto;
  padding: 32px;
}

.sg-h1 {
  font-size: 22px;
  font-weight: 500;
  color: var(--color-text);
}

.sg-note {
  font-size: 13px;
  color: var(--color-ink-soft);
  margin-bottom: 24px;
}

.sg-h2 {
  font-size: 18px;
  font-weight: 500;
  color: var(--color-text);
  margin: 32px 0 12px;
}

.sg-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-start;
}

.sg-swatch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.sg-swatch-color {
  height: 56px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.sg-swatch-label {
  font-size: 13px;
  color: var(--color-text);
  margin-top: 6px;
}

.sg-swatch-var {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-ink-soft);
}

.sg-radius-box {
  width: 96px;
  height: 96px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-alt);
  border: 1px solid var(--color-border);
  font-size: 12px;
  color: var(--color-ink-soft);
}

.sg-shadow-box {
  width: 160px;
  height: 96px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  font-size: 12px;
  color: var(--color-ink-soft);
}

.sg-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

.sg-badge--success {
  background: var(--color-success-bg);
  color: #176B39;
}

.sg-badge--warning {
  background: var(--color-warning-bg);
  color: #8F560A;
}

.sg-badge--danger {
  background: var(--color-error-bg);
  color: #B8342A;
}

.sg-type-sample {
  margin-bottom: 8px;
  color: var(--color-text);
}

.sg-width-demo {
  background: var(--color-surface-alt);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  margin-bottom: 8px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-ink-soft);
}
</style>
```

- [ ] **Step 2: 掛 dev-only 路由**

把 `frontend/src/router/index.ts` 從：

```ts
import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/store/authStore";

const PUBLIC_PATHS = ["/login", "/register"];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      redirect: "/hub/dashboard",
    },
```

改成：

```ts
import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/store/authStore";

const PUBLIC_PATHS = ["/login", "/register"];

const devOnlyRoutes = import.meta.env.DEV
  ? [
      {
        path: "/style-guide",
        name: "style-guide",
        component: () => import("@/views/StyleGuideView.vue"),
      },
    ]
  : [];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    ...devOnlyRoutes,
    {
      path: "/",
      redirect: "/hub/dashboard",
    },
```

（其餘路由設定不動，只在陣列開頭插入 `...devOnlyRoutes`）

- [ ] **Step 3: 建置與型別檢查**

Run: `npm run build`
Expected: 成功，無錯誤

- [ ] **Step 4: Lint**

Run: `npx eslint src/views/StyleGuideView.vue src/router/index.ts`
Expected: 零錯誤（有警告的話比照專案既有慣例，跟本次改動無關的不用處理）

- [ ] **Step 5: 確認 dev 模式看得到、production 看不到**

Run: `npm run dev`，瀏覽器開 `http://localhost:3000/style-guide`（如果被導去 `/login`，先登入再訪問），確認頁面正常顯示所有色票/圓角/陰影/按鈕/徽章/字級/寬度示意，色票看起來跟 `docs/DESIGN_SYSTEM.md` §2.2 的建議值一致。

再確認 production build 不含這個路由：
```bash
npm run build
grep -c "style-guide" dist/assets/*.js | grep -v ":0"
```
Expected: 沒有任何檔案出現 `style-guide` 字串（`import.meta.env.DEV` 在 production build 會被 Vite 靜態替換成 `false`，`devOnlyRoutes` 整段連同動態 import 會被 tree-shake 掉）

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/StyleGuideView.vue frontend/src/router/index.ts
git commit -m "feat: add dev-only /style-guide token showcase page"
```

---

### Task 6: 全專案驗收

**Files:** 無新增/修改，純驗證

**Interfaces:**
- Consumes: Task 1-5 的全部成果
- Produces: 無（終點任務）

- [ ] **Step 1: 完整建置**

Run: `npm run build`
Expected: 成功，無錯誤（`vue-tsc` 型別檢查 + `vite build` 都要過）

- [ ] **Step 2: Lint 全專案**

Run: `npm run lint`
Expected: 錯誤數不多於改動前的基準值（本次改動前 `npx eslint src/views/hub/FieldMappingView.vue` 的基準是 8 errors / 96 warnings；全專案 lint 若本來就有既有問題，只要確認本次新增的檔案/改動沒有引入新錯誤即可）

- [ ] **Step 3: 依 spec 的驗證方式逐項目視檢查**

`npm run dev`，對照 `docs/superpowers/specs/2026-08-10-design-token-foundation-design.md` 的「驗證方式」：

- [ ] `/style-guide` 色票、圓角、陰影跟 DESIGN_SYSTEM.md 建議值一致
- [ ] Hub 首頁、mapping 頁、workflow 頁的 Vuetify 內建元件（按鈕、輸入框、進度條）顏色正確套用，沒有「消失」的按鈕（尤其原本用 `color="accent"` 的地方，例如 `WorkflowBuilder.vue`、`PaperEditor.vue`、`PaperSourcesView.vue`）
- [ ] 32 個原本用 `--color-ink` 的檔案挑 3-5 個實際打開看，文字顏色沒有跑掉（改名前後應視覺零差異）
- [ ] 全站頁面背景是柔和漸層，不是純色
- [ ] `Introduction.vue`（如果有掛路由能看到的話）卡片圓角是 16px 不是 24px

- [ ] **Step 4: Commit（若前面步驟有修正遺漏才需要）**

若驗收過程沒有發現問題，這個任務不需要額外 commit，直接標記完成。若有修正，比照對應任務的 commit message 慣例個別提交。
