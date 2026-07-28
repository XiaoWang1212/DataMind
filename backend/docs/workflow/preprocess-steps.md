# Supported Workflow Preprocess Steps

這份文件列出目前後端 workflow 預處理可用的 step，並說明每個 step 的參數格式。

> **重要**：所有 stateful 操作（normalize、standardize、encode、impute）皆以 train set fit、test set transform 的方式執行，**不會造成 data leakage**。

## 1. drop_columns

- 功能：移除不想使用的欄位。
- 參數：
  - `columns`: 欄位名稱陣列

```json
{ "type": "drop_columns", "columns": ["id", "timestamp"] }
```

## 2. fill_na

- 功能：填補缺失值（策略參數從 train 學習，再套用到 test）。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用至全欄位
  - `strategy`: `"constant"` / `"mean"` / `"median"` / `"mode"`
  - `value`: 當 strategy 為 constant 時的填充值

```json
{ "type": "fill_na", "columns": ["age"], "strategy": "mean" }
```

## 3. knn_impute

- 功能：KNN 缺值填補，以相鄰樣本的數值推算缺值（比 mean/median 更精確，適合有複雜缺值模式的醫學資料）。
- 參數：
  - `n_neighbors` (預設 5): 用於填補的鄰近樣本數

```json
{ "type": "knn_impute", "n_neighbors": 5 }
```

## 4. iterative_impute

- 功能：MICE（多重插補法），以其他欄位迭代預測缺值，適合缺值呈 MAR/MNAR 分布的醫學資料。
- 參數：
  - `max_iter` (預設 10): 最大迭代次數
  - `random_state` (預設 42)

```json
{ "type": "iterative_impute", "max_iter": 10, "random_state": 42 }
```

## 5. normalize

- 功能：MinMax 縮放數值，範圍為 [0, 1]（scaler 從 train fit）。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用所有數值欄

```json
{ "type": "normalize", "columns": ["age", "income"] }
```

## 6. standardize

- 功能：Z-score 標準化（scaler 從 train fit）。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用所有數值欄

```json
{ "type": "standardize", "columns": ["age", "income"] }
```

## 7. one_hot

- 功能：對類別欄位做 One-Hot Encoding（類別對照從 train fit，test 未見類別填 0）。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用所有 object/category 欄

```json
{ "type": "one_hot", "columns": ["gender", "country"] }
```

## 8. label_encode

- 功能：對類別欄位做 Label Encoding（Encoder 從 train fit，test 未見類別標記為 -1）。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用所有 object/category 欄

```json
{ "type": "label_encode", "columns": ["city"] }
```

## 9. remove_outliers_iqr

- 功能：以 IQR 方法偵測異常值並 clip（邊界從 train 計算，test 套用同樣邊界，不影響資料量）。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用所有數值欄
  - `multiplier` (預設 1.5): IQR 倍數，值越大容忍範圍越寬

```json
{ "type": "remove_outliers_iqr", "multiplier": 1.5 }
```

## 10. remove_outliers_zscore

- 功能：以 Z-score 方法偵測異常值並 clip（均值與標準差從 train 計算）。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用所有數值欄
  - `threshold` (預設 3.0): Z-score 閾值，超過此值視為異常

```json
{ "type": "remove_outliers_zscore", "threshold": 3.0 }
```
