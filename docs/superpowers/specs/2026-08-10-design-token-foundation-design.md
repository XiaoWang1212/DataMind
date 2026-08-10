# 設計系統 Token 基礎層（Phase 1）

## 背景

`docs/DESIGN_SYSTEM.md` 定義了一套完整的視覺規範（色彩、字體、間距/圓角/陰影、玻璃效果、動畫、元件規格、RWD 寬度），要套用到整個系統。這份規範本身寫明「不規定實作方式」，把 token 怎麼落地交給實作者判斷。

目前前端的公版設定（`frontend/src/plugins/vuetify.ts` + `frontend/src/styles/tailwind.css`）只做到 2026-07-29〈色彩主題重新設計〉那次的範圍：Vuetify 主題色（`primary`/`secondary`/`accent`/`background`/`surface`）與少數延伸色（`chat-system`、`chat-user`、`ink`、`inverted`），且用了已被 DESIGN_SYSTEM.md 明文淘汰的金色 accent（`#e8a33d`）。圓角、陰影、動畫時長/緩動、內容寬度全部沒有 token，各頁面各自寫死數值。

這次要先把「所有頁面接下來都能引用」的公版 token 層建好，逐頁套用留到之後個別排隊處理。

## 目標

- 把 DESIGN_SYSTEM.md §2（色彩）、§4（間距/圓角/陰影）、§6.1（動畫 token）、§8.2（內容寬度）落地成 CSS custom properties，延續現有「Vuetify 為主、Tailwind 引用」的單一 source of truth 架構
- 套用 §5.4 的全域頁面背景漸層、§6.3 的 `prefers-reduced-motion` reset
- 處理既有 token 命名與新規範衝突的地方，避免顏色語意在不知情的情況下被錯置
- 提供一個 `/style-guide` 展示頁，作為沒有自動化測試時的人工驗收依據

## 非目標

- **不做逐頁套用**：現有頁面裡寫死的顏色/圓角/陰影（例如 `FieldMappingView.vue` 裡一堆 `#cbd5e1`、`#94a3b8`）不會自動換成 token，各頁排隊之後再個別處理
- **不做按鈕邊緣反光 hover（§6.2）與玻璃效果共用 class/mixin（§5）**：這些是「行為」而非「靜態值」，等第一個真正套用的頁面/元件出現時再抽成 composable/共用 class
- **不完成深色模式**：只確保 token 架構不擋路，不填深色實際色值
- **不改動 Vuetify 元件之外、頁面各自 `<style scoped>` 裡的局部變數**（例如 `PaperPage.vue` 的 `--brand`、`--page-bg`）

## 現況盤點與命名衝突處理

套用 DESIGN_SYSTEM.md 前，先查了現有 token 的實際用量，兩處會撞名或需要決策，其餘皆可直接覆蓋數值：

### 1.`--color-ink` 撞名 → 改名騰位子

現有 `--color-ink`（`#1c2130`）在 **32 個檔案、117 處**當「內文深色文字」用。DESIGN_SYSTEM.md 把同一個名字用在完全不同的角色：「品牌藏青 `#1A3159`」。兩者語意不同，不能只改數值——那會讓 117 處內文文字瞬間變成品牌強調色，而不是文件要的深色文字。

解法：**先把現有 117 處 `var(--color-ink)` 機械改名成 `var(--color-text)`（純改名，數值不變，視覺零影響）**，讓 `--color-ink` 這個名字空出來，之後才定義成文件講的品牌藏青（實際上以 `--color-primary` 為底層來源，見下方對照表）。

### 2. `--color-accent`（金色）：改值不改名

`--color-accent` 目前在 **28 個檔案、167 處**被引用，主要是輸入框/按鈕的 focus 邊框色與 active 文字色。DESIGN_SYSTEM.md 明文金色已淘汰，但這 167 處全部改成硬寫新顏色不合理（都是逐頁排隊之外的範圍）。解法：**保留 `--color-accent` 這個 token 名字，只把底層數值從金色改成藏青**。167 處會自動從金色變藏青，語意上也通（藏青本來就該是互動強調色）；名字何時退場，等對應頁面之後被排到、改寫成直接引用 `--color-ink`/`--color-primary` 時再拿掉。

### 3. 圓角 token 撞名但幾乎沒人用 → 直接覆蓋

