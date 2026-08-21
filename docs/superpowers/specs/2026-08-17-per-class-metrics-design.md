# Per-Class 指標 Design Spec

## 背景

「一般醫學論文流程還有什麼漏」的落差分析裡最後一項：多分類情境下每個類別各自的 precision/recall/f1。調查過程中發現一個既有 bug：`test_score_service.py` 的 precision/recall/f1 計算完全沒有指定 `average` 參數，多分類且沒有明確正類時，`_infer_positive_label()` 回傳 `None`，sklearn 的 `precision_score`/`recall_score`/`f1_score` 預設 `average='binary'`，遇到多分類 `y` 會拋 `ValueError`。雖然 `evaluate_metrics()` 的迴圈有 per-metric try/except 接住、不會讓整趟 workflow 崩潰，但結果是任何人拿多分類資料跑，precision/recall/f1 這三個指標在主要結果表格裡全部顯示「error」，完全沒有值。

這次要做兩件耦合的事：(1) 修掉這個既有 bug；(2) 新增 per-class 指標——每個類別各自的 precision/recall/f1/support，這是使用者真正要的東西。跟這個 session 稍早做的 ROC/PR 曲線、校準曲線不同，這個功能天生不受「只支援二元分類」的限制——precision/recall/f1/support 純粹是 `y_true`/`y_pred` 的函式，對任意類別數都有意義，不需要機率分數。

## 範圍

- 後端：`test_score_service.py` 修 `_compute_metric()` 的 average 策略選擇 + 新增 `build_per_class_metrics()`，`workflow_service.py` 兩處接進結果 dict
- 前端：`ConfusionMatrixPanel.vue` 加第五個分頁「各類別指標」，純表格呈現
- **不**動二元分類的既有行為（`pos_label` + `average='binary'` 邏輯完全不變）
- **不**新增畫布節點，`confusionMatrix` 節點不再變動

## 後端設計

### 修 bug：`_compute_metric()` 的 average 策略

現有的 precision/recall/f1 分支（`test_score_service.py:385-399`）：

```python
elif metric in {"precision", "recall", "f1"}:
    kwargs: Dict[str, Any] = {"zero_division": 0}
    effective_pos = pos_label or _infer_positive_label(y_true, labels)
    if effective_pos is not None:
        kwargs["pos_label"] = effective_pos
    if labels is not None:
        kwargs["labels"] = labels
    ...
```

改成：`effective_pos` 為 `None`（代表多分類且沒有明確正類）時，明確設定 `kwargs["average"] = "macro"`，避免 sklearn 用預設的 `average='binary'` 對多分類拋例外。選擇 `macro`（而非 `weighted`/`micro`）：每個類別的指標先各自算、再直接平均，不論該類別樣本數多寡，讓少數類別（例如罕見疾病亞型）的表現不會被多數類別稀釋掉，符合醫學多分類情境「每一類都要顧到」的需求。二元分類（`effective_pos` 非 `None`）的既有行為完全不變。

### 新函式：`build_per_class_metrics()`

```python
def build_per_class_metrics(y_true: pd.Series, y_pred: pd.Series) -> Dict[str, Any]:
    """算每個類別各自的 precision/recall/f1/support，二元、多分類皆適用。"""
    labels = sorted(pd.unique(pd.concat([y_true, y_pred]).dropna()), key=str)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    return {
        "labels": [str(label) for label in labels],
        "precision": [round(v, 6) for v in precision.tolist()],
        "recall": [round(v, 6) for v in recall.tolist()],
        "f1": [round(v, 6) for v in f1.tolist()],
        "support": [int(v) for v in support.tolist()],
    }
```

`labels` 排序沿用 `_build_confusion_matrix`（`workflow_service.py`）同一套邏輯（`sorted(pd.unique(pd.concat([y_true, y_pred]).dropna()), key=str)`），確保兩者類別順序一致，前端可以直接對齊。這個函式純粹是 `y_true`/`y_pred` 的函式，不需要 `y_score`，沒有 `_to_binary_array` 那種會因為數值型 target 混雜 NaN 而拋例外的路徑，不需要額外的 try/except 防護——`precision_recall_fscore_support` 本身對任意標籤型別（字串、數值、含 NaN 已被上游過濾）都是安全的。

