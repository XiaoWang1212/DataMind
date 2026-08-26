# 設計系統擴充：資料強調字重、AI 按鈕、驗證方式 step

## 背景

main 分支合併回 `yvonne` 後，帶入了幾個沒有套用 [DESIGN_SYSTEM.md](../../DESIGN_SYSTEM.md) 的畫面（Confusion Matrix、Results Page、Interrupt 確認框）。硬寫的 hex 色值、舊 token 名稱、圓角已經在合併後的清理裡對齊完成（見對應 commit）。這份 spec 處理清理過程中浮現的三個需要「新增規範」而非「套用既有規範」的題目：

1. 資料強調需要比 400/500 更重的字重，但目前 §3 只允許兩檔。
2. 站內散落的「AI 相關操作」按鈕沒有統一樣式，使用者分不出哪些按鈕會觸動 AI。
3. `SettingsPanel.vue` Step 3（驗證方式）用瀏覽器原生 radio/checkbox，沒有套用設計系統。

這三題透過 brainstorming（含瀏覽器 mockup 反覆比對）定案，以下是最終決議與規格。

## 1. 字重：新增 700 為第三檔，限定「資料強調」

**現況**：DESIGN_SYSTEM.md §3 只允許 400（Regular）與 500（Medium），唯一例外是 AI 對話氣泡 `**粗體**` 轉出的 `<strong>`。合併進來的 Confusion Matrix / Results Page 用了大量未經規範的 700，但實測效果（使用者原話：「我覺得我的組員新弄的那個字重還不錯，很明顯」）確實比 400/500 的落差更容易辨識。

**決議**：700 升格為正式的第三檔字重，**只用在「資料強調」**——具體來說：

| 用途 | 字重 | 範例 |
|---|---|---|
| 展示型數字（單一錨點數值） | 700（原規範是 500，這裡上調） | 統計卡的大數字、`.metric-value` |
| 表格裡的最佳值/重點結果 | 700 | Test & Score 表格的最佳分數、對角線格 |
| 資料表格表頭 | 700 | `.ds-table` th、Confusion Matrix 表頭 |

**不變的部分**：

- 頁面標題 h1/h2/h3、一般內文、次要文字、標籤/徽章**全部維持 400/500**，不隨這次擴充放寬。
- AI 對話氣泡 `**粗體**` 例外維持不變，兩者是各自獨立的例外，不合併成同一條規則的兩個子項——粗體的意義不同（一個是「這是重點數據」，一個是「AI 在強調語氣」）。

**DESIGN_SYSTEM.md 待更新處**：

- §3 字重表新增第三行：700，適用範圍寫「資料強調：展示型數字、表格最佳值、表格表頭」。
- §3.1 現有例外說明段落，補一句「700 的第二個合法用途見上表，兩者互相獨立」。
- §7.4 資料表格：表頭字重從「12px，Medium」改成「12px，Bold（700）」。

**受影響的既有程式碼**（合併清理時保留的 700，這次補上規範依據，不需要再改值，只需要在下次經過時視為「有規範撐腰」而非「待清理的違規」）：

- `ConfusionMatrixPanel.vue`：`.cm-cell--diagonal`、`.cm-row--lowest .cm-cell`（表格最佳值）→ 符合規範，保留
- `ConfusionMatrixPanel.vue`：`.cm-header`、`.cm-insight-header`（600）→ **不符合**，600 不在新規範裡，要嘛降回 500、要嘛升到 700，比照「表格表頭用 700」統一升到 700
- `ResultsPage.vue`：`.metric-value`、`.insight-title`（700）→ 展示型數字，符合規範，保留
- `ResultsPage.vue`：`.metric-title`、`.result-table th`、`.model-name`、`.score-best`（700）→ 需要逐一核對：`.metric-title` 是卡片小標題不是數字本身，應降回 500；`.result-table th` 是表頭，符合規範保留；`.model-name`、`.score-best` 是表格內文裡的強調值，符合「表格最佳值」保留
- `ResultsPage.vue`：`.imbalance-badge`（600）→ 不符合規範，是徽章不是資料強調，降回 500

