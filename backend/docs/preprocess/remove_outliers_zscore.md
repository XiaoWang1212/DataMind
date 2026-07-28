# remove_outliers_zscore

這一份文件說明此預處理步驟的用途與參數。

## 類別: preprocess

## 說明

以 Z-score 方法偵測並處理異常值。計算每個數值欄位的均值與標準差，Z-score 絕對值超過 threshold 的值會被 clip（截斷至邊界值）。

均值與標準差從 train set 計算，套用到 train 與 test，不造成 data leakage。

## 可用參數

- `columns`（可選）：指定欄位，未指定則套用所有數值欄
- `threshold`（浮點數，預設 3.0）：Z-score 閾值，超過此值視為異常（3.0 約覆蓋 99.7% 正態分布）

## 範例

```json
{ "type": "remove_outliers_zscore", "threshold": 3.0 }
```
