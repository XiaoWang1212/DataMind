# 框架提取 Loading 進度訊息 Design Spec

## 背景

`ExtractFrameworkView.vue` 的「提取框架」流程目前在等待期間只顯示固定文字「正在提取框架...」加一個 spinner。後端 `analyze_pdf`（`backend/services/gemini_service.py`）是單一顆 Gemini LLM call，沒有分階段處理、也沒有回傳任何中間進度訊號（唯一的例外是解析失敗時才會觸發的修復用二次呼叫，屬於錯誤路徑，非設計上的多階段流程）。

因此本次改動採「輪播假進度訊息」：不改動後端與 API 行為，純粹讓前端在等待期間依序顯示幾則預先寫好的階段文字，讓使用者感覺系統正在一步步處理，而不是卡住不動。

## 範圍

僅修改 `frontend/src/views/hub/ExtractFrameworkView.vue`。不涉及後端、不涉及其他頁面。

## 行為設計

- 保留現有的 `v-progress-circular` spinner。
- 文字部分改為依序顯示以下訊息，每則顯示 **2.5 秒**後切換到下一則：
  1. 正在解析 PDF 內容...
  2. 正在辨識研究方法與模型架構...
  3. 正在提取前處理與特徵工程步驟...
  4. 正在整理成框架...
- 播放到最後一則（第 4 則）後**停留在該訊息，不循環回第一則**——避免提取時間超過 10 秒（4 則 × 2.5 秒）時，訊息重新開始讓使用者誤以為處理被重置。
- 訊息切換時用 CSS transition 做淡入淡出，避免文字突然跳動。

## 實作方式

- 新增 `const messageIndex = ref(0)`，訊息陣列存成 `const EXTRACT_MESSAGES = [...]` 常數。
- `startExtract()` 開始時：`messageIndex.value = 0`，並用 `setInterval` 每 2.5 秒把 `messageIndex` 加一，加到陣列最後一個 index 就不再遞增（`clearInterval` 或在 callback 內判斷後跳過）。
- `finally` 區塊內 `clearInterval` 該 timer，避免計時器洩漏或在下一次提取時疊加。
- template 內把原本寫死的 `<span>正在提取框架...</span>` 換成 `<span>{{ EXTRACT_MESSAGES[messageIndex] }}</span>`，外層包 `<Transition name="fade">` 做淡入淡出，搭配對應的 `.fade-enter-active/.fade-leave-active` CSS。

## 測試

- 純前端行為，人工驗證即可：點擊「開始提取」後觀察文字每 2.5 秒切換一次、切換有淡入淡出、播完 4 則後停在最後一則、提取完成或失敗時計時器確實停止（不會在切到其他頁面或重新提取時殘留 interval）。
- 型別檢查：`cd frontend && npm run type-check`。