## 2. AI 按鈕：`AppButton` 新增 `ai` 變體

**目的**：讓使用者一眼認出「點下去會觸動 AI」，而不是要重新設計一套視覺語言——全站已經有 `mdi-shimmer` 圖示（WorkflowBuilder 品牌 icon、ResultsPage/ResultView 的 AI 洞察區塊）跟 §7.12 的漸層邊框動畫語言,這次接上既有語彙，不重新發明。

**視覺規格**（mockup 定案版本）：

- **底色**：`linear-gradient(100deg, var(--color-ink-vivid) 0%, var(--color-ink-strong) 100%)`。只用兩個既有 token（`#2B5CA8` → `#12244A`），不新增色相。跟一般 primary 按鈕的純色 `--color-ink` 區分開。
- **圖示**：固定帶 `mdi-shimmer`（若有 `-outline` 版本改用該版本；若無，沿用現行實心版，比照 §3.5.1 例外規則），放在文字左側。
- **文字色**：`var(--color-inverted)`，跟 primary 一致。
- **形狀 / 字級 / padding**：沿用 `AppButton` 現有規格（pill、14px、500），不另訂。
- **hover**：比照 primary 的處理方式，往亮的方向走（`color-mix(in oklab, var(--color-ink-vivid) 88%, white)`），維持「同類元件同一套回饋」原則（§6.2）。

**loading 狀態**（唯一新增的動畫，反覆調整後定案）：

- 底色維持靜止的漸層，**不**加邊框動畫、**不**加圖示裝飾（試過旋轉邊框、公轉光點、脈動光暈、色輪旋轉都被否決，理由分別是「太花俏跟整體安靜風格衝突」「太像心跳」「太不明顯」）。
- 一道光帶斜向掃過：`linear-gradient(100deg, transparent 20%, rgba(241,245,249,0.16) 50%, transparent 80%)`，`background-size: 260% 100%`，2.4s linear 迴圈。不透明度刻意壓低到 0.16（原始版本 0.35 太亮，被否決）、速度放慢、光帶加寬，取得「看得出來在動，但不吵」的平衡。
- 圖示與文字在 loading 期間維持顯示（跟現有 `AppButton` spinner 的「內容隱形」處理不同——AI 按鈕的識別圖示跟文案本身也是「這是 AI 操作」訊號的一部分，蓋掉會失去意義）。

**適用範圍**：只套在明確觸發 AI 運算的按鈕（Confusion Matrix 的 AI 解讀/重新生成、未來其他 AI 洞察觸發點）。一般操作按鈕（送出表單、切換頁籤等）不套用，避免這個變體被濫用成「特別好看的按鈕」而失去語意。

**DESIGN_SYSTEM.md 待更新處**：

- §7.1 按鈕：四變體表格新增第五種 `ai`，附上底色/圖示/loading 規格與適用範圍限制。
- `AppButton.vue`：`variant` prop 的型別加上 `'ai'`，新增對應的 CSS class 與 loading 態實作（沿用現有 `loading` prop，但 `ai` 變體下不觸發預設的圓圈 spinner + 內容隱形邏輯，改用上述光帶動畫）。

**受影響的既有程式碼**：`ConfusionMatrixPanel.vue` 目前自刻的 `.cm-insight-btn`（重試/重新生成/AI 解讀三顆）改用 `<AppButton variant="ai">`，移除對應的自訂 CSS。

## 3. SettingsPanel Step 3（驗證方式）視覺設計

**現況**：6 個驗證方式選項（Cross validation / Cross validation by feature / Random sampling / Leave one out / Test on train data / Test on test data）用瀏覽器原生 `<input type="radio">`，選中時在下方展開對應參數（fold 數、Stratified 勾選、Group column 等），完全沒有套樣式，跟同一個 wizard 裡其他 step（前處理、特徵工程、模型選擇）的視覺不一致。