`workflow_service.py` 的 `y_test`/`y_pred` 在兩處（`execute_workflow`、`execute_workflow_stream`）都已算好，緊接著現有的 `"confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),` 那行之後加：

```python
"per_class_metrics": build_per_class_metrics(y_test, y_pred),
```

`build_per_class_metrics` 需要一併加進 `from .test_score_service import (...)` 的 import 列表；`precision_recall_fscore_support` 需要加進 `test_score_service.py` 的 `from sklearn.metrics import (...)` 匯入區塊。

## 前端設計

**`ConfusionMatrixPanel.vue`**（擴充既有檔案）：

- 分頁陣列 `TABS` 從四個擴充成五個：`混淆矩陣` / `ROC 曲線` / `PR 曲線` / `校準曲線` / `各類別指標`，`TabKey` 型別對應加 `'perClass'`
- 資料型別新增 `PerClassMetricsData { labels: string[], precision: number[], recall: number[], f1: number[], support: number[] }`，`ResultItem`/`GroupedResult.splits[]` 元素型別各加一個 `per_class_metrics: PerClassMetricsData | null` 欄位，新增 `parsePerClassMetrics()`（比照既有 `parseConfusionMatrix()`/`parseRocPrCurve()` 的型別守衛寫法，四個陣列長度不一致或非 number 陣列都回傳 `null`）
- `confusionResults` 的 filter 條件加上 `|| item.per_class_metrics !== null`
- 新增 `currentPerClassMetrics` computed（比照既有 `currentMatrix`/`currentRocPrCurve` 的寫法）
- 內容呈現：純 HTML 表格（不需要 SVG），每個類別一列，欄位是「類別」「Precision」「Recall」「F1」「樣本數」，樣式比照既有 `.cm-table`。F1 分數最低的那一列用既有的 `.cm-cell--diagonal` 同一套醒目底色標出來（重新命名/新增一個語意清楚的 class，例如 `.cm-row--lowest`），幫助使用者快速找到表現最差的類別
- 這個分頁天生不受二元分類限制，只要有 `confusion_matrix`/`per_class_metrics` 資料就有值，不需要「僅支援二元分類」那類空狀態文字——空狀態只有「該抽樣沒有可用資料」跟「尚未有結果」兩種，比照混淆矩陣分頁既有的空狀態寫法（不是 ROC/PR/校準曲線那種文字）

## 錯誤處理 / 相容性

- 舊的 workflow 執行結果沒有 `per_class_metrics` 欄位，前端 `parsePerClassMetrics(undefined)` 第一行判斷就回傳 `null`，該分頁走「該抽樣沒有可用資料」空狀態，不會報錯崩潰
- 二元分類資料照樣會有 `per_class_metrics`（兩個類別各自的指標），這是額外資訊，不影響既有的整體 precision/recall/f1（那三個指標維持顯示「正類」的單一數值，行為不變）

## 測試

- 後端無 pytest，前端無 vitest。用 `docker exec datamind-backend .venv/bin/python -m py_compile` 做語法檢查，前端用 `npm run type-check`
- 後端另外用一個小型 repro script 確認：多分類資料跑 `evaluate_metrics()` 時 precision/recall/f1 不再回傳 `error`（改用 macro average 算出合理數值）；`build_per_class_metrics()` 對二元、多分類都回傳正確筆數的陣列，且 `labels` 順序跟 `_build_confusion_matrix()` 一致
- 人工瀏覽器驗證：執行一次 workflow（多分類資料集，例如 3 個類別），點「Classification Evaluation」節點，確認：
  - 主要結果表格的 precision/recall/f1 不再顯示「error」，有實際數值
  - 第五個分頁「各類別指標」正確顯示每個類別的 precision/recall/f1/樣本數，F1 最低的那一列有醒目標示
  - 切換模型 + fold 下拉時，內容跟著變
  - 用一個二元分類資料集跑一次，確認整體指標行為跟這次改動之前一樣（沒有變動），第五個分頁也正常顯示兩個類別各自的指標
