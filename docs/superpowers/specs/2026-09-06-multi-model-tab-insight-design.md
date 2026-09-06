# ROC/PR 多模型 AI 解讀 Design Spec

## 背景

`ConfusionMatrixPanel.vue` 的 ROC/PR 分頁剛改成多模型疊圖顯示（見 `2026-09-06-multi-model-curve-overlay-design.md`），但「AI 解讀」跟後續的追問聊天功能還是照舊只針對「目前選中的單一模型」講話——因為底層的 `generateTabInsight()`/`fetchTabInsight()`/後端 `generate_tab_insight()` 從設計上就是單模型：一個 `model_name` 字串走到底。使用者現在看到的畫面是多個模型疊在一起比較，AI 解讀卻只講一個模型的事，資訊不對稱、讀起來很奇怪。

這次改動讓 ROC/PR 分頁的 AI 解讀/聊天涵蓋「圖例上目前顯示中（沒被使用者關掉）的模型」，並且明確要求 AI 做跨模型比較。混淆矩陣、校準曲線、逐類別指標三個分頁完全不受影響——這幾個分頁本身仍是單模型檢視，AI 解讀維持現有的單模型邏輯。

## 範圍

- ROC、PR 兩個分頁的 AI 解讀跟聊天：改成涵蓋目前圖例顯示中的所有模型，prompt 明確要求跨模型比較
- **不**動：混淆矩陣、校準曲線、逐類別指標三個分頁的 AI 解讀（維持單模型）
- **不**動：localStorage 的持久化函式簽名（`modelName` 參數本來就只是組 key 用的字串，傳多模型逗號分隔字串進去不用改任何程式碼）
- 快取範圍：ROC/PR 的解讀快取 key 依「目前顯示中的模型集合」區分——關掉/開啟圖例上的模型會被視為不同的解讀範圍，需要重新產生（不是延用舊解讀然後加一句話蒙混過去）

## 後端改動：`backend/services/rag/paper_rag.py`

### 1. 抽出單一模型的曲線格式化邏輯

現有 `_format_tab_data()`（第 516-594 行）裡 `tab in ("roc", "pr")` 那段（第 533-554 行）抽成獨立函式：

```python
def _format_roc_pr_curve_text(self, result: dict, tab: str) -> Optional[str]:
    """單一模型的 ROC/PR 曲線格式化文字（不含【ROC 曲線】這種外層標題，
    給單模型跟多模型兩條路徑共用，各自決定要不要加標題/模型名稱前綴）。
    """
    curve = result.get("roc_pr_curve")
    if not curve:
        return None
    metric_key = "auc" if tab == "roc" else "auprc"
    metric_val = next(
        (m.get("value") for m in result.get("metrics", []) if m.get("metric") == metric_key),
        None,
    )
    sub = curve.get("roc" if tab == "roc" else "pr", {})
    xs_key, ys_key = ("fpr", "tpr") if tab == "roc" else ("recall", "precision")
    points = self._sample_curve_points(sub.get(xs_key, []), sub.get(ys_key, []))
    points_str = "、".join(f"({x:.2f}, {y:.2f})" for x, y in points) or "N/A"
    metric_label = "AUC" if tab == "roc" else "AUPRC"
    metric_str = f"{metric_val:.4f}" if isinstance(metric_val, (int, float)) else "N/A"
    axis_label = "FPR, TPR" if tab == "roc" else "Recall, Precision"
    return (
        f"正類：{curve.get('pos_label', 'N/A')}\n"
        f"{metric_label}：{metric_str}\n"
        f"取樣座標點（{axis_label}）：{points_str}"
    )
```
`_format_tab_data()` 裡原本的 `tab in ("roc", "pr")` 分支改成呼叫這個新函式並補回外層標題：
```python
if tab in ("roc", "pr"):
    curve_text = self._format_roc_pr_curve_text(result, tab)
    if curve_text is None:
        return None
    return f"【{'ROC' if tab == 'roc' else 'PR'} 曲線】\n{curve_text}"
```
（其餘分支：`matrix`/`calibration`/`perClass` 完全不動）

### 2. 新增多模型查找與格式化函式

