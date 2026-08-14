# Hub Sidebar 浮動化改版 設計文件

## 背景

`HubSidebar.vue` 是全站共用元件，掛載於 `HubLayout.vue`、`PaperPage.vue`、`WorkflowPage.vue`、`ResultsPage.vue`、`PaperSourcesView.vue` 五個入口。目前是貼齊視窗左緣、上下頂滿的 `position: sticky` 面板，帶一個持續播放的光帶掃過動畫，收合後純圖示排列沒有任何方式得知每個圖示對應哪一頁，收合鈕用方向箭頭表示，跟下方 nav 項目沒有對齊，品牌文字寫的是「研究中心」。

這次改版目標：讓側邊欄看起來像浮在頁面上的卡片、拿掉持續播放的動畫、收合時 hover 圖示能看到頁面名稱、調整圖示尺寸與間距、修正對齊、換一個更常見的收合鈕圖示、品牌文字改為 DataMind，並儘量對齊 `docs/DESIGN_SYSTEM.md` 既有規範（§4 圓角陰影、§5 玻璃、§6 動畫 token、§7.2 側邊欄規格）。

## 範圍

**只改 `HubSidebar.vue` 這一個檔案**，不改動任何掛載它的宿主頁面（見下方「明確排除」）。

## 設計決策

### 1. 浮動效果：維持 `position: sticky`，不改 `fixed`

側邊欄目前是 `.hub-wrap`（flex container）的子項，用 `position: sticky` 貼齊 viewport 頂端，主內容區靠 flex 自然被推開。

若改成 `position: fixed`，側邊欄會脫離文件流，5 個宿主頁面都要各自補上跟展開/收合狀態同步的 `margin-left`，一旦有頁面漏改或側邊欄寬度以後調整，就會跟主內容打架。

改法：**保留 `position: sticky; top: 0;`**，把 `height: 100vh` 改成 `height: calc(100vh - 32px)`，側邊欄自身加 `margin: 16px 0 16px 16px`（top / bottom / left；因為它是 flex item，margin 會被 flex 版面自然吸收，主內容區不用任何改動）。視覺上四邊都會露出底色漸層，跟真的浮動卡片一樣，但完全不影響宿主頁面。

圓角改用 `--radius-lg`（16px，DESIGN_SYSTEM.md §4.2 定義給「大型容器」用）；陰影改用 `--shadow-float`（`0 16px 40px rgba(14,30,66,0.16)`，§4.3 定義給「浮動玻璃面板」用，取代目前寫死的陰影值）。

### 2. Header：品牌文字與對齊修正

- 「研究中心」→「DataMind」，副標「框架分析系統」保留（tagline，收合時隨 `.hub-brand` 一起淡出，邏輯不變）。
- 目前 header 用 `padding: 18px 14px 14px`、nav 用 `padding: 6px 10px` 加上 nav-item 自己的 `padding: 9px 10px`，兩者水平起始點沒有對齊，導致收合鈕跟下方圖示視覺上沒對齊。改法：header 與 nav 共用同一個水平內距數值（沿用 nav-item 目前的 `10px`），讓收合鈕與 nav icon 的左邊界對齊。

### 3. 收合鈕圖示

換成 `mdi-dock-left`（展開狀態顯示，代表「點擊收起側邊欄」）／`mdi-dock-right`（收合狀態顯示，代表「點擊展開」）。這組矩形分兩塊的圖示是 Notion、VS Code 等產品慣用的「側邊面板開關」語意圖示，比原本的 `mdi-chevron-left/right` 方向箭頭更明確。MDI 沒有這組圖示的 outline/filled 變體（本身已是線條化符號），符合 §3.5.1 例外條款，直接使用即可。

### 4. Nav 項目：尺寸與間距

- icon `size` 從 `19` 調到 `22`。
- `.hub-nav-item` 的 `gap` 從 `10px` 調到 `14px`，`padding` 從 `9px 10px` 調到 `11px 12px`。
- 收合狀態下 `.hub-sidebar--collapsed .hub-nav-item` 的置中 padding 數值需依新的 item 尺寸重新抓一次置中位置。

### 5. 選中狀態：維持 DESIGN_SYSTEM.md §7.2 規範

§7.2 明訂側邊欄選中項規則是「較亮的半透明白底 + Medium 字重」——即目前 `hub-nav-item--active { background: rgba(255,255,255,0.72) }` 這套做法。維持不變，不引入新的指示樣式（曾考慮過左側色條方案，決定捨棄以貼合既定文件規範）。深色玻璃版本的對應規則（`rgba(255,255,255,0.18)` 白底）也維持不變。

### 6. 收合時 Hover Tooltip（新增）

`.hub-sidebar--collapsed` 狀態下，每個 `.hub-nav-item` 內新增一個 `<span class="hub-nav-tooltip">{{ item.label }}</span>`：

- 預設 `opacity: 0; transform: translateX(-4px) scale(0.97); pointer-events: none;`
- hover 時 `opacity: 1; transform: translateX(0) scale(1);`
- `transition: opacity var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out);`（150ms 級距，符合 §6.1 `--dur-fast` 用於 hover/小回饋的定義）
- 定位：`position: absolute; left: 100%; top: 50%; transform: translateY(-50%) translateX(-4px) scale(0.97);`（貼在圖示右側）
- 樣式沿用 `.glass-menu` 那套處理「浮動選單疊在不透明卡片上」的 fallback 材質（見 §5.3 已知並接受的下拉選單玻璃牴觸），因為 tooltip 展開後會蓋到主內容區的不透明卡片上，跟下拉選單是同一種情境。
- 整組 hover 規則包在 `@media (hover: hover) and (pointer: fine)` 內，觸控裝置不會卡在 hover 態（沿用專案既有慣例）。
- 深色玻璃版本（`.hub-sidebar--glass-dark`）需要同步一份對應樣式（tooltip 背景色、文字色對比），不能只做淺色版。

### 7. 移除光帶掃過動畫

刪除 `.hub-sidebar::before` 整塊規則與 `@keyframes hub-sidebar-shine`。三顆模糊光暈裝飾（`.orb-1/2/3`）本身是靜態的，不受影響，維持原樣。

## 明確排除（本次不動）

- 登出區塊、footer 版本號區塊的顯示邏輯
- dev-only 玻璃深/淺切換鈕（`hub-glass-toggle`）與兩版玻璃並存的決策
- 展開/收合的寬度 transition（`width var(--dur-base) var(--ease-in-out)`）
- 5 個宿主頁面（`HubLayout.vue`、`PaperPage.vue`、`WorkflowPage.vue`、`ResultsPage.vue`、`PaperSourcesView.vue`）的任何版面/留白邏輯

## 驗證方式

- `npx eslint`、`npm run build` 確認無型別或 lint 錯誤（專案無自動化視覺測試）
- 手動在瀏覽器檢查：
  - 展開/收合切換動作正常，收合鈕圖示兩個方向都正確
  - 5 個宿主頁面逐一確認側邊欄浮動效果、與主內容間距正常（因為改用 sticky + margin，理論上不需要个别調整，但仍要逐頁確認沒有意外的視覺回歸）
  - 收合狀態下 hover 每個圖示，tooltip 在淺色玻璃與深色玻璃版本下都清晰可讀
  - 品牌文字顯示 DataMind
