# 深色模式設計

日期：2026-08-31

## 目標

讓 DataMind 全站支援深色模式，使用者可以在側邊欄一鍵切換，首次進站跟隨系統偏好。

不在範圍內：淺色模式的既有配色不做調整；不新增「自動依時間切換」之類的排程行為。

## 現況

`frontend/src/styles/tailwind.css` 的角色 token 幾乎全部寫成 `rgb(var(--v-theme-*))`，指向
Vuetify 的 theme 色票。這代表只要在 `plugins/vuetify.ts` 補一組 `dark` themes，多數元件會自己跟著變。

真正需要處理的是三處把顏色寫死的地方：

1. `styles/main.scss` 的 `.v-application` 頁面漸層——四層 radial/linear，全部是淺色數值
2. `styles/glass.css` 整份——底色、邊框、inset 折射線都是 `rgba(255, 255, 255, …)`
3. 元件層：4 個 `.vue` 檔有寫死 hex（`WorkflowBuilder.vue` 41 處最多），23 個 `.vue` 檔有 `rgba(…)`

## 方向

把深色當成「第二組 token 值」，不是「第二套樣式」。

漸層與玻璃改用 CSS 變數表達（`--page-gradient-*`、`--glass-tint`、`--glass-edge` 等），
在 `.v-theme--light` / `.v-theme--dark` 兩個 scope 各給一組值。元件層的 `rgba(…)` 逐一換成
token 或 `color-mix()`。

這樣元件檔不需要寫任何 `@media (prefers-color-scheme)` 或 `.v-theme--dark .foo` 分支，
之後要調色只動 token 定義處。

考慮過但不採用：

- 全靠 `.v-theme--dark .foo {}` 覆寫。會在 65 個元件裡散出雙份樣式，日後兩邊容易走鐘。
- CSS `filter: invert()`。圖表配色與 workflow 節點分類色會整組壞掉。

## 色票

底色走中性石墨，不帶色相。相對於延續品牌藏青的方案，中性底讓狀態色與節點分類色跳得更開，
資料本身比較好讀；代價是深色模式少了藏青的品牌識別，這是刻意的取捨。

| token | 淺色 | 深色 | 角色 |
|---|---|---|---|
| `background` | `#E4E9ED` | `#141618` | 頁面底（實際被漸層蓋掉，這是 fallback） |
| `surface` | `#FFFFFF` | `#1F2225` | 卡片、面板 |
| `surface-alt` | `#F1F4F8` | `#26292D` | 表頭、hover 底、工具列 |
| `border` | `#E4E6E8` | `#33373C` | 一般分隔線 |
| `border-strong` | `#D3D8DC` | `#454A50` | 強調分隔、輸入框邊界 |
| `text` | `#1C2130` | `#E8EAEC` | 內文 |
| `secondary`（ink-soft） | `#626B7E` | `#9BA1A8` | 次要文字、說明、icon |
| `primary`（ink） | `#1A3159` | `#8FB4EE` | 主要按鈕、選中、重點 |
| `ink-strong` | `#12244A` | `#B4CDF5` | hover/按下、標題強調 |
| `ink-vivid` | `#2B5CA8` | `#5B8FD8` | 已選項目等需要跳出來的地方 |
| `accent` | `#1A3159` | `#8FB4EE` | 未遷移頁面的相容插槽，值跟 primary 同步 |
| `success` | `#3B9A7F` | `#4FC79E` | |
| `warning` | `#C88819` | `#E0A93F` | |
| `error` | `#D7445C` | `#F0687F` | |
| `success-bg` | `#DCEAE5` | `#16342B` | |
| `warning-bg` | `#F7EECF` | `#3A2E12` | |
| `error-bg` | `#F2DEE2` | `#3A1D25` | |
| `success-text` | `#1D6151` | `#6ADCB6` | |
| `warning-text` | `#835A07` | `#F0C46A` | |
| `error-text` | `#A22F43` | `#FF8FA2` | |
| `score-low` | `#E6B800` | `#E8C24A` | 進度條填色，不可當文字色 |

深色的 ink 系列從深藏青翻成淺藍：深底上要維持 4.5:1 就不可能沿用原本的深色值。
色相保持在藏青的範圍內（220° 附近），讓兩個模式仍然是同一個品牌。

量到的對比（皆過 WCAG AA 4.5:1）：

```
13.25  text / surface          7.56  primary / surface
 6.13  ink-soft / surface      9.89  ink-strong / surface
 7.61  success / surface       7.55  warning / surface
 5.32  error / surface
 8.03  success-text / success-bg
 8.11  warning-text / warning-bg
 7.02  error-text / error-bg
```

### workflow 節點分類色

`node-source` 等五個 token 目前是直接當**填色**用（`IconNode.vue` 的 `background`），
上面疊深色 icon 與文字，`chartColors.ts` 也拿它們當圖表系列色。

深色模式維持這個用法，五個值不變。這組粉彩色本來就是中明度，疊在石墨底上依然清楚，
上面的深色文字對比也不受背景影響。翻成「深底＋亮色 icon」會需要動 `IconNode.vue` 的結構，
而且畫布會失去 Orange Data Mining 那組配色語彙——那是當初刻意選的識別。

