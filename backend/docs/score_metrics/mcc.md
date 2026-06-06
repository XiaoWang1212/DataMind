# MCC（Matthews Correlation Coefficient）

這一份文件說明可用的 score metric 及其設定。

## 類別: score_metrics

## 說明

Matthews 相關係數，同時考量 TP、TN、FP、FN 的綜合指標，等同於預測值與真實值的相關係數。

公式：`MCC = (TP×TN - FP×FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))`

範圍 [-1, 1]：1 = 完美預測，0 = 隨機猜測，-1 = 完全反預測。

## 適用場景

- **類別嚴重不平衡時最推薦的單一指標**（比 F1 更全面）
- 醫學診斷模型的效能評估
- 論文中需要一個公正的綜合指標時

## 可用參數

- `metric`: `"mcc"`

## 範例

```json
{ "id": "s0", "metric": "mcc" }
```
