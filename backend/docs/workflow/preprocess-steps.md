# Supported Workflow Preprocess Steps

這份文件列出目前後端 workflow 預處理可用的 step，並說明每個 step 的參數格式。

## 1. drop_columns

- 功能：移除不想使用的欄位。
- 參數：
  - `columns`: 欄位名稱陣列

範例：

```json
{ "type": "drop_columns", "columns": ["id", "timestamp"] }
```

## 2. fill_na

- 功能：填補缺失值。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用至全欄位
  - `strategy`: `"constant"` / `"mean"` / `"median"`
  - `value`: 當 strategy 為 constant 時的填充值

範例：

```json
{ "type": "fill_na", "columns": ["age"], "strategy": "mean" }
```

## 3. normalize

- 功能：MinMax 缩放數值，範圍為 [0, 1]。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用所有數值欄

範例：

```json
{ "type": "normalize", "columns": ["age", "income"] }
```

## 4. standardize

- 功能：Z-score 標準化。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用所有數值欄

範例：

```json
{ "type": "standardize", "columns": ["age", "income"] }
```

## 5. one_hot

- 功能：對類別欄位做 One-Hot Encoding。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用所有 object/category 欄

範例：

```json
{ "type": "one_hot", "columns": ["gender", "country"] }
```

## 6. label_encode

- 功能：對類別欄位做 Label Encoding。
- 參數：
  - `columns` (可選): 欄位陣列，若未指定則套用所有 object/category 欄

範例：

```json
{ "type": "label_encode", "columns": ["city"] }
```