`tailwind.css` 現有 `--radius-sm: 2px`／`--radius-lg: 8px`／`--radius-xl: 24px`，跟 DESIGN_SYSTEM.md 要的 `--radius-sm: 8px`／`--radius-md: 12px`／`--radius-lg: 16px` 同名不同值。查過用量：全專案只有 `Introduction.vue` 一處用 `rounded-xl`，`rounded-sm`/`rounded-lg` 完全沒人用。**直接覆蓋成文件的新數值**，`Introduction.vue` 那處圓角會從 24px 變 16px，影響小且在預期內。

### 4. `--color-danger` 不新增，沿用既有 `error`

DESIGN_SYSTEM.md 稱這個角色為「danger」，但 Vuetify 內建插槽本來就叫 `error`，且目前 `--color-error` 完全沒人用（0 處引用），沒有撞名問題。**沿用既有 `--color-error` 這個名字**，不另外造一個 `--color-danger`，兩者同義。

### 5. 其餘新增角色皆無衝突

`ink-strong`、`ink-soft`、`surface-alt`、`page`、`border`、`border-strong`、`success-bg`、`warning-bg`、`danger(error)-bg`、workflow 節點色、圓角/陰影/動畫/內容寬度所有新 token 名稱，都查過現有程式碼零引用，可直接新增。

## 架構

延續現有「Vuetify 是顏色的 source of truth，Tailwind `@theme` 引用 Vuetify 產生的 CSS 變數」模式，不新開一份平行色票：

- **顏色**：能對應到 Vuetify 既有插槽的角色（primary/secondary/background/surface/success/warning/error/accent）直接改插槽數值；插槽沒有對應角色的（`ink-strong`、`surface-alt`、`border`、`border-strong`、三個 `-bg` 徽章底色、workflow 節點色）以 kebab-case 字串當 key 新增到 `theme.colors`（例如 `'ink-strong'`），讓 Vuetify 產生對應的 `--v-theme-ink-strong`；`tailwind.css` 的 `@theme` 區塊比照現有 `--color-success: rgb(var(--v-theme-success))` 的寫法全部橋接一份。
- **非顏色 token**（圓角、陰影、動畫時長/緩動、內容寬度）：Vuetify 主題管不到，直接在 `tailwind.css` 的 `@theme` 區塊新增 CSS 變數；圓角需要對應 Tailwind utility class 的，比照現有 `@utility rounded-lg {...}` 手寫（沿用既有模式，不依賴 Tailwind 自動產生，因為現有檔案的模式就是手寫 `@utility` 來排 layer 優先權）；陰影/動畫/寬度這階段不強制配 Tailwind utility class，元件之後用 `var(--shadow-card)` 這種寫法直接在 scoped `<style>` 引用即可（現有頁面本來就是這樣寫，不是靠 Tailwind class）。
- **全域背景漸層**（§5.4）與 `prefers-reduced-motion` reset（§6.3）：套用在 `body` 層級的全域樣式（沿用現有全域 CSS 檔案，不新建額外入口）。

## Token 對照表

### 色彩

| DESIGN_SYSTEM.md 角色 | 建議值 | 這次的實際 token 名稱 | 說明 |
|---|---|---|---|
| 品牌藏青（ink） | `#1A3159` | `--color-ink`（= Vuetify `primary`） | 原本佔用這個名字的文字色已改名見下 |
| ink-strong | `#12244A` | `--color-ink-strong`（新 key） | hover/按下、標題強調 |
| ink-soft | `#626B7E` | `--color-ink-soft`（= Vuetify `secondary`） | 次要文字、說明、icon |
| 內文文字（原 ink，現 text） | `#1C2130` | `--color-text`（原 `--color-ink` 改名而來，117 處已改名） | |
| surface | `#FFFFFF` | `--color-surface`（Vuetify `surface`，本來就是，無變化） | |
| surface-alt | `#F6F5F2` | `--color-surface-alt`（新 key） | 表頭、hover 背景、工具列 |
| page（頁面底） | `#E4E9ED` | `--color-page`（= Vuetify `background`） | 搭配 §5.4 漸層 |
| border | `#E4E6E8` | `--color-border`（新 key） | |
| border-strong | `#D3D8DC` | `--color-border-strong`（新 key） | |
| success / success-bg | `#1F7A44` / `#DCEDE3` | `--color-success`（Vuetify `success`）/ `--color-success-bg`（新 key） | |
| warning / warning-bg | `#C9822E` / `#F5E9D8` | `--color-warning`（Vuetify `warning`）/ `--color-warning-bg`（新 key） | |
| danger / danger-bg | `#C7392E` / `#F5DEDC` | `--color-error`（Vuetify `error`，沿用既有名字）/ `--color-error-bg`（新 key） | 文件講的「danger」＝這裡的 `error` |
| （deprecated）accent | 金色 → `#1A3159` | `--color-accent`（維持名字，只改數值） | 167 處自動變色，見上方衝突處理 |
| workflow 節點：資料 | `#5B7A9D` | `--color-node-data`（新 key） | |
| workflow 節點：AI/模型 | `#6B5B95` | `--color-node-ai`（新 key） | |
| workflow 節點：人工確認 | 複用 warning | 直接引用 `--color-warning` | |
| workflow 節點：完成 | 複用 success | 直接引用 `--color-success` | |

