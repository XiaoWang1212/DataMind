# iterative_impute

這一份文件說明此預處理步驟的用途與參數。

## 類別: preprocess

## 說明

MICE（Multiple Imputation by Chained Equations）多重插補法。以迭代方式用其他欄位預測缺值欄位，每輪迭代更新所有缺值欄位直到收斂。適合缺值呈 MAR（Missing At Random）或 MNAR（Missing Not At Random）分布的醫學資料，例如住院記錄、電子病歷。

## 可用參數

- `max_iter`（整數，預設 10）：最大迭代輪數
- `random_state`（整數，預設 42）：隨機種子，確保可重現性

## 範例

```json
{ "type": "iterative_impute", "max_iter": 10, "random_state": 42 }
```
