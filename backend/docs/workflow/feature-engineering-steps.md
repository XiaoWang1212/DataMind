# Supported Feature Engineering Steps

這份文件列出目前後端 feature engineering 可用的 step，並說明每個 step 的參數格式。

## 1. discretize_continuous

- 功能：將連續數值離散化成分箱類別。
- 參數：
  - `columns` (可選): 欄位陣列
  - `bins`: 分箱數，預設 5
  - `labels` (可選): 分箱標籤陣列

範例：

```json
{ "type": "discretize_continuous", "columns": ["age"], "bins": 4 }
```

## 2. continuize_discrete

- 功能：將類別欄位轉成數值編碼。
- 參數：
  - `columns` (可選): 欄位陣列

範例：

```json
{ "type": "continuize_discrete", "columns": ["color"] }
```

## 3. impute_missing

- 功能：填補缺失值。
- 參數：
  - `columns` (可選): 欄位陣列
  - `strategy`: `"constant"` / `"mean"` / `"median"` / `"mode"`
  - `value`: constant 填充值

範例：

```json
{ "type": "impute_missing", "strategy": "median" }
```

## 4. select_relevant_features

- 功能：選取最相關的數值特徵。
- 參數：
  - `k`: 選取前 k 個特徵，預設 10
  - `variance_threshold` (可選): 若未提供 target，則用變異數閾值過濾

範例：

```json
{ "type": "select_relevant_features", "k": 8 }
```

## 5. select_random_features

- 功能：隨機選取特徵。
- 參數：
  - `k`: 選取欄位數，預設最少 5
  - `random_state` (可選): 隨機種子

範例：

```json
{ "type": "select_random_features", "k": 5, "random_state": 42 }
```

## 6. normalize_features

- 功能：對數值欄位做 MinMax 正規化。
- 參數：
  - `columns` (可選): 欄位陣列

範例：

```json
{ "type": "normalize_features", "columns": ["age", "income"] }
```

## 7. randomize_rows

- 功能：隨機打亂資料列順序。
- 參數：
  - `random_state` (可選): 隨機種子

範例：

```json
{ "type": "randomize_rows", "random_state": 42 }
```

## 8. remove_sparse_features

- 功能：移除過多缺失值的數值欄位。
- 參數：
  - `threshold`: 最大缺失比例，預設 0.9

範例：

```json
{ "type": "remove_sparse_features", "threshold": 0.85 }
```

## 9. pca

- 功能：對數值欄位做主成分分析降維。
- 參數：
  - `n_components`: 主成分數，預設 2

範例：

```json
{ "type": "pca", "n_components": 3 }
```

## 10. cur_decomposition

- 功能：使用 CUR 分解對數值資料降維。
- 參數：
  - `n_components`: 分解維度，預設 2

範例：

```json
{ "type": "cur_decomposition", "n_components": 3 }
```
