# ROC/PR 多模型 AI 解讀 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 ROC/PR 分頁的 AI 解讀跟聊天涵蓋「圖例上目前顯示中的所有模型」並做跨模型比較，而不是只針對單一選中的模型。混淆矩陣、校準曲線、逐類別指標三個分頁完全不受影響。

**Architecture:** 後端 `generate_tab_insight()`/`chat_about_tab()` 新增選填的 `model_names: Optional[List[str]]` 參數，有帶值走新的多模型比較路徑（新函式 `_find_tab_results()`/`_format_multi_model_curve_data()`），沒帶維持現有單模型邏輯完全不動。路由層新增 `model_names` 這個選填欄位，跟既有 `model_name` 二選一。前端新增 `visibleModelNames`/`insightModelParam` 兩個 computed，把「圖例上顯示中的模型清單」餵進既有的 AI 解讀/聊天呼叫鏈，取代原本寫死的 `selectedModel.value`。

**Tech Stack:** Python 3.11 + Flask（後端）；Vue 3 `<script setup>` + TypeScript（前端）。

## Global Constraints

- 只影響 ROC、PR 兩個分頁；混淆矩陣、校準曲線、逐類別指標三個分頁的 AI 解讀/聊天完全不能受影響（單模型路徑的既有程式碼跟輸出文字都要維持逐字不變）
- `model_names` 是選填參數，沒帶時的行為必須跟改動前完全一致（回歸相容）
- 快取範圍依「目前顯示中的模型集合」區分——切換圖例會被視為不同的解讀範圍
- localStorage 持久化函式（`saveTabInsightToStorage` 等）的函式簽名不能改，呼叫端自行把模型參數轉成字串再傳入
- 前端型別檢查在 `datamind-frontend` container 內執行（`docker exec datamind-frontend sh -c "cd /app && npm run type-check"`）
- 直接在 `main` branch 上工作，不開額外 git worktree

---

### Task 1: 後端 `paper_rag.py`——抽出共用邏輯 + 新增多模型函式

**Files:**
- Modify: `backend/services/rag/paper_rag.py`
- Create: `backend/tests/test_paper_rag_tab_insight.py`

**Interfaces:**
- Produces: `_format_roc_pr_curve_text(self, result: dict, tab: str) -> Optional[str]`（單一模型的 ROC/PR 曲線文字，不含外層〈標題〉）
- Produces: `_find_tab_results(self, mining_results: dict, model_names: List[str], split_name: str) -> List[dict]`
- Produces: `_format_multi_model_curve_data(self, results: List[dict], tab: str) -> Optional[str]`
- Produces: `generate_tab_insight(self, mining_results, tab, model_name, split_name, model_names: Optional[List[str]] = None) -> str`（新增選填參數，Task 3 的前端會用到這個參數名稱）
- Produces: `chat_about_tab(self, mining_results, tab, model_name, split_name, history, message, model_names: Optional[List[str]] = None) -> str`（新增選填參數）

- [ ] **Step 1: 抽出 `_format_roc_pr_curve_text()`**

`backend/services/rag/paper_rag.py` 現有的 `_format_tab_data()`（第 516-594 行）裡，找到這段（第 533-554 行）：
```python
        if tab in ("roc", "pr"):
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
                f"【{'ROC' if tab == 'roc' else 'PR'} 曲線】\n"
                f"正類：{curve.get('pos_label', 'N/A')}\n"
                f"{metric_label}：{metric_str}\n"
                f"取樣座標點（{axis_label}）：{points_str}"
            )
```
改成：
```python
        if tab in ("roc", "pr"):
            curve_text = self._format_roc_pr_curve_text(result, tab)
            if curve_text is None:
                return None
            return f"【{'ROC' if tab == 'roc' else 'PR'} 曲線】\n{curve_text}"
```
在 `_format_tab_data()`（第 516 行）之前新增：
```python
    def _format_roc_pr_curve_text(self, result: dict, tab: str) -> Optional[str]:
        """單一模型的 ROC/PR 曲線格式化文字（不含【ROC 曲線】這種外層標題），
        給單模型跟多模型兩條路徑共用，各自決定要不要加標題/模型名稱前綴。
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

- [ ] **Step 2: 語法檢查**

Run:
```bash
docker cp backend/services/rag/paper_rag.py datamind-backend:/tmp/paper_rag.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/paper_rag.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 3: 新增 `_find_tab_results()` 與 `_format_multi_model_curve_data()`**

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

- [ ] **Step 4: 語法檢查**

Run:
```bash
docker cp backend/services/rag/paper_rag.py datamind-backend:/tmp/paper_rag.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/paper_rag.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 5: `generate_tab_insight()` 新增多模型路徑**

現有簽名跟函式本體（第 596-623 行）：
```python
    def generate_tab_insight(
        self, mining_results: dict, tab: str, model_name: str, split_name: str
    ) -> str:
        """針對 workflow 結果裡某個 (model × fold) 的單一分頁資料，生成一段繁體中文解讀。"""
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
整段改成：
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

- [ ] **Step 6: `chat_about_tab()` 新增多模型路徑**

