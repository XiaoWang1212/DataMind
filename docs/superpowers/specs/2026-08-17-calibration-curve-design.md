# Calibration Curve Design Spec

## 背景

「一般醫學論文流程還有什麼漏」的落差分析裡，最後一項是 calibration curve（機率校準曲線）。前三項（class distribution、confusion matrix、ROC/PR 曲線）都已完成。這次延續 ROC/PR 曲線剛建立的模式：同一個檔案、同一個 helper、同一個防護寫法、同一個前端面板，加第四個分頁。

## 範圍

- 後端：`test_score_service.py` 新增 `build_calibration_curve()`，`workflow_service.py` 兩處接進結果 dict
- 前端：`ConfusionMatrixPanel.vue` 加第四個分頁「校準曲線」
- **不**開放 `n_bins`/`strategy` 給使用者調整（固定用 sklearn 預設 `n_bins=10, strategy='uniform'`），跟 ROC/PR 曲線一樣沒有對應的 UI 控制項
- **不**新增畫布節點，`confusionMatrix` 節點 id/label/description 不再變動

## 後端設計

`test_score_service.py` 新增（緊接著 `build_roc_pr_curve` 之後）：

```python
from sklearn.calibration import calibration_curve

def build_calibration_curve(y_true: pd.Series, y_score: Any) -> Optional[Dict[str, Any]]:
    """算校準曲線（reliability diagram），只支援二元分類。任何失敗都回傳 None，絕不讓例外往外傳。"""
    if y_score is None:
        return None
    score_vec = _get_score_vector(y_score)
    if score_vec is None:
        return None
    unique_labels = pd.unique(y_true.dropna())
    if len(unique_labels) != 2:
        return None

    try:
        pos_label = _infer_positive_label(y_true)
        binary = _to_binary_array(y_true, pos_label)
        if not np.array_equal(np.unique(binary), np.array([0, 1])):
            binary = (y_true == pos_label).to_numpy(dtype=int)

        prob_true, prob_pred = calibration_curve(binary, score_vec, n_bins=10, strategy="uniform")
    except Exception:
        return None

    return {
        "pos_label": str(pos_label),
        "prob_true": [round(v, 6) for v in prob_true.tolist()],
        "prob_pred": [round(v, 6) for v in prob_pred.tolist()],
    }
```

這個寫法直接沿用 `build_roc_pr_curve` 這次審查來回兩輪才定案的防護結構：guard 檢查（`y_score is None`／`score_vec is None`／`len(unique_labels) != 2`）之後，剩下所有邏輯（含 `_to_binary_array` 本身可能拋出的例外，例如數值型 target 混雜 NaN）全部包在同一個 `try/except` 裡，任何失敗都回傳 `None`，不會讓整趟 workflow 崩潰。`prob_true`/`prob_pred` 一樣四捨五入到小數點後 6 位，控制 payload 大小（比照 `build_roc_pr_curve` 的教訓）。

`workflow_service.py` 的 `y_test`/`y_score` 在兩處（`execute_workflow`、`execute_workflow_stream`）都已算好，緊接著現有的 `"roc_pr_curve": build_roc_pr_curve(y_test, y_score),` 那行之後加：

```python
"calibration_curve": build_calibration_curve(y_test, y_score),
```

`build_calibration_curve` 需要一併加進 `from .test_score_service import build_roc_pr_curve, evaluate_metrics, generate_score_variants` 的 import 列表。

## 前端設計

**`ConfusionMatrixPanel.vue`**（擴充既有檔案）：

- 分頁陣列 `TABS` 從三個擴充成四個：`混淆矩陣` / `ROC 曲線` / `PR 曲線` / `校準曲線`，`TabKey` 型別對應加 `'calibration'`
- 資料型別新增 `CalibrationCurveData { posLabel: string, probTrue: number[], probPred: number[] }`，`ResultItem`/`GroupedResult.splits[]` 元素型別各加一個 `calibration_curve: CalibrationCurveData | null` 欄位，新增 `parseCalibrationCurve()`（比照 `parseRocPrCurve()` 的型別守衛寫法：非物件、`pos_label` 非字串、`prob_true`/`prob_pred` 非 number 陣列都回傳 `null`，絕不拋例外）
- `confusionResults` 的 filter 條件加上 `|| item.calibration_curve !== null`（三個資料欄位互相獨立，任一存在就保留該筆結果）
- 新增 `currentCalibrationCurve` computed（比照 `currentRocPrCurve` 的寫法）
- 圖表畫法：跟 ROC/PR 的平滑折線不同，reliability diagram 是「有限個點 + 連接線」。除了用既有的 `buildLinePath(xs, ys)` 畫連接線（x = `prob_pred`、y = `prob_true`），每個資料點另外疊一個 `<circle>` 圓點標出來（用既有的 `toChartX`/`toChartY` 轉換座標，半徑固定 `1.5`，顏色跟折線同色）。同樣搭配對角線（完美校準）參考線，以及既有的 0/0.5/1 刻度（比照 Finding 5 那次補上的 `<text class="cm-chart-tick">` 寫法）
- 正類標示：比照 ROC/PR 分頁已有的 `正類：{{ posLabel }}` 標籤，校準曲線分頁也加同樣的標籤
- 空狀態：沒有資料時（多分類、模型不支援機率輸出、或舊版執行結果）顯示「此模型或此類別數不支援校準曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。」——文字模式沿用 ROC/PR 分頁 Finding 6 那次補上的寫法（同時涵蓋「本來就不支援」與「舊版結果缺欄位」兩種情況）

## 錯誤處理 / 相容性

- 舊的 workflow 執行結果沒有 `calibration_curve` 欄位，前端 `parseCalibrationCurve(undefined)` 第一行 `!value` 判斷就回傳 `null`，該分頁走空狀態文字，不會報錯崩潰
- bin 數量少的 fold（例如驗證集樣本數很少）產生的曲線點會比較稀疏，這是統計上正常的現象，不需要額外的「樣本太少」警告或特殊處理——`calibration_curve` 本身只回傳有資料的 bin，稀疏但仍然是有效資料

## 測試

- 後端無 pytest，前端無 vitest。用 `docker exec datamind-backend .venv/bin/python -m py_compile` 做語法檢查，前端用 `npm run type-check`
- 後端另外用一個小型 repro script（比照 ROC/PR 曲線那次最終審查用過的驗證方式）確認：二元分類正常情況回傳有效 dict；數值型 target 混雜 NaN 不會拋例外、回傳 `None`；多分類回傳 `None`
- 人工瀏覽器驗證：執行一次 workflow（二元分類資料集），點「Classification Evaluation」節點，確認：
  - 第四個分頁「校準曲線」能正常切換，切換模型 + fold 下拉時內容跟著變
  - 圖上看得到資料點（圓點）與連接線，加上對角線參考線
  - 用一個多分類資料集跑一次，確認校準曲線分頁顯示正確的空狀態文字，其他三個分頁不受影響
