# ROC / PR 曲線 Design Spec

## 背景

「一般醫學論文流程還有什麼漏」的落差分析裡，confusion matrix 已經補完（見 `2026-08-15-confusion-matrix-design.md`），這次接著做清單上第三項：ROC / PR 曲線。`test_score_service.py` 目前只在 `_compute_metric()` 的 `auc`/`auprc` 分支算出純量值（`roc_auc_score`/`average_precision_score`），從來沒有把畫圖用的座標點（fpr/tpr、precision/recall）存下來回傳過。

## 範圍

- 後端：`test_score_service.py` 新增計算函式，`workflow_service.py` 兩處（`execute_workflow`/`execute_workflow_stream`）各加一行接進結果 dict
- 前端：擴充既有 `ConfusionMatrixPanel.vue`，加分頁切換顯示 ROC/PR 曲線；`workflowData.ts` 的 `confusionMatrix` 節點改顯示名稱
- **不**新增畫布節點、**不**動 `useWorkflowNodes.ts`/`useWorkflowImport.ts`（節點 id 不變，這些檔案的邏輯都是照 id 判斷，跟本次改動無關）
- **不**支援多分類 ROC/PR（跟 `auc`/`auprc` 現有限制一致）

## 後端設計

`test_score_service.py` 新增：

```python
from sklearn.metrics import precision_recall_curve, roc_curve

def build_roc_pr_curve(y_true: pd.Series, y_score: Any) -> Optional[Dict[str, Any]]:
    """算 ROC / PR 曲線座標點，只支援二元分類（y_score 為 None 或多分類時回傳 None）"""
    if y_score is None:
        return None
    score_vec = _get_score_vector(y_score)
    if score_vec is None:
        return None
    unique_labels = pd.unique(y_true.dropna())
    if len(unique_labels) != 2:
        return None

    pos_label = _infer_positive_label(y_true)
    binary = _to_binary_array(y_true, pos_label)

    fpr, tpr, _ = roc_curve(binary, score_vec)
    precision, recall, _ = precision_recall_curve(binary, score_vec)

    return {
        "pos_label": str(pos_label),
        "roc": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
        "pr": {"precision": precision.tolist(), "recall": recall.tolist()},
    }
```

複用既有的 `_get_score_vector()`（從 `y_score` dict 取出正類機率向量）、`_infer_positive_label()`、`_to_binary_array()`——跟 `auc`/`auprc` 走同一套二元轉換邏輯，避免邏輯分歧。

`workflow_service.py` 的 `y_test`/`y_score` 在 `results.append(...)` 之前已經算好（跟 `confusion_matrix` 同一個位置），兩處（非串流 `:486`、串流 `:688` 附近，緊接著 `confusion_matrix` 那行）各加：

```python
"roc_pr_curve": build_roc_pr_curve(y_test, y_score),
```

`build_roc_pr_curve` 需要一併加進 `from .test_score_service import evaluate_metrics, generate_score_variants` 的 import 列表。

## 前端設計

**`ConfusionMatrixPanel.vue`**（擴充既有檔案）：

- 頂端加一個分頁切換（`混淆矩陣` / `ROC 曲線` / `PR 曲線`），模型 + fold 雙下拉維持共用（現有的 `selectedModel`/`selectedFold`/`groupedResults` 邏輯不變），只有下方內容區依分頁切換
- `groupedResults`/`ResultItem` 的 parsing 邏輯比照 `confusion_matrix` 欄位的既有寫法，多讀一個 `roc_pr_curve` 欄位，用型別守衛防禦（`Array.isArray`/型別檢查），缺欄位或非二元分類時該筆結果視為「沒有 ROC/PR 資料」
- ROC 曲線圖：手刻 inline SVG 折線圖（不引入圖表函式庫，比照 `FeatureImportancePanel.vue`/`ConfusionMatrixPanel.vue` 現有慣例）。x 軸 = FPR（0–1）、y 軸 = TPR（0–1），加一條對角線參考線（隨機分類器基準），座標軸簡單標示 0 / 0.5 / 1
- PR 曲線圖：同樣手刻 SVG，x 軸 = Recall（0–1）、y 軸 = Precision（0–1）
- 沒有 ROC/PR 資料時（多分類或模型不支援機率輸出），該分頁顯示「此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出）」，比照現有空狀態文字寫法

**`workflowData.ts`**：`confusionMatrix` 節點（id 不變）的顯示內容更新：
- `label`: `"Classification\nEvaluation"`（原為 `"Confusion\nMatrix"`）
- `description`: `"顯示混淆矩陣與 ROC/PR 曲線"`（原為 `"輸出混淆矩陣"`）

`icon`（`mdi-grid`）、`config`（`{ normalize: "none" }`）維持不變。

## 錯誤處理 / 相容性

- 舊的 workflow 執行結果（這次改動之前跑的）沒有 `roc_pr_curve` 欄位，前端讀取時用型別守衛防禦，缺欄位時該筆結果視為「沒有 ROC/PR 資料」，不會讓面板報錯崩潰（比照 `confusion_matrix` 現有的防禦寫法）
- `build_roc_pr_curve` 內部任何例外都不攔截——沿用專案現有慣例（`_build_confusion_matrix` 同樣沒有 try/except），若 sklearn 呼叫本身失敗會直接讓該筆 workflow 結果報錯，不會靜默吞掉例外

## 測試

- 後端無 pytest，前端無 vitest。用 `docker exec datamind-backend .venv/bin/python -m py_compile` 做語法檢查，前端用 `npm run type-check`
- 人工瀏覽器驗證：執行一次 workflow（二元分類資料集），點畫布上「Classification Evaluation」節點，確認：
  - 三個分頁都能正常切換（混淆矩陣 / ROC 曲線 / PR 曲線）
  - 切換模型 + fold 下拉時，三個分頁的內容都跟著變
  - ROC 曲線有畫出對角線參考線；PR 曲線座標軸範圍正確（0–1）
  - 用一個多分類資料集跑一次，確認 ROC/PR 分頁顯示正確的空狀態文字，混淆矩陣分頁不受影響、正常顯示 NxN 表格