現有簽名跟函式本體（第 625-670 行）：
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
        """針對 workflow 結果裡某個 (model × fold) 的單一分頁資料，跟使用者進行範圍限定的多輪問答。

        跟 chat_about_results() 不同：這裡不帶 arXiv 查詢工具（用不帶 tools 的 self._model，
        不是 self._chat_model），範圍限定在這個分頁的資料，不做例外處理——Gemini 呼叫本身的
        例外、resp.text 解析例外都直接往上拋，讓路由層統一接住、回傳 success:false。
        """
        result = self._find_tab_result(mining_results, model_name, split_name)
        if result is None:
            return "找不到對應的結果資料。"

        tab_text = self._format_tab_data(result, tab)
        if tab_text is None:
            return "此分頁沒有可供解讀的資料。"

        if len(tab_text) > self._MAX_TAB_TEXT_CHARS:
            tab_text = tab_text[: self._MAX_TAB_TEXT_CHARS] + "\n…（資料量過大，僅取部分內容）"

        tab_label = self._TAB_LABELS.get(tab, tab)
        context_turns = [
            {
                "role": "user",
                "parts": [
                    f"以下是這次機器學習實驗中「{tab_label}」的資料，請記住這些資訊，"
                    "之後我會針對這個圖表/表格提問。"
                    "你只能回答跟這個圖表或這次 workflow 執行結果直接相關的問題；"
                    "如果我問到無關的話題（例如其他學術文獻查證、與此資料無關的閒聊），"
                    "請禮貌地簡短說明你只能討論這個分頁的內容，不需要展開回答。\n\n"
                    f"{tab_text}"
                ],
            },
            {"role": "model", "parts": [f"好的，我已經了解「{tab_label}」這個分頁的資料，請問有什麼問題？"]},
        ]
        prior_turns = [{"role": h["role"], "parts": [h["text"]]} for h in history]

        chat = self._model.start_chat(history=context_turns + prior_turns)
        resp = chat.send_message(message)
        return (getattr(resp, "text", "") or "").strip()
```
整段改成：
```python
    def chat_about_tab(
        self,
        mining_results: dict,
        tab: str,
        model_name: str,
        split_name: str,
        history: List[dict],
        message: str,
        model_names: Optional[List[str]] = None,
    ) -> str:
        """針對 workflow 結果裡某個分頁的資料，跟使用者進行範圍限定的多輪問答。

        model_names 有帶值時，context 涵蓋多個模型的資料（目前只有 ROC/PR 分頁的前端
        會帶這個參數）；否則維持原本單一 (model_name × split_name) 的既有邏輯。

        跟 chat_about_results() 不同：這裡不帶 arXiv 查詢工具（用不帶 tools 的 self._model，
        不是 self._chat_model），範圍限定在這個分頁的資料，不做例外處理——Gemini 呼叫本身的
        例外、resp.text 解析例外都直接往上拋，讓路由層統一接住、回傳 success:false。
        """
        tab_label = self._TAB_LABELS.get(tab, tab)

        if model_names:
            results = self._find_tab_results(mining_results, model_names, split_name)
            if not results:
                return "找不到對應的結果資料。"

            tab_text = self._format_multi_model_curve_data(results, tab)
            if tab_text is None:
                return "此分頁沒有可供解讀的資料。"

            if len(tab_text) > self._MAX_TAB_TEXT_CHARS:
                tab_text = tab_text[: self._MAX_TAB_TEXT_CHARS] + "\n…（資料量過大，僅取部分內容）"

            context_turns = [
                {
                    "role": "user",
                    "parts": [
                        f"以下是這次機器學習實驗中「{tab_label}」的資料（{len(results)} 個模型的比較），"
                        "請記住這些資訊，之後我會針對這個圖表提問。"
                        "你只能回答跟這個圖表或這次 workflow 執行結果直接相關的問題；"
                        "如果我問到無關的話題（例如其他學術文獻查證、與此資料無關的閒聊），"
                        "請禮貌地簡短說明你只能討論這個分頁的內容，不需要展開回答。\n\n"
                        f"{tab_text}"
                    ],
                },
                {"role": "model", "parts": [f"好的，我已經了解「{tab_label}」這個分頁的資料，請問有什麼問題？"]},
            ]
            prior_turns = [{"role": h["role"], "parts": [h["text"]]} for h in history]

            chat = self._model.start_chat(history=context_turns + prior_turns)
            resp = chat.send_message(message)
            return (getattr(resp, "text", "") or "").strip()

        # 單模型路徑（既有邏輯，完全不動）
        result = self._find_tab_result(mining_results, model_name, split_name)
        if result is None:
            return "找不到對應的結果資料。"

        tab_text = self._format_tab_data(result, tab)
        if tab_text is None:
            return "此分頁沒有可供解讀的資料。"

        if len(tab_text) > self._MAX_TAB_TEXT_CHARS:
            tab_text = tab_text[: self._MAX_TAB_TEXT_CHARS] + "\n…（資料量過大，僅取部分內容）"

        context_turns = [
            {
                "role": "user",
                "parts": [
                    f"以下是這次機器學習實驗中「{tab_label}」的資料，請記住這些資訊，"
                    "之後我會針對這個圖表/表格提問。"
                    "你只能回答跟這個圖表或這次 workflow 執行結果直接相關的問題；"
                    "如果我問到無關的話題（例如其他學術文獻查證、與此資料無關的閒聊），"
                    "請禮貌地簡短說明你只能討論這個分頁的內容，不需要展開回答。\n\n"
                    f"{tab_text}"
                ],
            },
            {"role": "model", "parts": [f"好的，我已經了解「{tab_label}」這個分頁的資料，請問有什麼問題？"]},
        ]
        prior_turns = [{"role": h["role"], "parts": [h["text"]]} for h in history]

        chat = self._model.start_chat(history=context_turns + prior_turns)
        resp = chat.send_message(message)
        return (getattr(resp, "text", "") or "").strip()
