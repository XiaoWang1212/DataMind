# 分頁圖表問答（Tab Chat）Design Spec

## 背景

`ConfusionMatrixPanel.vue` 的每個分頁（混淆矩陣/ROC 曲線/PR 曲線/校準曲線/各類別指標）旁邊都有一個 `.cm-insight-panel`，目前只能按「AI 解讀」按鈕，單向生成一段解讀文字（呼叫後端 `PaperRAGService.generate_tab_insight()`）。使用者看完解讀後如果還有疑問（例如想追問某個數字的意義、跟其他分頁的關聯），沒有辦法繼續問下去。

專案裡已經有一個類似但範圍更大的功能可以參考：`PaperRAGService.chat_about_results()`，讓使用者針對整份 workflow 結果（`mining_results`）進行多輪對話，AI 還能自主呼叫 `search_arxiv` 工具查文獻，對應的 UI 在 `frontend/src/views/hub/ResultView.vue`。

這次要做的是它的「分頁限定版」：讓使用者可以針對目前看的這一個分頁（例如 ROC 曲線）繼續追問，但**不**做成整份結果的通用問答，範圍限定在「這張圖表/這次 workflow 執行結果」相關的問題。

## 範圍

- 後端：新增 `PaperRAGService.chat_about_tab()`，重用 `generate_tab_insight()` 已有的「只取該分頁精簡資料」邏輯（`_find_tab_result()` + `_format_tab_data()` + `_MAX_TAB_TEXT_CHARS` 截斷），加上多輪對話能力
- 後端：新增路由 `POST /api/rag/tab-chat`
- 前端：`ConfusionMatrixPanel.vue` 的 `.cm-insight-panel` 下方新增一個對話區塊（訊息串 + 輸入框）
- 前端：對話紀錄存 localStorage，比照現有 `tabInsight_*` 的命名與失效規則
- **不**包含 arXiv 查詢工具（那是「結果總覽」頁面對話功能的定位，不在這個分頁問答的範圍）
- **不**做整份結果的通用問答（那個已經存在，是 `chat_about_results()`）
- **不**用程式硬性過濾使用者輸入的問題內容——範圍限制是透過 system prompt 引導 AI 婉拒離題問題（軟性限制），不是關鍵字黑名單那種硬擋

## 架構

### 後端：`PaperRAGService.chat_about_tab()`

簽章：
```python
def chat_about_tab(
    self,
    mining_results: dict,
    tab: str,
    model_name: str,
    split_name: str,
    history: List[dict],  # [{role: "user"|"model", text: str}]
    message: str,
) -> str
```

邏輯（比照 `generate_tab_insight()` 抓資料的方式，比照 `chat_about_results()` 組多輪對話的方式）：

1. 用 `_find_tab_result(mining_results, model_name, split_name)` 找出對應結果；找不到就直接回傳「找不到對應的結果資料。」，不呼叫 Gemini。
2. 用 `_format_tab_data(result, tab)` 取得該分頁的精簡文字；`None` 就回傳「此分頁沒有可供解讀的資料。」
3. 套用既有的 `_MAX_TAB_TEXT_CHARS` 截斷規則（跟 `generate_tab_insight()` 完全一樣）。
4. 組出開場的 context turns（比照 `chat_about_results()` 的寫法，但範圍縮小到單一分頁，並加入範圍限制指示）：
   ```python
   context_turns = [
       {
           "role": "user",
           "parts": [
               "以下是這次機器學習實驗中「{分頁中文名稱}」的資料，請記住這些資訊，"
               "之後我會針對這個圖表/表格提問。"
               "你只能回答跟這個圖表或這次 workflow 執行結果直接相關的問題；"
               "如果我問到無關的話題（例如其他學術文獻查證、與此資料無關的閒聊），"
               "請禮貌地簡短說明你只能討論這個分頁的內容，不需要展開回答。\n\n"
               f"{tab_text}"
           ],
       },
       {"role": "model", "parts": ["好的，我已經了解這個分頁的資料，請問有什麼問題？"]},
   ]
   ```
   分頁中文名稱沿用 `_TAB_PROMPT_HINTS` 旁邊新增一個對照表（`matrix`→「混淆矩陣」、`roc`→「ROC 曲線」、`pr`→「PR 曲線」、`calibration`→「校準曲線」、`perClass`→「各類別指標」）。
