# Workflow Validation Strategy Examples

這份文件示範 `POST /api/models/workflow/execute` 的 `validation_config` 使用方式。

每個策略只能選一個 `method`，其他參數視該策略而定。

---

## 1. Cross validation

- `method`: `k_fold`
- `n_splits`: fold 數
- `stratified`: 是否使用 stratified split
- `shuffle`: 是否洗牌
- `random_state`: 隨機種子

```json
{
  "data_path": "uploads/workflow/example.csv",
  "target_col": "label",
  "preprocess_pipelines": [
    [
      { "type": "fill_na", "columns": ["age"], "strategy": "mean" },
      { "type": "one_hot", "columns": ["gender"] }
    ]
  ],
  "model_names": ["LogisticRegressionModel", "RandomForestModel"],
  "score_variants": [
    { "id": "score_variant_0", "metric": "accuracy" },
    { "id": "score_variant_1", "metric": "f1" }
  ],
  "validation_config": {
    "method": "k_fold",
    "n_splits": 5,
    "stratified": true,
    "shuffle": true,
    "random_state": 42
  }
}
```

---

## 2. Cross validation by feature

- `method`: `group_k_fold`
- `group_column`: 以哪個欄位當群組分割依據
- `n_splits`: fold 數

```json
{
  "data_path": "uploads/workflow/example.csv",
  "target_col": "label",
  "preprocess_pipelines": [
    [
      { "type": "drop_columns", "columns": ["id"] },
      { "type": "standardize", "columns": ["age", "income"] }
    ]
  ],
  "model_names": ["SVMModel"],
  "score_variants": [
    { "id": "score_variant_0", "metric": "precision" },
    { "id": "score_variant_1", "metric": "recall" }
  ],
  "validation_config": {
    "method": "group_k_fold",
    "n_splits": 4,
    "group_column": "hospital_id",
    "shuffle": false
  }
}
```

---

## 3. Random sampling

- `method`: `random_sampling`
- `n_repeats`: 重複 train/test 次數
- `train_size`: 訓練集比重
- `stratified`: 是否 stratified
- `shuffle`: 是否隨機洗牌
- `random_state`: 隨機種子

```json
{
  "data_path": "uploads/workflow/example.csv",
  "target_col": "label",
  "preprocess_pipelines": [
    [
      { "type": "fill_na", "columns": ["age"], "strategy": "median" },
      { "type": "label_encode", "columns": ["city"] }
    ]
  ],
  "model_names": ["DecisionTreeModel"],
  "score_variants": [{ "id": "score_variant_0", "metric": "accuracy" }],
  "validation_config": {
    "method": "random_sampling",
    "n_repeats": 10,
    "train_size": 0.66,
    "stratified": true,
    "shuffle": true,
    "random_state": 42
  }
}
```

---

## 4. Leave one out

- `method`: `leave_one_out`

```json
{
  "data_path": "uploads/workflow/example.csv",
  "target_col": "label",
  "preprocess_pipelines": [
    [
      { "type": "fill_na", "columns": ["age"], "strategy": "mean" },
      { "type": "one_hot", "columns": ["region"] }
    ]
  ],
  "model_names": ["LogisticRegressionModel"],
  "score_variants": [{ "id": "score_variant_0", "metric": "accuracy" }],
  "validation_config": {
    "method": "leave_one_out"
  }
}
```

---

## 5. Test on train data

- `method`: `test_on_train`
- `train_size`: 只會將資料切為 train/test，之後測試資料會使用 train 集
- `test_size`: 仍可指定，但實際測試組會使用同一 train 集

```json
{
  "data_path": "uploads/workflow/example.csv",
  "target_col": "label",
  "preprocess_pipelines": [
    [{ "type": "fill_na", "columns": ["age"], "strategy": "mean" }]
  ],
  "model_names": ["RandomForestModel"],
  "score_variants": [
    { "id": "score_variant_0", "metric": "accuracy" },
    { "id": "score_variant_1", "metric": "specificity" }
  ],
  "validation_config": {
    "method": "test_on_train",
    "train_size": 0.8,
    "stratified": true,
    "shuffle": true,
    "random_state": 42
  }
}
```

---

## 6. Test on test data

- `method`: `test_on_test`
- `train_size`: 訓練集比重
- `stratified`: 是否 stratified

```json
{
  "data_path": "uploads/workflow/example.csv",
  "target_col": "label",
  "preprocess_pipelines": [
    [
      { "type": "drop_columns", "columns": ["id"] },
      { "type": "standardize", "columns": ["age", "income"] }
    ]
  ],
  "model_names": ["SVMModel"],
  "score_variants": [
    { "id": "score_variant_0", "metric": "recall" },
    { "id": "score_variant_1", "metric": "f1" }
  ],
  "validation_config": {
    "method": "test_on_test",
    "train_size": 0.7,
    "stratified": true,
    "shuffle": true,
    "random_state": 42
  }
}
```