```

- [ ] **Step 7: 語法檢查**

Run:
```bash
docker cp backend/services/rag/paper_rag.py datamind-backend:/tmp/paper_rag.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/paper_rag.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 8: 建立測試檔**

建立 `backend/tests/test_paper_rag_tab_insight.py`：
```python
"""ROC/PR 多模型 AI 解讀的新函式測試。

不連網：用 PaperRAGService.__new__(PaperRAGService) 繞過 __init__（不需要
GEMINI_API_KEY），純邏輯的函式（_find_tab_results/_format_multi_model_curve_data/
_format_roc_pr_curve_text）直接呼叫；需要呼叫 Gemini 的函式（generate_tab_insight/
chat_about_tab）monkeypatch 掉 service._call_gemini，理由同
test_paper_rag_section_prompt.py 開頭註解。
"""

from services.rag.paper_rag import PaperRAGService


def make_result(model_name, split_name="fold_1", fpr=None, tpr=None, recall=None, precision=None, auc=0.85):
    return {
        "model_name": model_name,
        "split_name": split_name,
        "roc_pr_curve": {
            "pos_label": "1",
            "roc": {"fpr": fpr or [0.0, 0.5, 1.0], "tpr": tpr or [0.0, 0.8, 1.0]},
            "pr": {"recall": recall or [0.0, 0.5, 1.0], "precision": precision or [1.0, 0.9, 0.5]},
        },
        "metrics": [{"metric": "auc", "value": auc}, {"metric": "auprc", "value": 0.75}],
    }


def make_service():
    return PaperRAGService.__new__(PaperRAGService)


def test_find_tab_results_returns_in_requested_order():
    service = make_service()
    mining_results = {
        "results": [
            make_result("SVM"),
            make_result("Random Forest"),
            make_result("Logistic Regression"),
        ]
    }
    results = service._find_tab_results(
        mining_results, ["Logistic Regression", "SVM"], "fold_1",
    )
    assert [r["model_name"] for r in results] == ["Logistic Regression", "SVM"]


def test_find_tab_results_skips_missing_models():
    service = make_service()
    mining_results = {"results": [make_result("SVM")]}
    results = service._find_tab_results(
        mining_results, ["SVM", "不存在的模型"], "fold_1",
    )
    assert [r["model_name"] for r in results] == ["SVM"]


def test_find_tab_results_skips_error_rows():
    service = make_service()
    errored = make_result("SVM")
    errored["error"] = "訓練失敗"
    mining_results = {"results": [errored]}
    results = service._find_tab_results(mining_results, ["SVM"], "fold_1")
    assert results == []


def test_format_multi_model_curve_data_builds_one_block_per_model():
    service = make_service()
    results = [make_result("SVM"), make_result("Random Forest")]
    text = service._format_multi_model_curve_data(results, "roc")
    assert text is not None
    assert "【ROC 曲線】" in text
    assert "▶ SVM" in text
    assert "▶ Random Forest" in text
    assert text.index("▶ SVM") < text.index("▶ Random Forest")


def test_format_multi_model_curve_data_skips_models_without_curve():
    service = make_service()
    no_curve = make_result("SVM")
    no_curve["roc_pr_curve"] = None
    results = [no_curve, make_result("Random Forest")]
    text = service._format_multi_model_curve_data(results, "roc")
    assert text is not None
    assert "▶ SVM" not in text
    assert "▶ Random Forest" in text


def test_format_multi_model_curve_data_returns_none_when_all_missing():
    service = make_service()
    no_curve = make_result("SVM")
    no_curve["roc_pr_curve"] = None
    text = service._format_multi_model_curve_data([no_curve], "roc")
    assert text is None


def test_generate_tab_insight_multi_model_prompt_mentions_all_models_and_asks_for_comparison():
    service = make_service()
    captured_prompt = {}

    def fake_call_gemini(prompt, usage_total):
        captured_prompt["value"] = prompt
        return "SVM 的表現最好。"

    service._call_gemini = fake_call_gemini
    mining_results = {"results": [make_result("SVM"), make_result("Random Forest")]}

    text = service.generate_tab_insight(
        mining_results, "roc", "SVM", "fold_1", model_names=["SVM", "Random Forest"],
    )

    assert text == "SVM 的表現最好。"
    prompt = captured_prompt["value"]
    assert "SVM" in prompt
    assert "Random Forest" in prompt
    assert "請比較它們的表現" in prompt
    assert "明確指出哪個模型的表現最接近理想" in prompt
    assert "2 個模型" in prompt


def test_generate_tab_insight_without_model_names_uses_single_model_path_unchanged():
    service = make_service()
    captured_prompt = {}

    def fake_call_gemini(prompt, usage_total):
        captured_prompt["value"] = prompt
        return "解讀內容。"

    service._call_gemini = fake_call_gemini
    mining_results = {"results": [make_result("SVM")]}

    text = service.generate_tab_insight(mining_results, "roc", "SVM", "fold_1")

    assert text == "解讀內容。"
    prompt = captured_prompt["value"]
    assert '模型「SVM」在「fold_1」這筆結果的資料' in prompt
    assert "請比較它們的表現" not in prompt


def test_generate_tab_insight_multi_model_no_matching_results():
    service = make_service()
    mining_results = {"results": [make_result("SVM")]}
    text = service.generate_tab_insight(
        mining_results, "roc", "SVM", "fold_1", model_names=["不存在的模型"],
    )
    assert text == "找不到對應的結果資料。"


def test_chat_about_tab_multi_model_context_mentions_model_count():
    service = make_service()
    captured = {}

    class FakeChat:
        def send_message(self, message):
            captured["message"] = message
            class Resp:
                text = "SVM 表現比較好。"
            return Resp()

    class FakeModel:
        def start_chat(self, history):
            captured["history"] = history
            return FakeChat()

    service._model = FakeModel()
    mining_results = {"results": [make_result("SVM"), make_result("Random Forest")]}

    reply = service.chat_about_tab(
        mining_results, "roc", "SVM", "fold_1", [], "哪個模型比較好？",
        model_names=["SVM", "Random Forest"],
    )

    assert reply == "SVM 表現比較好。"
    first_turn_text = captured["history"][0]["parts"][0]
    assert "2 個模型的比較" in first_turn_text
    assert "SVM" in first_turn_text
    assert "Random Forest" in first_turn_text
```