**決議**（mockup 反覆比較後定案，最終選了「自訂 radio + 精修細節」）：

- **外層容器**：整組選項裝進 `border: 1px solid var(--color-border)`、`border-radius: var(--radius-md)`、`background: var(--color-surface)` 的容器裡（跟其他 step 的 `.item-list` 一樣是「裝在一個東西裡」，不是裸清單）。
- **每一行**：自訂 radio 圓點取代瀏覽器原生樣式。未選中：`border: 1.5px solid var(--color-border-strong)`。選中：邊框與填色改用 `var(--color-node-evaluate)`（§2.3 這個 step 對應的 evaluate 分類色，跟 add-bar、item-idx 等既有元素的 `--step-color` 用法一致）。
- **hover**：整行 `background: var(--color-surface-alt)`，比照 §7.3「卡片內列表 row hover 換 surface-alt 底」的既有規則，`@media (hover: hover) and (pointer: fine)` gate 住。
- **展開的參數**：選中該行時，參數區塊用左側細線（`border-left: 1.5px solid color-mix(in oklab, var(--color-node-evaluate) 35%, transparent)`）接住上面那一行，視覺上讀成「從選中的選項長出來」而非獨立浮動的區塊。
- **連接線對齊點**：對齊選項文字的左緣（不是圓點中心）——實測「對齊文字」比「對齊圓點」視線更連貫，因為往下讀的是參數文字，接續的應該是文字的閱讀線，不是圖形元素的中心線。
- **參數本身**（number input、checkbox、CustomSelect）沿用 Step 0/1 既有的 `.param-num`、`.param-checkbox`、`CustomSelect` 樣式，不新增。

**DESIGN_SYSTEM.md 待更新處**：不需要新增全域規則——這節純粹是套用既有 §7.3（卡片/列表 hover）、§2.3（節點分類色）、§7.10（CustomSelect 已選項語彙的「選中即改色」精神，但這裡具體實作是自訂 radio 而非下拉選單）的既有規則到一個之前漏掉的元件，不寫進 DESIGN_SYSTEM.md 本文，只在 `SettingsPanel.vue` 補上對應樣式。

**受影響的既有程式碼**：`SettingsPanel.vue` 的 `.validation-methods`、`.validation-method`、`.validation-method__radio`、`.validation-method__params` 這幾個 class 需要重寫（目前是最基本的 flex 排列，沒有容器/hover/自訂 radio/連接線）。

## 範圍外（明確不做）

- 不重新評估 400/500 兩檔本身的數值（曾經考慮過改成 450/600，被否決——維持現有兩檔 + 新增第三檔 700，不是全面重新調整）。
- AI 按鈕不擴大到全站「跟 AI 有關」的所有按鈕一次到位，只先套在已知的 AI 觸發點（Confusion Matrix 三顆按鈕），其餘等之後遇到再套。
- 不處理 `ResultsPage.vue` 手動指定 `font-family` 覆蓋全站 Roboto 這件事——這是合併時發現的另一個既有問題，不在這次三個題目範圍內，留待下次經過時處理。
- 不處理 `ProjectDetailView.vue`「生成論文下方留白不足」的回報——程式碼檢查沒發現明顯問題（padding 上下對稱），需要實際看畫面才能判斷，留待下次一起看。

## 實作順序建議

三個題目彼此獨立，可以照風險與依賴排序：

1. **字重**：純 CSS 數值調整 + 補文件，風險最低，先做。
2. **驗證方式 step**：單一元件內的樣式重寫，不影響其他元件，其次做。
3. **AI 按鈕**：新增 `AppButton` 變體會影響共用元件，且要順手把 `ConfusionMatrixPanel.vue` 現有的自刻按鈕換掉，範圍稍大，排最後。