### 圓角、陰影、動畫、內容寬度

直接照 DESIGN_SYSTEM.md §4.2、§4.3、§6.1、§8.2 的建議值新增，皆無命名衝突：

- 圓角：`--radius-sm`(8px) / `--radius-md`(12px) / `--radius-lg`(16px)；pill 用 Tailwind 內建 `rounded-full`（999px），不另造 token
- 陰影：`--shadow-card` / `--shadow-float`
- 動畫：`--dur-fast`(120ms) / `--dur-base`(200ms) / `--dur-slow`(320ms)、`--ease-out` / `--ease-in-out` / `--ease-spring`
- 內容寬度：`--content-measure`(760px) / `--content-max-width`(1280–1440px) / `--content-max-width-wide`(1680px)

## 立即可見的視覺影響

改完這幾個公版檔案後，**不用等任何一頁被排隊套用**就會馬上看到的變化：

- 所有 Vuetify 內建元件（按鈕、輸入框、進度條、tooltip 底色…）套上藏青主色，不再是現在的米白 `primary`/石板 `secondary`
- 金色 accent 消失（167 處自動變成藏青），例如 `FieldMappingView.vue` 的載入圈圈
- 全站頁面背景從純色變成 §5.4 的柔和漸層底色
- `Introduction.vue` 一處圓角 24px → 16px
- 32 個檔案裡 117 處 `var(--color-ink)` 改名為 `var(--color-text)`（純改名，視覺不變）

**不會變的**：每頁「寫死的顏色/圓角/陰影」（例如各種硬寫的 hex 值）——這些沒有引用 token，維持原樣，等各頁個別排隊套用時才改。

## 深色模式的預留方式

新增的 `--v-theme-*` 色彩變數天生是「每個 Vuetify theme 一份」（`.v-theme--light`/`.v-theme--dark`），架構上已經自然預留位置：這次只定義 `light` theme 底下的值，之後要做深色模式時，直接在 `themes.dark.colors` 補上對應色值即可接上，Tailwind 橋接層完全不用改（因為引用的是 `rgb(var(--v-theme-xxx))`，本來就會跟著當前 theme 切換）。圓角/陰影/動畫/寬度沒有深淺之分，不受影響。這個技術棧下「預留架構」幾乎零額外成本，不用刻意多寫東西。

## 驗收：`/style-guide` 展示頁

新增一頁展示所有 token 實際長相：色票色塊＋色碼、四種按鈕變體（沿用 Vuetify 元件套上新色即可，不用先做反光 hover）、圓角四級、兩種陰影、字級階層、狀態徽章/圓點三色、內容寬度容器示意。**只在 dev 模式掛路由**（`import.meta.env.DEV` 判斷），不進 production build 的導覽，純粹用來對照 token 是否套對。

## 驗證方式

- `npm run build`（含 `vue-tsc` 型別檢查 + vite build）確認無編譯錯誤
- `npm run dev` 打開 `/style-guide` 目視核對色票、圓角、陰影跟 DESIGN_SYSTEM.md 建議值一致
- 目視檢查幾個現有頁面（Hub、mapping、workflow）確認 Vuetify 內建元件顏色套用正確、無「消失」的按鈕（尤其原本用 `color="accent"` 的按鈕/圖示）
- 確認 32 個原用 `--color-ink` 的檔案文字顏色沒有跑掉（改名前後應該視覺零差異）