- [ ] **Step 9: 跑測試**

Run:
```bash
docker cp backend/tests/test_paper_rag_tab_insight.py datamind-backend:/tmp/test_paper_rag_tab_insight.py
docker exec -w /app datamind-backend .venv/bin/python -m pytest /tmp/test_paper_rag_tab_insight.py -v
```
Expected: 10 個測試全部 PASS

- [ ] **Step 10: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/services/rag/paper_rag.py backend/tests/test_paper_rag_tab_insight.py
git commit -m "feat: add multi-model ROC/PR comparison path to tab insight/chat"
```

---

### Task 2: 後端路由 `rag.py`——`model_names` 選填欄位

**Files:**
- Modify: `backend/routes/rag.py`
- Modify: `backend/tests/test_rag_routes.py`

**Interfaces:**
- Consumes: Task 1 產出的 `generate_tab_insight(..., model_names=...)`/`chat_about_tab(..., model_names=...)`
- Produces: `POST /api/rag/tab-insight`、`POST /api/rag/tab-chat` 都接受 `model_name`（字串）或 `model_names`（字串陣列）其中一個

- [ ] **Step 1: `/tab-insight` 改成 `model_name`/`model_names` 二選一**

現有的（第 563-596 行）：
```python
@rag_bp.route("/tab-insight", methods=["POST"])
@login_required
def generate_tab_insight():
    """針對 workflow 結果裡某個分頁（混淆矩陣/ROC/PR/校準曲線/各類別指標）生成 AI 解讀文字

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - tab             : 'matrix' | 'roc' | 'pr' | 'calibration' | 'perClass'（必填）
        - model_name      : 要解讀哪個模型（必填）
        - split_name      : 要解讀哪個 fold/split（必填）

    回傳：
        - insight : AI 生成的解讀文字
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400
    tab = data.get("tab")
    model_name = data.get("model_name")
    split_name = data.get("split_name")
    if not tab or not model_name or not split_name:
        return jsonify({"success": False, "error": "tab、model_name、split_name 為必填欄位"}), 400

    service = get_paper_rag_service()

    try:
        insight = service.generate_tab_insight(data["mining_results"], tab, model_name, split_name)
        return jsonify({"success": True, "insight": insight})

    except Exception as e:
        logger.exception("分頁解讀生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```
改成：
```python
@rag_bp.route("/tab-insight", methods=["POST"])
@login_required
def generate_tab_insight():
    """針對 workflow 結果裡某個分頁（混淆矩陣/ROC/PR/校準曲線/各類別指標）生成 AI 解讀文字

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - tab             : 'matrix' | 'roc' | 'pr' | 'calibration' | 'perClass'（必填）
        - model_name      : 要解讀哪個模型（跟 model_names 二選一，至少要有一個）
        - model_names     : 要解讀哪些模型的比較（ROC/PR 多模型疊圖用，跟 model_name 二選一）
        - split_name      : 要解讀哪個 fold/split（必填）

    回傳：
        - insight : AI 生成的解讀文字
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400
    tab = data.get("tab")
    model_name = data.get("model_name")
    model_names = data.get("model_names")
    split_name = data.get("split_name")
    if not tab or not split_name or (not model_name and not model_names):
        return jsonify({
            "success": False,
            "error": "tab、split_name 為必填欄位，且 model_name/model_names 至少要有一個",
        }), 400

    service = get_paper_rag_service()

    try:
        insight = service.generate_tab_insight(
            data["mining_results"], tab, model_name, split_name, model_names=model_names,
        )
        return jsonify({"success": True, "insight": insight})

    except Exception as e:
        logger.exception("分頁解讀生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 2: `/tab-chat` 同樣改法**

現有的（第 599-637 行）：
```python
@rag_bp.route("/tab-chat", methods=["POST"])
def chat_about_tab():
    """針對 workflow 結果裡某個分頁（混淆矩陣/ROC/PR/校準曲線/各類別指標），進行範圍限定的多輪問答

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - tab             : 'matrix' | 'roc' | 'pr' | 'calibration' | 'perClass'（必填）
        - model_name      : 要問哪個模型的結果（必填）
        - split_name      : 要問哪個 fold/split（必填）
        - history         : 對話歷史 [{role: "user"|"model", text: str}]（選填，預設空陣列）
        - message         : 本輪使用者輸入（必填）

    回傳：
        - reply : AI 回覆文字
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400
    tab = data.get("tab")
    model_name = data.get("model_name")
    split_name = data.get("split_name")
    message = (data.get("message") or "").strip()
    if not tab or not model_name or not split_name:
        return jsonify({"success": False, "error": "tab、model_name、split_name 為必填欄位"}), 400
    if not message:
        return jsonify({"success": False, "error": "message 為必填欄位"}), 400

    history = data.get("history") or []
    service = get_paper_rag_service()

    try:
        reply = service.chat_about_tab(data["mining_results"], tab, model_name, split_name, history, message)
        return jsonify({"success": True, "reply": reply})

    except Exception as e:
        logger.exception("分頁問答失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```
改成：
```python
@rag_bp.route("/tab-chat", methods=["POST"])
def chat_about_tab():
    """針對 workflow 結果裡某個分頁（混淆矩陣/ROC/PR/校準曲線/各類別指標），進行範圍限定的多輪問答

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - tab             : 'matrix' | 'roc' | 'pr' | 'calibration' | 'perClass'（必填）
        - model_name      : 要問哪個模型的結果（跟 model_names 二選一，至少要有一個）
        - model_names     : 要問哪些模型的比較（ROC/PR 多模型疊圖用，跟 model_name 二選一）
        - split_name      : 要問哪個 fold/split（必填）
        - history         : 對話歷史 [{role: "user"|"model", text: str}]（選填，預設空陣列）
        - message         : 本輪使用者輸入（必填）

    回傳：
        - reply : AI 回覆文字
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400
    tab = data.get("tab")
    model_name = data.get("model_name")
    model_names = data.get("model_names")
    split_name = data.get("split_name")
    message = (data.get("message") or "").strip()
    if not tab or not split_name or (not model_name and not model_names):
        return jsonify({
            "success": False,
            "error": "tab、split_name 為必填欄位，且 model_name/model_names 至少要有一個",
        }), 400
    if not message:
        return jsonify({"success": False, "error": "message 為必填欄位"}), 400

    history = data.get("history") or []
    service = get_paper_rag_service()

    try:
        reply = service.chat_about_tab(
            data["mining_results"], tab, model_name, split_name, history, message, model_names=model_names,
        )
        return jsonify({"success": True, "reply": reply})

    except Exception as e:
        logger.exception("分頁問答失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 3: 語法檢查**

Run:
```bash
docker cp backend/routes/rag.py datamind-backend:/tmp/rag.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/rag.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 4: 幫既有的 `FakeService`（`test_rag_routes.py`）加上兩個假方法**

`backend/tests/test_rag_routes.py` 裡的 `FakeService` class（第 38 行開始）目前沒有 `generate_tab_insight`/`chat_about_tab` 方法，找到這個 class 定義，在既有方法（例如 `generate_paper`，第 66-70 行）之後新增：
```python
    def generate_tab_insight(self, mining_results, tab, model_name, split_name, model_names=None):
        self.calls.append(("generate_tab_insight", tab, model_name, split_name, model_names))
        return "假的解讀文字"

    def chat_about_tab(self, mining_results, tab, model_name, split_name, history, message, model_names=None):
        self.calls.append(("chat_about_tab", tab, model_name, split_name, model_names, message))
        return "假的回覆文字"
```

- [ ] **Step 5: 新增路由測試**

在 `test_rag_routes.py` 檔案尾端新增（沿用檔案裡既有的 `client`/`FakeProject`/`FakeService`/monkeypatch 慣例）：
```python
def test_tab_insight_accepts_model_names_list(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.post("/api/rag/tab-insight", json={
        "mining_results": {"results": []},
        "tab": "roc",
        "model_names": ["SVM", "Random Forest"],
        "split_name": "fold_1",
    })

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    call = fake_service.calls[0]
    assert call == ("generate_tab_insight", "roc", None, "fold_1", ["SVM", "Random Forest"])


def test_tab_insight_still_accepts_single_model_name(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.post("/api/rag/tab-insight", json={
        "mining_results": {"results": []},
        "tab": "matrix",
        "model_name": "SVM",
        "split_name": "fold_1",
    })

    assert response.status_code == 200
    call = fake_service.calls[0]
    assert call == ("generate_tab_insight", "matrix", "SVM", "fold_1", None)


def test_tab_insight_rejects_missing_both_model_fields(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.post("/api/rag/tab-insight", json={
        "mining_results": {"results": []},
        "tab": "roc",
        "split_name": "fold_1",
    })

    assert response.status_code == 400
    assert fake_service.calls == []


def test_tab_chat_accepts_model_names_list(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.post("/api/rag/tab-chat", json={
        "mining_results": {"results": []},
        "tab": "pr",
        "model_names": ["SVM", "Random Forest"],
        "split_name": "fold_1",
        "message": "哪個模型比較好？",
    })

    assert response.status_code == 200
    call = fake_service.calls[0]
    assert call == ("chat_about_tab", "pr", None, "fold_1", ["SVM", "Random Forest"], "哪個模型比較好？")


def test_tab_chat_rejects_missing_both_model_fields(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.post("/api/rag/tab-chat", json={
        "mining_results": {"results": []},
        "tab": "pr",
        "split_name": "fold_1",
        "message": "哪個模型比較好？",
    })

    assert response.status_code == 400
    assert fake_service.calls == []
```
（`/tab-insight` 這幾個測試用既有的 `client` fixture 就好——它已經設定 `app.config["LOGIN_DISABLED"] = True`，會繞過 `@login_required`，不用額外處理登入；`/tab-chat` 本身沒有 `@login_required`，同一個 `client` fixture 一樣適用）

- [ ] **Step 6: 跑測試**

Run:
```bash
docker cp backend/tests/test_rag_routes.py datamind-backend:/tmp/test_rag_routes.py
docker exec -w /app datamind-backend .venv/bin/python -m pytest /tmp/test_rag_routes.py -v
```
Expected: 既有測試全部維持 PASS，新增的 5 個測試也 PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/routes/rag.py backend/tests/test_rag_routes.py
git commit -m "feat: accept model_names list on tab-insight/tab-chat routes"
```

---

### Task 3: 前端 `api/insight.ts`——支援多模型參數

**Files:**
- Modify: `frontend/src/api/insight.ts`

**Interfaces:**
- Consumes: Task 2 產出的路由（`model_name`/`model_names` 二選一）
- Produces: `fetchTabInsight(miningResults, tab, model: string | string[], splitName): Promise<string>`、`fetchTabChatReply(miningResults, tab, model: string | string[], splitName, history, message): Promise<string>`（Task 4 會用到這兩個新簽名）

- [ ] **Step 1: `fetchTabInsight` 改成接受 `string | string[]`**

現有的（第 16-39 行）：
```typescript
export async function fetchTabInsight (
  miningResults: Record<string, unknown>,
  tab: string,
  modelName: string,
  splitName: string,
): Promise<string> {
  const response = await fetch('/api/rag/tab-insight', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mining_results: miningResults,
      tab,
      model_name: modelName,
      split_name: splitName,
    }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return String(result.insight ?? '')
}
```
改成：
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

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return String(result.insight ?? '')
}
```

- [ ] **Step 2: `fetchTabChatReply` 同樣改法**

現有的（第 46-73 行）：
```typescript
export async function fetchTabChatReply (
  miningResults: Record<string, unknown>,
  tab: string,
  modelName: string,
  splitName: string,
  history: TabChatMessage[],
  message: string,
): Promise<string> {
  const response = await fetch('/api/rag/tab-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mining_results: miningResults,
      tab,
      model_name: modelName,
      split_name: splitName,
      history,
      message,
    }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return String(result.reply ?? '')
}
```
改成：
```typescript
export async function fetchTabChatReply (
  miningResults: Record<string, unknown>,
  tab: string,
  model: string | string[],
  splitName: string,
  history: TabChatMessage[],
  message: string,
): Promise<string> {
  const response = await fetch('/api/rag/tab-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mining_results: miningResults,
      tab,
      split_name: splitName,
      history,
      message,
      ...(Array.isArray(model) ? { model_names: model } : { model_name: model }),
    }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return String(result.reply ?? '')
}
```

- [ ] **Step 3: 型別檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`

Expected: 這個階段 `ConfusionMatrixPanel.vue`（Task 4 才會改）呼叫 `fetchTabInsight`/`fetchTabChatReply` 時傳的還是 `string`（`selectedModel.value`），型別上 `string` 相容於 `string | string[]`，不會產生新錯誤。用 `npm run type-check 2>&1 | grep -i "insight.ts\|ConfusionMatrixPanel"` 確認沒有輸出。

- [ ] **Step 4: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/api/insight.ts
git commit -m "feat: accept model_names list in tab insight/chat API functions"
```

---

### Task 4: 前端 `ConfusionMatrixPanel.vue`——整合多模型解讀範圍

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`

**Interfaces:**
- Consumes: Task 3 產出的 `fetchTabInsight(miningResults, tab, model: string | string[], splitName)`、`fetchTabChatReply(...)`

- [ ] **Step 1: 新增 `visibleModelNames`**

在 `hiddenModels`（第 510 行）附近新增：
```typescript
const visibleModelNames = computed(() =>
  groupedResults.value
    .filter(g => !hiddenModels.value.has(g.model_name))
    .map(g => g.model_name),
)
```

- [ ] **Step 2: 新增 `insightModelParam` 與 `modelParamToString`**

在 `tabInsightCache`/`tabInsightCacheKey`（第 625-631 行）之前新增：
```typescript
// ROC/PR 用「目前顯示中的模型集合」當作 AI 解讀的範圍；其他分頁維持單一 selectedModel，
// 排序是為了同一組模型不管使用者關閉/開啟的先後順序，都對應到同一個快取 key
const insightModelParam = computed<string | string[]>(() => {
  if (activeTab.value === 'roc' || activeTab.value === 'pr') {
    return [...visibleModelNames.value].sort()
  }
  return selectedModel.value
})

function modelParamToString (model: string | string[]): string {
  return Array.isArray(model) ? model.join(',') : model
}
```

- [ ] **Step 3: `tabInsightCacheKey()` 改用 `modelParamToString()`**

現有的（第 629-631 行）：
```typescript
  function tabInsightCacheKey (tab: TabKey, model: string, fold: string): string {
    return `${tab}::${model}::${fold}`
  }
```
改成：
```typescript
  function tabInsightCacheKey (tab: TabKey, model: string | string[], fold: string): string {
    return `${tab}::${modelParamToString(model)}::${fold}`
  }
```

- [ ] **Step 4: `currentTabInsightKey` 改用 `insightModelParam`**

現有的（第 633-635 行）：
```typescript
  const currentTabInsightKey = computed(() =>
    tabInsightCacheKey(activeTab.value, selectedModel.value, selectedFold.value),
  )
```
改成：
```typescript
  const currentTabInsightKey = computed(() =>
    tabInsightCacheKey(activeTab.value, insightModelParam.value, selectedFold.value),
  )
```

- [ ] **Step 5: `hasCurrentTabData` 的 ROC/PR 分支改用 `visibleModelNames`**

找到 `hasCurrentTabData`（第 614-622 行附近）目前這一行：
```typescript
      case 'roc':
      case 'pr': return currentRocPrCurve.value !== null
```
改成：
```typescript
      case 'roc':
      case 'pr': return visibleModelNames.value.length > 0
```

- [ ] **Step 6: `generateTabInsight()` 改用 `insightModelParam`**

現有的（第 643-665 行）：
```typescript
  async function generateTabInsight (): Promise<void> {
    if (!props.projectId || !props.workflowResult) return
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)

    tabInsightLoadingKey.value = key
    tabInsightError.value = null
    try {
      const insight = await fetchTabInsight(props.workflowResult, tab, model, fold)
      tabInsightCache.value = new Map(tabInsightCache.value).set(key, insight)
      saveTabInsightToStorage(props.projectId, model, fold, tab, insight)
    } catch (error) {
      tabInsightError.value = error instanceof Error ? error.message : String(error)
    } finally {
      // 只清自己那把 key 的 loading 狀態——避免使用者切到別的組合又按了一次生成，
      // 這次 finally 執行時把「新的那次」的 loading 狀態誤清掉
      if (tabInsightLoadingKey.value === key) {
        tabInsightLoadingKey.value = null
      }
    }
  }
