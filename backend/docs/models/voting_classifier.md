# Voting Classifier

這一份文件列出該模型可用的輸入參數。

## 類別: models

## 說明

多模型投票集成，預設使用 Logistic Regression + Random Forest + SVM 進行 soft voting（機率平均），提升單一模型的穩定性。適合作為論文中的集成基線方法。

## 預設 Base Estimators

- `lr`：Logistic Regression（class_weight=balanced）
- `rf`：Random Forest（n_estimators=100, class_weight=balanced）
- `svc`：SVC（probability=True）

## 可用參數

- `voting`（`"soft"` / `"hard"`，預設 `"soft"`；soft 使用機率平均，hard 使用多數投票）
- `weights`（各 estimator 的投票權重，`None` 表示等權，例如 `[1, 2, 1]`）
- `lr__C`（LR 的正則化強度）
- `rf__n_estimators`（RF 的樹數量）
- `svc__C`（SVC 的正則化強度）
