# 色彩主題重新設計

## 背景

專案目前的色彩系統存在兩個問題：

1. `frontend/src/plugins/vuetify.ts` 未自訂 theme，Vuetify 元件（按鈕、卡片等）走內建預設藍色系；`frontend/src/styles/tailwind.css` 的 `@theme` 區塊則獨立定義了一套不同的藍/青色階（`--color-primary-100/900`、`--color-secondary-100~800`），兩邊互不相干、色彩不一致。
2. 目前 `--color-background`、`--color-surface`、`--color-success/info/warning/error` 已經是「Tailwind 引用 Vuetify CSS 變數」的模式，但 `primary`/`secondary` 沒有沿用這個模式，造成架構不一致。

使用者要求把整個專案換成新的配色，並提供了 7 個色碼，同時預告近期會新增聊天功能（需要系統訊息 vs 使用者訊息的泡泡配色）。這次一併修正上述架構不一致的問題。

## 目標

- 導入新配色：主背景、次要色、強調色、卡片背景、文字（深/淺）
- 為即將開發的聊天功能預先定義系統訊息／使用者訊息泡泡色
- 讓 Vuetify 與 Tailwind 共用同一份色彩定義（Vuetify 為主，Tailwind 引用），消除現有架構不一致
- 修正因換色而失去可視性的既有元件（`color="primary"` 用法、舊色階 utility class）

## 非目標

- 不處理各頁面內部 `<style scoped>` 自訂的局部色票（例如 `PaperPage.vue` 的 `--brand`、`--page-bg`、`--text-main` 等），這些留待後續個別頁面整理
- 不啟用/完成深色模式（dark mode）。專案目前 dark mode 只有 CSS 骨架（`@custom-variant dark`），未串接切換開關，本次不新增此功能
- 不實作聊天功能本身，只預先定義其會用到的色彩 token
- 不處理圖表（chart）配色邏輯

## 色彩 Token 定義

| Token 名稱 | 色碼 | 角色 | 對比搭配文字 |
|---|---|---|---|
| `primary` | `#f6f5f2` | 頁面主背景 | `ink` |
| `secondary` | `#334155` | 次要區塊／中性深色（導覽、次要文字區塊背景） | `inverted` |
| `accent` | `#e8a33d` | 強調色（按鈕、CTA、高亮、選中狀態） | `ink` |
| `surface` | `#ffffff` | 卡片、彈窗等浮起區塊背景 | `ink` |
| `chat-system` | `#fbead0` | （新）聊天系統訊息泡泡背景，供未來聊天功能使用 | `ink` |
| `chat-user` | `#12213b` | （新）聊天使用者訊息泡泡背景，供未來聊天功能使用 | `inverted` |
| `ink` | `#1c2130` | 深色文字，用於淺色背景 | — |
| `inverted` | `#f1f5f9` | 淺色文字，用於深色背景 | — |

**命名理由**：文字色取名 `ink`／`inverted` 而非 `text-primary`，避免與 Tailwind `text-{token}` 語法（token 值當文字顏色使用）產生語意衝突——`text-primary` 若照字面語法會是「把文字塗成米白色」，與「深色內文文字」的意圖相反。

**對比度驗證**：已計算 WCAG 相對亮度對比，`primary/ink`（極高對比）、`secondary/inverted`（約 9.5:1）、`accent/ink`（約 7.1:1）、`chat-system/ink`（約 13.6:1）、`chat-user/inverted`（約 14.7:1）皆達 AAA 等級（≥7:1），無可讀性疑慮。

`surface` 色碼（`#ffffff`）不在使用者提供的 7 色之內，是為了讓卡片與米白頁面背景（`primary`）產生層次差異而新增的白色，經確認後採用。

## 架構調整

**單一真相來源**：以 Vuetify theme 為主，Tailwind `@theme` 全部改為引用 Vuetify 產生的 CSS 變數（沿用專案已有的 `background`/`surface` 模式），消除目前 primary/secondary 兩邊各自定義、容易漂移的問題。

### 1. `frontend/src/plugins/vuetify.ts`

新增 `theme.themes.light.colors`：

```ts
theme: {
  defaultTheme: 'light',
  utilities: false,
  themes: {
    light: {
      colors: {
        primary: '#f6f5f2',
        secondary: '#334155',
        accent: '#e8a33d',
        background: '#f6f5f2',
        surface: '#ffffff',
        // success / info / warning / error 沿用 Vuetify 預設值，不在本次範圍
      },
    },
  },
},
```

Vuetify 會自動為每個色計算對比足夠的 `on-*` 文字色（`on-primary`、`on-secondary`、`on-accent`、`on-background`、`on-surface`），Vuetify 元件本身不需要額外處理。

### 2. `frontend/src/styles/tailwind.css`

`@theme` 區塊變更：

- `--color-primary`、`--color-secondary`、`--color-accent` 改為引用 `rgb(var(--v-theme-*))`，比照現有 `--color-background`/`--color-surface` 寫法
- 移除舊的九個色階變數：`--color-primary-100`、`--color-primary-900`、`--color-secondary-100` ~ `--color-secondary-800`
- 新增純 Tailwind 常數（不經 Vuetify，因為聊天泡泡與文字色不是 Vuetify 元件會用到的角色）：`--color-chat-system: #fbead0`、`--color-chat-user: #12213b`、`--color-ink: #1c2130`、`--color-inverted: #f1f5f9`

### 3. 既有用法遷移

**`frontend/src/components/Introduction.vue`**（唯一使用舊色階 utility class 的檔案）：

| 舊寫法 | 新寫法 | 說明 |
|---|---|---|
| `bg-primary-100 dark:bg-primary-900` | `bg-primary` | `dark:` 變體目前不會觸發（dark mode 未啟用，屬 dead code），直接移除 |
| `bg-secondary-100` | `bg-secondary/10` | 用 10% 透明度模擬原本的淺色階效果 |
| `dark:bg-linear-to-r dark:from-secondary-800 dark:to-secondary-600 dark:text-white` | 移除 | 同上，dark mode 未啟用，這段從未實際生效 |

**`color="primary"` 用法**（共 9 處，換色後 Vuetify primary 變為米白色，會導致這些元件視覺上幾乎消失，故一併改為 `color="accent"`）：

- `frontend/src/components/HelloWorld.vue`
- `frontend/src/views/PaperPage.vue`
- `frontend/src/components/WorkflowBuilder.vue`（2 處）
- `frontend/src/views/PaperSourcesView.vue`（2 處）
- `frontend/src/components/paper/InsertChartDialog.vue`
- `frontend/src/views/ResultsPage.vue`（2 處）

## 驗證方式

- 建置前端（`npm run build` 或 dev server）確認 Tailwind `@theme` 與 Vuetify theme 無編譯錯誤
- 目視檢查上述 9 處元件與 `Introduction.vue` 的 hero-card / feature-card，確認顏色套用正確、無「消失」的按鈕
- 檢查全站背景、卡片、導覽等主要區塊呈現新配色