```
改成（只有 `const model = selectedModel.value` 改成 `insightModelParam.value`，跟 `saveTabInsightToStorage` 呼叫時把 `model` 轉成字串，其餘不動）：
```typescript
  async function generateTabInsight (): Promise<void> {
    if (!props.projectId || !props.workflowResult) return
    const tab = activeTab.value
    const model = insightModelParam.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)

    tabInsightLoadingKey.value = key
    tabInsightError.value = null
    try {
      const insight = await fetchTabInsight(props.workflowResult, tab, model, fold)
      tabInsightCache.value = new Map(tabInsightCache.value).set(key, insight)
      saveTabInsightToStorage(props.projectId, modelParamToString(model), fold, tab, insight)
    } catch (error) {
      tabInsightError.value = error instanceof Error ? error.message : String(error)
    } finally {
      // 只清自己那把 key 的 loading 狀態——避免使用者切到別的組合又按了一次生成，
      // 這次 finally 執行時把「新的那次」的 loading 狀態誤清掉
      if (tabInsightLoadingKey.value === key) {
        tabInsightLoadingKey.value = null
      }
    }
  }
```

- [ ] **Step 7: `requestTabChatReply()` 改用 `insightModelParam`**

現有的（第 727-754 行）：
```typescript
  async function requestTabChatReply (
    tab: TabKey, model: string, fold: string, history: TabChatMessage[], text: string,
  ): Promise<void> {
    if (!props.projectId || !props.workflowResult) return
    const key = tabInsightCacheKey(tab, model, fold)

    tabChatLoadingKeys.value = new Set(tabChatLoadingKeys.value).add(key)
    if (tabChatError.value.has(key)) {
      const nextError = new Map(tabChatError.value)
      nextError.delete(key)
      tabChatError.value = nextError
    }
    try {
      const reply = await fetchTabChatReply(props.workflowResult, tab, model, fold, history, text)
      const messages = [...(tabChatCache.value.get(key) ?? []), { role: 'model' as const, text: reply }]
      tabChatCache.value = new Map(tabChatCache.value).set(key, messages)
      saveTabChatToStorage(props.projectId, model, fold, tab, messages.slice(-MAX_PERSISTED_MESSAGES))
      startTypewriter(`${key}::${messages.length - 1}`, reply)
    } catch (error) {
      tabChatError.value = new Map(tabChatError.value).set(
        key, error instanceof Error ? error.message : String(error),
      )
    } finally {
      const nextLoadingKeys = new Set(tabChatLoadingKeys.value)
      nextLoadingKeys.delete(key)
      tabChatLoadingKeys.value = nextLoadingKeys
    }
  }
