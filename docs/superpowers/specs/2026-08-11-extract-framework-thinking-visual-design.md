# 框架提取思考顯示視覺重新設計 Design Spec

## 背景

`ExtractFrameworkView.vue` 剛上線的即時思考串流（見 `docs/superpowers/specs/2026-08-09-extract-framework-thinking-stream-design.md`）目前是固定高度、可捲動的灰色方框，裡面把所有 thought chunk 累積成一段純文字。使用者實際看過後回饋：這個呈現方式體感很差、很無聊，不想要「一個框框 + 純文字」。

透過瀏覽器視覺companion 做了三組活動畫 demo 比較後，使用者選定：**B 流動漸層光暈卡片**，內容行為選 **只顯示最新 1-2 句、舊句淡出**（而非完整累積可捲動）。

此規格只重新設計思考顯示的**呈現層**，不動 SSE 串流、`streamAnalyzeWorkflowFromPdf`、`onResult`/`onError` 邏輯、最終框架結果顯示。

## 範圍

僅修改 `frontend/src/views/hub/ExtractFrameworkView.vue`。不涉及後端、不涉及 `frontend/src/api/gemini.ts`。

## 資料層改動

移除：
- `thoughtLog = ref('')`（累積字串）
- `thoughtLogEl = ref<HTMLElement | null>(null)`（捲動容器 DOM ref）
- `scrollThoughtLogToBottom()`（自動捲到底部函式）
- `displayedThought` computed（原本套用在累積字串上的星號過濾）

新增：
- `currentLine = ref('')`：目前顯示的這一句（去除星號後的文字）
- `previousLine = ref('')`：上一句（去除星號後的文字），顯示為變小變淡的樣式
- `stripMarkdownAsterisks(text: string): string` 小函式（把原本 `displayedThought` 的 `replace(/\*\*?/g, '')` 邏輯抽成獨立函式，供兩個 ref 共用）

`startExtract()` 內的改動：
- 開始前重置：`currentLine.value = ''`、`previousLine.value = ''`（原本是 `thoughtLog.value = ''`）
- `onThought` callback 改為：
  ```ts
  onThought: text => {
    previousLine.value = currentLine.value
    currentLine.value = stripMarkdownAsterisks(text)
  },
  ```
  不再呼叫任何捲動函式（因為沒有捲動容器了）。**觸發時機是每次收到後端 SSE 的一個 `thought` 事件就換一次**，不是固定時間間隔的計時器——後端已經是按語意段落切好的 chunk，不需要額外節流或計時器模擬。

## 視覺設計

**卡片容器**（取代原本的 `.thought-log` 灰色方框）：
- 圓角卡片，背景 `#fafaff`，內距 `16px 18px`
- 邊框用 CSS 偽元素 `::before` 做流動漸層光暈：`linear-gradient(120deg, #6366f1, #a855f7, #6366f1, #a855f7)`，`background-size: 300% 300%`，透過 `mask`/`-webkit-mask` 只顯示邊框那一圈（`padding: 1.5px` 挖空中間），`animation: gradientMove 3s ease infinite` 讓漸層緩慢移動
- 卡片標題「AI 正在思考」，字級 12.5px、粗體、`color: #6366f1`，前面一個會跳動的小圓點（`.b-dot`，`animation: pulse 1.2s ease-in-out infinite`，透過 opacity/scale 做呼吸效果）

**兩行文字：**
- `previousLine`：字級 12.5px，`color: #b8bccb`（淺灰，視覺上退到背景），顯示在上方，`margin-bottom: 4px`；若為空字串則不渲染（`v-if`）
- `currentLine`：字級 14px，`color: #4b5563`（正常文字色），每次更新時用 Vue `<Transition>` 做 `swapIn` 效果（`opacity 0→1` + `translateY(6px→0)`，`0.5s ease`）
- 卡片本身固定 `min-height`（約 3.4em，足夠容納兩行），不設 `max-height`/`overflow-y`（不再需要捲動，因為只顯示兩行）

**版面結構簡化：** 原本 `.extracting-header`（`v-progress-circular` spinner + 「正在提取框架...」文字）整個移除，不再是獨立於卡片之外的一行。卡片標題「AI 正在思考」+ 跳動小圓點取代原本 spinner 的角色，`extracting` 為真時只渲染這一張卡片，不再是「spinner 一行 + 方框一塊」兩層結構。

## 錯誤處理

不變：`onError` 寫入 `extractError`，`extracting.value = false` 時整個卡片（`v-if="extracting"`）連同思考內容一起消失，不自動重試。

## 測試

- 前端無單元測試框架，用 `npm run type-check` + 人工瀏覽器驗證：上傳 PDF、觀察卡片邊框有流動光暈動畫、每次收到新 thought 事件時舊句變淡上移、新句淡入、星號正確被過濾、提取完成後卡片正確消失並顯示結果
