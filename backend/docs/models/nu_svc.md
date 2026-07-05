# Nu-SVC

這一份文件列出該模型可用的輸入參數。

## 類別: models

## 說明

SVM 的另一種形式，以 `nu` 參數控制訓練誤差上限比例與支援向量數下限。當標準 SVC 收斂困難時可嘗試，支援 predict_proba。

## 可用參數

- `nu`（訓練誤差上限比例，範圍 (0, 1]，預設候選 `[0.1, 0.25, 0.5]`）
- `kernel`（`"linear"` / `"rbf"` / `"poly"` / `"sigmoid"`）
- `degree`（多項式核的次數，僅 kernel='poly' 時有效）
- `gamma`（`"scale"` / `"auto"` 或數值）
- `class_weight`（`"balanced"` / `None`）
- `probability`（固定為 `True`）
- `random_state`