```
改成（函式簽名的 `model: string` 改成 `model: string | string[]`，`saveTabChatToStorage` 呼叫時轉成字串，其餘不動）：
```typescript
  async function requestTabChatReply (
    tab: TabKey, model: string | string[], fold: string, history: TabChatMessage[], text: string,
  ): Promise<void> {
    if (!props.projectId || !props.workflowResult) return
    const key = tabInsightCacheKey(tab, model, fold)

    tabChatLoadingKeys.value = new Set(tabChatLoadingKeys.value).add(key)
    if (tabChatError.value.has(key)) {
      const nextError = new Map(tabChatError.value)
      nextError.delete(key)
      tabChatError.value = nextError
    }
    try {
      const reply = await fetchTabChatReply(props.workflowResult, tab, model, fold, history, text)
      const messages = [...(tabChatCache.value.get(key) ?? []), { role: 'model' as const, text: reply }]
      tabChatCache.value = new Map(tabChatCache.value).set(key, messages)
      saveTabChatToStorage(
        props.projectId, modelParamToString(model), fold, tab, messages.slice(-MAX_PERSISTED_MESSAGES),
      )
      startTypewriter(`${key}::${messages.length - 1}`, reply)
    } catch (error) {
      tabChatError.value = new Map(tabChatError.value).set(
        key, error instanceof Error ? error.message : String(error),
      )
    } finally {
      const nextLoadingKeys = new Set(tabChatLoadingKeys.value)
      nextLoadingKeys.delete(key)
      tabChatLoadingKeys.value = nextLoadingKeys
    }
  }
