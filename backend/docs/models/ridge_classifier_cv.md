# Ridge Classifier CV

這一份文件列出該模型可用的輸入參數。

## 類別: models

## 說明

Ridge Classifier 的交叉驗證版本，內部自動從 `alphas` 候選中選出最佳正則化強度。速度快，適合高維特徵的分類問題。

## 可用參數

- `alphas`（要嘗試的 alpha 候選值 tuple，預設 `(0.1, 1.0, 10.0, 100.0)`，內部自動 CV 選最佳）
- `class_weight`（`"balanced"` / `None`）
- `fit_intercept`（`True` / `False`）
- `scoring`（CV 評分方式，預設 `None` 使用 R²）
- `cv`（折數，`None` 使用 Leave-One-Out）
