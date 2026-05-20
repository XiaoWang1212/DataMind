# Supported Validation Strategies

此文件列出後端 workflow 支援的所有驗證策略，以及對應的參數格式。

## 1. test_on_test

- 功能：做一次 train/test split，使用測試集評估。
- 參數：
  - `method`: `"test_on_test"`
  - `train_size`: 訓練集比例
  - `test_size` (可選): 測試集比例，若未提供則為 `1.0 - train_size`
  - `stratified`: 是否分層抽樣
  - `shuffle`: 是否洗牌
  - `random_state`: 隨機種子

範例：

```json
{
  "method": "test_on_test",
  "train_size": 0.7,
  "stratified": true,
  "shuffle": true,
  "random_state": 42
}
```

## 2. test_on_train

- 功能：切出 train 集後，使用同一 train 集做測試。
- 參數：
  - `method`: `"test_on_train"`
  - `train_size`
  - `stratified`
  - `shuffle`
  - `random_state`

範例：

```json
{
  "method": "test_on_train",
  "train_size": 0.8,
  "stratified": true,
  "shuffle": true,
  "random_state": 42
}
```

## 3. k_fold

- 功能：K 折交叉驗證。
- 參數：
  - `method`: `"k_fold"`
  - `n_splits`: fold 數
  - `stratified`: 是否分層
  - `shuffle`
  - `random_state`

範例：

```json
{
  "method": "k_fold",
  "n_splits": 5,
  "stratified": true,
  "shuffle": true,
  "random_state": 42
}
```

## 4. group_k_fold

- 功能：依群組欄位做交叉驗證。
- 參數：
  - `method`: `"group_k_fold"`
  - `n_splits`
  - `group_column`: 作為群組依據的欄位名稱

範例：

```json
{
  "method": "group_k_fold",
  "n_splits": 4,
  "group_column": "hospital_id"
}
```

## 5. random_sampling

- 功能：重複做 train/test random split。
- 參數：
  - `method`: `"random_sampling"`
  - `n_repeats`
  - `train_size`
  - `stratified`
  - `shuffle`
  - `random_state`

範例：

```json
{
  "method": "random_sampling",
  "n_repeats": 10,
  "train_size": 0.66,
  "stratified": true,
  "shuffle": true,
  "random_state": 42
}
```

## 6. leave_one_out

- 功能：Leave-One-Out 驗證，每一筆資料作為一次測試集。
- 參數：
  - `method`: `"leave_one_out"`

範例：

```json
{
  "method": "leave_one_out"
}
```