5. 用 `self._model.start_chat(history=context_turns + prior_turns)`（注意：用不帶工具的 `self._model`，不是 `self._chat_model`）送出 `message`，取得 `resp.text`。
6. 例外處理比照 `generate_tab_insight()`：Gemini 呼叫本身的例外、`resp.text` 解析例外都往上拋，讓路由層統一接住、回傳 `success:false`（不像 `chat_about_results()` 那樣把錯誤字串包進回覆文字裡——因為前端要能明確分辨「AI 回覆」跟「呼叫失敗」，跟現有 `tabInsightError` 的錯誤處理方式一致）。

### 後端：路由 `POST /api/rag/tab-chat`

比照 `/tab-insight` 路由的驗證與錯誤處理風格：

```
JSON body:
    - mining_results : 必填
    - tab             : 'matrix' | 'roc' | 'pr' | 'calibration' | 'perClass'，必填
    - model_name      : 必填
    - split_name      : 必填
    - history         : [{role, text}]，選填，預設空陣列
    - message          : 必填

回傳：
    - reply : AI 回覆文字
```

失敗回傳 `{"success": false, "error": "..."}`，狀態碼 500（跟其他 rag 路由一致）。

### 前端：API 封裝

`frontend/src/api/insight.ts` 新增：
```typescript
export interface TabChatMessage {
  role: 'user' | 'model'
  text: string
}

export async function fetchTabChatReply(
  miningResults: Record<string, unknown>,
  tab: string,
  modelName: string,
  splitName: string,
  history: TabChatMessage[],
  message: string,
): Promise<string>
```
錯誤處理比照現有 `fetchTabInsight`（`success:false` 就 `throw new Error(...)`）。

### 前端：`ConfusionMatrixPanel.vue`

**狀態**：仿照現有 `tabInsightCache`（`Map<string, string>`，key 為 `` `${tab}::${model}::${fold}` ``）的模式，新增：
- `tabChatCache = ref<Map<string, TabChatMessage[]>>(new Map())` —— 每個 (tab, model, fold) 組合各自的對話紀錄
- `tabChatInput = ref('')` —— 輸入框內容（切換分頁/模型/fold 時清空，不跟著存）
- `tabChatLoadingKey = ref<string | null>(null)` —— 比照 `tabInsightLoadingKey`，用同一個 key-based 模式避免不同組合互相影響 loading 狀態
- `tabChatError = ref<string | null>(null)`

**行為**：
- 送出問題時，依序：(1) 把目前陣列（尚未包含這輪問題）當作 `history` 參數呼叫 `fetchTabChatReply()`——當輪問題本身是用 `message` 參數單獨傳，不該重複出現在 `history` 裡；(2) 把使用者訊息 push 進畫面陣列、清空輸入框，讓使用者送出後立刻看到自己的問題（不用等 AI 回覆才顯示）；(3) 拿到回覆後，把 `role:'model'` 訊息也 push 進陣列，並存回 localStorage。
- 失敗時：使用者訊息保留在畫面上（不要因為 AI 沒回應就讓使用者的問題憑空消失），顯示錯誤提示，不 push model 訊息。
- 切換 tab/model/fold 時（既有的 `watch([activeTab, selectedModel, selectedFold], ...)`），比照現有邏輯，只從 localStorage 讀取快取，不主動呼叫 API。