在 `_find_tab_result()`（第 504-514 行）之後新增：
```python
def _find_tab_results(
    self, mining_results: dict, model_names: List[str], split_name: str
) -> List[dict]:
    """依 model_names 的順序回傳所有符合的結果；跳過找不到或有 error 的模型，
    不因為某個模型缺資料就整批失敗——這是刻意的寬鬆行為，圖例上顯示中的模型
    理論上都該有資料，這裡只是防禦性處理。
    """
    by_key = {
        (r.get("model_name"), r.get("split_name")): r
        for r in mining_results.get("results", [])
        if "error" not in r
    }
    return [
        by_key[(name, split_name)]
        for name in model_names
        if (name, split_name) in by_key
    ]

def _format_multi_model_curve_data(self, results: List[dict], tab: str) -> Optional[str]:
    """把多個模型的 ROC/PR 曲線資料組成一段文字，每個模型各自一個 ▶ 區塊，
    照抄 _format_datamind_output() 既有的分段慣例。"""
    blocks = []
    for result in results:
        curve_text = self._format_roc_pr_curve_text(result, tab)
        if curve_text is None:
            continue
        blocks.append(f"▶ {result.get('model_name', 'N/A')}\n{curve_text}")
    if not blocks:
        return None
    header = "【ROC 曲線】" if tab == "roc" else "【PR 曲線】"
    return f"{header}\n\n" + "\n\n".join(blocks)
```

### 3. `generate_tab_insight()` 新增多模型路徑

現有簽名（第 596-597 行）：
```python
def generate_tab_insight(
    self, mining_results: dict, tab: str, model_name: str, split_name: str
) -> str:
```
改成：
```python
def generate_tab_insight(
    self, mining_results: dict, tab: str, model_name: str, split_name: str,
    model_names: Optional[List[str]] = None,
) -> str:
    """針對 workflow 結果裡某個分頁生成一段繁體中文解讀。

    model_names 有帶值（非空 list）時走多模型比較路徑（目前只有 ROC/PR 分頁的
    前端會帶這個參數）；否則維持原本的單一 (model_name × split_name) 路徑，
    matrix/calibration/perClass 分頁完全不受影響。
    """
    if model_names:
        results = self._find_tab_results(mining_results, model_names, split_name)
        if not results:
            return "找不到對應的結果資料。"

        tab_text = self._format_multi_model_curve_data(results, tab)
        if tab_text is None:
            return "此分頁沒有可供解讀的資料。"

        if len(tab_text) > self._MAX_TAB_TEXT_CHARS:
            tab_text = tab_text[: self._MAX_TAB_TEXT_CHARS] + "\n…（資料量過大，僅取部分內容）"

        ideal_hint = "ROC 曲線越靠左上角" if tab == "roc" else "PR 曲線越靠右上角"
        hint = self._TAB_PROMPT_HINTS.get(tab, "")
        prompt = (
            "你是資料科學顧問，正在協助解讀一份醫學研究的機器學習分類結果。\n"
            f"以下是 {len(results)} 個模型在「{split_name}」這筆結果的"
            f"{'ROC' if tab == 'roc' else 'PR'} 曲線資料，請比較它們的表現：\n\n"
            f"{tab_text}\n\n"
            f"請用繁體中文寫 3 到 5 句話的解讀，明確指出哪個模型的表現最接近理想"
            f"（{ideal_hint}），並簡短說明其他模型的相對表現。{hint}\n"
            "請「只」輸出解讀本身，不要加上任何標題、條列符號或多餘說明文字。"
        )
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        text = self._call_gemini(prompt, usage_total)
        if text.startswith("（生成失敗："):
            raise RuntimeError(text)
        return text.strip()

    # 單模型路徑（既有邏輯，完全不動）
    result = self._find_tab_result(mining_results, model_name, split_name)
    if result is None:
        return "找不到對應的結果資料。"

    tab_text = self._format_tab_data(result, tab)
    if tab_text is None:
        return "此分頁沒有可供解讀的資料。"

    if len(tab_text) > self._MAX_TAB_TEXT_CHARS:
        tab_text = tab_text[: self._MAX_TAB_TEXT_CHARS] + "\n…（資料量過大，僅取部分內容）"

    hint = self._TAB_PROMPT_HINTS.get(tab, "")
    prompt = (
        "你是資料科學顧問，正在協助解讀一份醫學研究的機器學習分類結果。\n"
        f"以下是模型「{model_name}」在「{split_name}」這筆結果的資料：\n\n"
        f"{tab_text}\n\n"
        f"請用繁體中文寫 2 到 4 句話的解讀。{hint}\n"
        "請「只」輸出解讀本身，不要加上任何標題、條列符號或多餘說明文字。"
    )
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    text = self._call_gemini(prompt, usage_total)
    if text.startswith("（生成失敗："):
        raise RuntimeError(text)
    return text.strip()
```

