# Logistic Regression CV

這一份文件列出該模型可用的輸入參數。

## 類別: models

## 說明

Logistic Regression 的交叉驗證版本，內部自動以 CV 從 `Cs` 候選中選出最佳正則化強度，省去手動調 C 的步驟。適合醫學研究中的臨床預測模型建立。

## 可用參數

- `Cs`（要嘗試的 C 候選數量，預設 10，內部自動 CV 選最佳）
- `cv`（交叉驗證折數，預設 5）
- `penalty`（`"l2"` 或 `"l1"`，預設 `"l2"`）
- `solver`（`"lbfgs"` / `"saga"` / `"liblinear"`）
- `class_weight`（`"balanced"` / `None`）
- `max_iter`（最大迭代次數，預設 2000）
- `random_state`
- `n_jobs`