**Template**：`.cm-insight-panel` 內、既有的解讀文字/按鈕區塊下方，新增：
- 一條視覺分隔線
- 訊息串（`v-for` 目前 key 對應的 `tabChatCache` 陣列），使用者訊息、AI 訊息用不同對齊/底色區分（純文字氣泡，不需要 `chat-papers` 那種論文卡片）
- 載入中提示（`isCurrentTabChatLoading` computed，比照 `isCurrentTabInsightLoading` 的寫法）
- 錯誤提示（`tabChatError`）
- 輸入框 + 送出按鈕（`<form @submit.prevent>`），`:disabled="!props.projectId || isCurrentTabChatLoading"`，空白輸入不送出

### 前端：localStorage 持久化

`frontend/src/composables/workflow/useWorkflowStorage.ts` 新增：
- `saveTabChatToStorage(tab, model, split, projectId, messages)`
- `loadTabChatFromStorage(tab, model, split, projectId): TabChatMessage[]`
- `clearAllTabChatsFromStorage(projectId)` —— key pattern `` `tabChat_<tab>_<model>_<split>_<projectId>` ``，寫法比照現有 `saveTabInsightToStorage`/`loadTabInsightFromStorage`/`clearAllTabInsightsFromStorage`

`WorkflowWorkspace.vue` 的 `handleApplyColumnConfig()`、`handleContinueSettings()` 這兩處目前呼叫 `clearAllTabInsightsFromStorage(projectId.value)` 的地方，各自旁邊加一行 `clearAllTabChatsFromStorage(projectId.value)`——理由跟解讀快取完全一樣：dataTable/settings 改動導致結果失效時，舊的問答內容（可能引用了已經不存在的數字）也該一起清掉。

## 錯誤處理 / 邊界情況

- `projectId` 未帶入：輸入框/送出按鈕維持 disabled（沿用既有 `:disabled="!props.projectId"` 的模式），跟「AI 解讀」按鈕一致
- 找不到對應結果 / 該分頁無資料：由後端直接回傳固定文字（不呼叫 Gemini），前端當成正常的 AI 回覆顯示即可，不特別區分
- Gemini 呼叫失敗：使用者剛送出的問題保留在訊息串畫面上（不因為 AI 沒回應就消失），並在下方顯示錯誤提示 + 一顆「重試」按鈕（比照現有 `tabInsightError` 的「重試」模式），按下後用同一則使用者訊息、同樣的 history 重新呼叫一次；輸入框在送出後即清空，不用於重試
- 對話輪數：不做上限（跟 `chat_about_results()` 一致，沒有限制歷史輪數），因為 `_MAX_TAB_TEXT_CHARS` 已經限制了每次送給 Gemini 的底層資料量，歷史對話本身通常不會太長

## 測試

- 後端無既有 pytest 套件覆蓋 `paper_rag.py`（`generate_tab_insight()` 當時也沒補測試），這次一致不新增自動化測試，改用手動驗證
- 前端無 vitest，用 `npm run type-check` 做語法/型別檢查
- 人工瀏覽器驗證：
  1. 任一分頁按「AI 解讀」拿到解讀文字後，在下方輸入框問一個追問（例如「這個數字算好還是不好？」），確認能拿到回覆，且回覆內容看起來跟這個分頁的資料相關
  2. 問一個明顯離題的問題（例如「今天天氣如何」），確認 AI 有禮貌地說明只能討論這個分頁內容，而不是隨意作答
  3. 問一個「有沒有論文佐證」的文獻查詢問題，確認 AI 不會嘗試查 arXiv（因為這個分頁對話沒帶工具），而是回覆內容裡沒有論文卡片
  4. 切到另一個分頁再切回來，確認先前的問答紀錄還在
  5. 重新整理頁面，確認問答紀錄還在（localStorage 有正確存取)
  6. 修改 dataTable 欄位設定並確認中斷重跑，確認先前分頁的問答紀錄被清空
  7. 兩個不同分頁分別問不同問題，確認彼此的對話不會混在一起
  8. 沒有 `projectId`（理論上正常操作流程不會發生，但確認按鈕/輸入框 disabled 狀態正確）
