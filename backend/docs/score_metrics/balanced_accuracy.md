# Balanced Accuracy

這一份文件說明可用的 score metric 及其設定。

## 類別: score_metrics

## 說明

各類別召回率的算術平均值。當類別不平衡時（如正例 5%、負例 95%），標準 accuracy 會被多數類主導而失真，balanced_accuracy 能公平反映各類別的分類表現。

公式：`(Sensitivity + Specificity) / 2`（二元分類）

## 適用場景

- 醫學資料（疾病陽性率通常低）
- 類別不平衡的分類問題
- 作為 accuracy 的替代指標

## 可用參數

- `metric`: `"balanced_accuracy"`

## 範例

```json
{ "id": "s0", "metric": "balanced_accuracy" }
```
