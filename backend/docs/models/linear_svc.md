# Linear SVC

這一份文件列出該模型可用的輸入參數。

## 類別: models

## 說明

線性核 SVM 的高效實作，訓練速度比 SVC(kernel='linear') 快，適合高維特徵（如基因組、文字特徵）。內部以 CalibratedClassifierCV 包裝，支援 predict_proba 輸出機率。

## 可用參數

- `estimator__C`（正則化強度，預設候選 `[0.01, 0.1, 1.0, 10.0]`）
- `estimator__loss`（`"hinge"` / `"squared_hinge"`，預設 `"squared_hinge"`）
- `estimator__class_weight`（`"balanced"` / `None`）
- `estimator__max_iter`（最大迭代次數，預設 2000）

> 注意：參數名稱需加 `estimator__` 前綴（因為外層是 CalibratedClassifierCV）。