```

- [ ] **Step 8: `sendTabChatMessage()` 改用 `insightModelParam`**

現有的（第 756-782 行）：
```typescript
  async function sendTabChatMessage (): Promise<void> {
    const text = tabChatInput.value.trim()
    if (!text || !props.projectId || !props.workflowResult) return

    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    const cachedMessages = tabChatCache.value.get(key) ?? []
    // 如果上一則還是「還沒被回覆的 user 訊息」（送出失敗留下的），視為使用者放棄那次嘗試，
    // 把它從 history 跟畫面快取裡都拿掉，避免產生連續兩筆 user 訊息、破壞跟後端對話輪替的順序
    const hasTrailingUnansweredUserMessage =
      cachedMessages[cachedMessages.length - 1]?.role === 'user'
    const history = hasTrailingUnansweredUserMessage
      ? cachedMessages.slice(0, -1)
      : cachedMessages

    tabChatInput.value = ''
    tabChatCache.value = new Map(tabChatCache.value).set(key, [...history, { role: 'user' as const, text }])
    if (tabChatError.value.has(key)) {
      const nextError = new Map(tabChatError.value)
      nextError.delete(key)
      tabChatError.value = nextError
    }

    await requestTabChatReply(tab, model, fold, history, text)
  }
```
把 `const model = selectedModel.value` 改成 `const model = insightModelParam.value`，其餘完全不動。

- [ ] **Step 9: `retryTabChatMessage()` 改用 `insightModelParam`**

現有的（第 786-796 行）：
```typescript
  function retryTabChatMessage (): void {
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    const messages = tabChatCache.value.get(key) ?? []
    const lastMessage = messages[messages.length - 1]
    if (!lastMessage || lastMessage.role !== 'user') return
    const history = messages.slice(0, -1)
    void requestTabChatReply(tab, model, fold, history, lastMessage.text)
  }