### 4. `chat_about_tab()` 新增多模型路徑

現有簽名（第 625-633 行）：
```python
def chat_about_tab(
    self,
    mining_results: dict,
    tab: str,
    model_name: str,
    split_name: str,
    history: List[dict],
    message: str,
) -> str:
```
改成新增同樣的 `model_names: Optional[List[str]] = None` 參數，邏輯結構跟 `generate_tab_insight()` 一樣分兩條路徑——多模型路徑用 `_find_tab_results`/`_format_multi_model_curve_data` 組出 context，`context_turns` 的開場白從「以下是這次機器學習實驗中「{tab_label}」的資料」改成「以下是這次機器學習實驗中「{tab_label}」的資料（{N} 個模型的比較）」，其餘聊天邏輯（`self._model.start_chat()`、`history`/`message` 處理）完全不變。單模型路徑維持現有程式碼不動。

## 路由改動：`backend/routes/rag.py`

`/tab-insight`（第 563-596 行）與 `/tab-chat`（第 599-634 行）都做同樣的改動：
```python
model_name = data.get("model_name")
model_names = data.get("model_names")
if not tab or not split_name or (not model_name and not model_names):
    return jsonify({
        "success": False,
        "error": "tab、split_name 為必填欄位，且 model_name/model_names 至少要有一個",
    }), 400
```
呼叫 service 時多帶一個 `model_names=model_names`：
```python
insight = service.generate_tab_insight(
    data["mining_results"], tab, model_name, split_name, model_names=model_names,
)
```
（`/tab-chat` 同理，`reply = service.chat_about_tab(..., model_names=model_names)`）

## 前端改動

### 1. `frontend/src/api/insight.ts`

`fetchTabInsight`/`fetchTabChatReply` 的 `modelName: string` 參數改成 `model: string | string[]`：
```typescript
export async function fetchTabInsight (
  miningResults: Record<string, unknown>,
  tab: string,
  model: string | string[],
  splitName: string,
): Promise<string> {
  const response = await fetch('/api/rag/tab-insight', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mining_results: miningResults,
      tab,
      split_name: splitName,
      ...(Array.isArray(model) ? { model_names: model } : { model_name: model }),
    }),
  })
  // ...其餘不變
}
```
`fetchTabChatReply` 同樣改法（多帶 `history`/`message` 兩個既有參數，不受影響）。

### 2. `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`

新增（放在 `hiddenModels`/`groupedResults` 附近）：
```typescript
const visibleModelNames = computed(() =>
  groupedResults.value
    .filter(g => !hiddenModels.value.has(g.model_name))
    .map(g => g.model_name),
)

// ROC/PR 用「目前顯示中的模型集合」當作 AI 解讀的範圍；其他分頁維持單一 selectedModel，
// 排序是為了同一組模型不管使用者關閉/開啟的先後順序，都對應到同一個快取 key
const insightModelParam = computed<string | string[]>(() => {
  if (activeTab.value === 'roc' || activeTab.value === 'pr') {
    return [...visibleModelNames.value].sort()
  }
  return selectedModel.value
})
```

`tabInsightCacheKey()`（第 629-631 行）型別擴充，改用下面新增的 `modelParamToString()`：
```typescript
function tabInsightCacheKey (tab: TabKey, model: string | string[], fold: string): string {
  return `${tab}::${modelParamToString(model)}::${fold}`
}
```

以下位置把 `selectedModel.value` 換成 `insightModelParam.value`（其餘邏輯不動）：
- `currentTabInsightKey`（第 633-635 行）
- `generateTabInsight()` 裡的 `const model = selectedModel.value`（第 646 行）
- `requestTabChatReply()` 的呼叫端：`sendTabChatMessage()`（第 761 行）、`retryTabChatMessage()`（第 788 行）
- 自動載入快取的 `watch([activeTab, selectedModel, selectedFold], ...)`（第 799、804 行）——依賴陣列裡的 `selectedModel` 也要換成 `insightModelParam`，改成 `watch([activeTab, insightModelParam, selectedFold], ...)`，這樣使用者切換圖例顯示/隱藏某個模型時，這個 watch 才會重新檢查 localStorage 快取