## 頁面漸層

`main.scss` 現在把四層漸層寫死在 `.v-application`。改成用變數表達每一層的顏色，
在兩個 theme scope 各定義一組。深色版的色塊位置與大小維持不變，只換顏色與不透明度：
主色塊用低彩度的冷灰藍（`rgba(120, 128, 140, .16)`），暖色那層在深色下幾乎看不出來，直接拿掉。

底色由 `linear-gradient(175deg, #1A1C1F, #141618 55%, #101112)` 取代淺色那組。

`WorkflowPage.vue` 蓋在整頁上的 `rgba(255, 255, 255, 0.6)` 白罩同樣改成變數，
深色給一層低不透明度黑罩，維持「畫布區的漸層比 Hub 淡」這個既有意圖。

## 玻璃材質

深色的玻璃走暗場：面板比底色**暗**，靠 `backdrop-filter` 把後面的內容暈進來當亮度來源，
折射線壓細。這是深色 UI 的常見作法，讓內容區看起來在前、面板退到後面。

如果沿用淺色那組構造（白色 rgba 換成中灰、面板比底色亮），深色下會變成一層浮起來的灰霧，
後面的顏色被洗掉。

`glass.css` 的每一項改用變數，兩個 theme 各給一組值：

| 變數 | 淺色 | 深色 |
|---|---|---|
| `--glass-tint-from` | `rgba(255,255,255,.78)` | `rgba(20,22,25,.82)` |
| `--glass-tint-to` | `rgba(255,255,255,.58)` | `rgba(13,14,16,.72)` |
| `--glass-edge` | `rgba(255,255,255,.4)` | `rgba(255,255,255,.09)` |
| `--glass-sheen` | `rgba(255,255,255,.7)` | `rgba(255,255,255,.11)` |
| `--glass-blur` | `blur(14px) saturate(180%)` | `blur(18px) saturate(180%)` |

常駐的側邊欄不透明度比浮層低一階（`.55` / `.40`），讓它跟畫面融在一起而不是壓在上面。

既有的 `prefers-reduced-transparency` 與 `@supports not (backdrop-filter)` 兩個 fallback
一併改成吃變數，深色下退回實色 `surface`。

## 切換

側邊欄（`components/hub/HubSidebar.vue`）放一顆圖示按鈕，在淺／深兩態之間切換，
不提供「跟隨系統」這個第三態——首次載入才讀 `prefers-color-scheme` 當初始值，
使用者按過之後就以他的選擇為準。

狀態放新的 Pinia store `store/themeStore.ts`：

- 讀取順序：`localStorage['datamind-theme']` → `prefers-color-scheme` → `light`
- 切換時同步寫回 `localStorage`，並呼叫 Vuetify 的 `useTheme().change()`
- 在 `App.vue` 掛載時初始化，避免首屏閃一下淺色

側邊欄出現在 Hub、workflow、paper 三個區域，登入與註冊頁沒有。那兩頁沒有切換入口，
但照樣吃當前 theme——它們是進站的第一個畫面，首次載入讀到系統偏好就該直接是對的。

不監聽系統偏好的後續變化：使用者手動選過之後系統再變，不該把他的選擇蓋掉；
還沒選過的情況下重整就會重新讀，夠用了。

## 元件層清理

寫死的顏色分兩批處理：

1. **`rgba(…)`（23 個檔）**——多數是投影、hover 底、半透明覆蓋。投影統一吃
   `--shadow-card` / `--shadow-float`（這兩個也要各給深色值，深色的投影要更重更散）；
   hover 底改成 `color-mix(in oklab, var(--color-ink) 8%, transparent)` 這類寫法。
2. **寫死 hex（4 個檔）**——`WorkflowBuilder.vue` 41 處、`StyleGuideView.vue` 24 處、
   `PaperEditor.vue` 5 處、`CustomSelect.vue` 1 處。逐一對照到最接近的角色 token。
   `StyleGuideView.vue` 是設計系統展示頁，本來就該全部用 token，順手修掉。

`tailwind.css` 裡的 `--color-chat-system: #ffffff` 與 `--color-chat-user: #1a3159`
是聊天氣泡的專用色，也要改成吃 theme 插槽。深色下 AI 氣泡用 `surface-alt`、
使用者氣泡用 `ink-vivid`，維持「一邊靠高度、一邊靠實色」的原本區分方式。

## 驗收

沒有自動化測試，靠逐頁看。兩個模式都要走過一遍：

Hub（專案、專案詳情、框架庫、萃取框架、建立專案、欄位對齊、結果、設定）、
workflow 畫布（含節點面板與各種結果面板）、paper（檢視／編輯兩種模式、引用浮卡、期刊評分面板）、
登入與註冊頁、StyleGuideView。

特別要確認的：切換當下不會有元素卡在舊配色；重整之後維持選擇；玻璃面板在
`prefers-reduced-transparency` 下退回實色仍然可讀。