```
把 `const model = selectedModel.value` 改成 `const model = insightModelParam.value`，其餘完全不動。

- [ ] **Step 10: 自動載入快取的 `watch()` 改用 `insightModelParam`**

現有的（第 798-819 行）：
```typescript
  // 切換分頁/模型/fold 時，如果 localStorage 已經有這個組合的快取就直接顯示，不用重新打 API
  watch([activeTab, selectedModel, selectedFold], () => {
    tabInsightError.value = null
    tabChatInput.value = ''
    if (!props.projectId) return
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    if (!tabInsightCache.value.has(key)) {
      const cached = loadTabInsightFromStorage(props.projectId, model, fold, tab)
      if (cached !== null) {
        tabInsightCache.value = new Map(tabInsightCache.value).set(key, cached)
      }
    }
    if (!tabChatCache.value.has(key)) {
      const cachedChat = loadTabChatFromStorage(props.projectId, model, fold, tab)
      if (cachedChat.length > 0) {
        tabChatCache.value = new Map(tabChatCache.value).set(key, cachedChat)
      }
    }
  }, { immediate: true })
```
改成（依賴陣列的 `selectedModel` 換成 `insightModelParam`，內部 `const model = selectedModel.value` 換成 `insightModelParam.value`，傳給 `loadTabInsightFromStorage`/`loadTabChatFromStorage` 時用 `modelParamToString()` 轉成字串）：
```typescript
  // 切換分頁/模型/fold 時，如果 localStorage 已經有這個組合的快取就直接顯示，不用重新打 API
  watch([activeTab, insightModelParam, selectedFold], () => {
    tabInsightError.value = null
    tabChatInput.value = ''
    if (!props.projectId) return
    const tab = activeTab.value
    const model = insightModelParam.value
    const modelKey = modelParamToString(model)
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    if (!tabInsightCache.value.has(key)) {
      const cached = loadTabInsightFromStorage(props.projectId, modelKey, fold, tab)
      if (cached !== null) {
        tabInsightCache.value = new Map(tabInsightCache.value).set(key, cached)
      }
    }
    if (!tabChatCache.value.has(key)) {
      const cachedChat = loadTabChatFromStorage(props.projectId, modelKey, fold, tab)
      if (cachedChat.length > 0) {
        tabChatCache.value = new Map(tabChatCache.value).set(key, cachedChat)
      }
    }
  }, { immediate: true })
```

- [ ] **Step 11: 型別檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`

Expected: 既有的 53 個 `@tiptap/*` 錯誤不變，`npm run type-check 2>&1 | grep -i "ConfusionMatrixPanel"` 沒有輸出。

- [ ] **Step 12: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
git commit -m "feat: scope ROC/PR AI insight and chat to currently visible models"
```

---

## 完成後的人工驗證

四個 task 都完成、commit 之後，在瀏覽器 `http://localhost:5173` 上驗證：

1. 進 ROC 分頁，圖例全部顯示時按「AI 解讀」，確認生成的文字有提到多個模型並做比較（點名表現最好的模型）
2. 關掉圖例上的某個模型，確認「AI 解讀」區塊變回「尚未產生」的狀態，重新產生後的內容只涵蓋還顯示中的模型
3. 針對這個多模型解讀繼續追問（聊天），確認 AI 的回覆有考慮到所有目前顯示中的模型的資料，不是只回答其中一個
4. 切到混淆矩陣分頁，確認 AI 解讀維持單模型行為，跟改動前一樣
5. 把 ROC 圖例上全部模型都關掉，確認「AI 解讀」區塊整個消失（跟「此分頁沒有資料」時的畫面一致）
6. 切到 PR 分頁重複第 1-2 項，確認行為一致