`hasCurrentTabData`（第 614-622 行）的 ROC/PR 分支：
```typescript
const hasCurrentTabData = computed(() => {
  switch (activeTab.value) {
    case 'matrix': return currentMatrix.value !== null
    case 'roc':
    case 'pr': return visibleModelNames.value.length > 0
    case 'calibration': return currentCalibrationCurve.value !== null
    // ...perClass 分支不變
  }
})
```

`fetchTabInsight`/`fetchTabChatReply` 的呼叫端（`generateTabInsight()`、`requestTabChatReply()`）把原本傳 `model`（字串）的地方改傳 `insightModelParam.value`（可能是字串或陣列，函式簽名已經支援兩種）。

`saveTabInsightToStorage`/`loadTabInsightFromStorage`/`saveTabChatToStorage`/`loadTabChatFromStorage` 這幾個函式的簽名不用改——它們的 `modelName` 參數本來就只是拿來組 localStorage key 用的字串，不做任何模型名稱相關的邏輯判斷。但呼叫這些函式的地方，現在拿到的是 `insightModelParam.value`（可能是字串或陣列），不能直接傳陣列進去，要先轉成字串。新增一個共用的轉換函式，跟 `tabInsightCacheKey()` 內部用的是同一套邏輯：
```typescript
function modelParamToString (model: string | string[]): string {
  return Array.isArray(model) ? model.join(',') : model
}
```
`tabInsightCacheKey()` 直接呼叫這個函式取代原本內聯的三元判斷；所有呼叫 `saveTabInsightToStorage`/`loadTabInsightFromStorage`/`saveTabChatToStorage`/`loadTabChatFromStorage` 的地方，第二個參數一律改成 `modelParamToString(insightModelParam.value)`。

## 邊界情況

- 使用者把 ROC/PR 圖例上的模型全部關掉：`visibleModelNames` 變空陣列，`hasCurrentTabData` 回傳 `false`，AI 解讀區塊整個不顯示（跟現有「沒有資料」的行為一致，不會呼叫 API 傳空陣列給後端）
- 後端 `_find_tab_results` 收到的 `model_names` 裡有些模型在該 fold 沒有結果（例如舊資料、部分模型執行失敗）：跳過缺資料的模型，不因此整批失敗；如果全部都找不到才回傳「找不到對應的結果資料」
- 使用者先產生了「顯示全部模型」的解讀，關掉一個模型再回來看 ROC 分頁：因為 `insightModelParam`（進而 `currentTabInsightKey`）變了，會視為新的組合，`currentTabInsight` 從快取讀不到值，畫面顯示「尚未產生」，需要使用者重新按「AI 解讀」——這是刻意的行為（見 brainstorming 階段的選擇），不是 bug
- 混淆矩陣/校準曲線/逐類別指標分頁：`insightModelParam` 一律回傳 `selectedModel.value`（字串），跟改動前完全一樣的行為，不受影響

## 測試

後端：
- 手動確認 `_find_tab_results()` 對「部分模型缺資料」「全部模型都缺資料」「正常情況」三種輸入的回傳結果
- 手動確認 `generate_tab_insight()`/`chat_about_tab()` 在 `model_names` 為 `None`／空陣列／非空陣列三種情況下，各自走到正確的路徑（單模型 vs 多模型），且單模型路徑產生的文字內容跟改動前逐字一致（回歸驗證）

前端：
- `npm run type-check`（在 `datamind-frontend` container 內跑）
- 人工瀏覽器驗證：
  1. 進 ROC 分頁，圖例全部顯示時按「AI 解讀」，確認生成的文字有提到多個模型並做比較（點名表現最好的模型）
  2. 關掉圖例上的某個模型，確認「AI 解讀」區塊變回「尚未產生」的狀態，重新產生後的內容只涵蓋還顯示中的模型
  3. 針對這個多模型解讀繼續追問（聊天），確認 AI 的回覆有考慮到所有目前顯示中的模型的資料，不是只回答其中一個
  4. 切到混淆矩陣分頁，確認 AI 解讀維持單模型行為，跟改動前一樣
  5. 把 ROC 圖例上全部模型都關掉，確認「AI 解讀」區塊整個消失（跟「此分頁沒有資料」時的畫面一致）
