# Stacking Classifier

這一份文件列出該模型可用的輸入參數。

## 類別: models

## 說明

Stacking 集成，以 cross-validation 的方式取得 base estimator 的預測作為特徵，再用 meta-learner 學習如何組合。通常能獲得比單一模型更好的效果，醫學論文中常作為最終模型。

## 預設 Base Estimators

- `lr`：Logistic Regression（class_weight=balanced）
- `rf`：Random Forest（n_estimators=100, class_weight=balanced）
- `et`：Extra Trees（n_estimators=100, class_weight=balanced）

## Meta-learner

- Logistic Regression

## 可用參數

- `passthrough`（`True` / `False`，是否將原始特徵一併傳給 meta-learner，預設 `False`）
- `final_estimator__C`（meta-learner LR 的正則化強度）
- `stack_method`（`"auto"` / `"predict_proba"` / `"decision_function"`）
- `cv`（base estimator 的交叉驗證折數，預設 5）
