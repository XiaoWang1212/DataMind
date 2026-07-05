# remove_outliers_iqr

這一份文件說明此預處理步驟的用途與參數。

## 類別: preprocess

## 說明

以 IQR（四分位距）方法偵測並處理異常值。計算每個數值欄位的 Q1、Q3，超出 `[Q1 - multiplier×IQR, Q3 + multiplier×IQR]` 範圍的值會被 clip（截斷至邊界值）而非刪除，避免 train/test 資料量不一致。

邊界值從 train set 計算，套用到 train 與 test，不造成 data leakage。

## 可用參數

- `columns`（可選）：指定欄位，未指定則套用所有數值欄
- `multiplier`（浮點數，預設 1.5）：IQR 倍數，值越大容忍範圍越寬（1.5 為標準異常值，3.0 為極端異常值）

## 範例

```json
{ "type": "remove_outliers_iqr", "multiplier": 1.5 }
```
