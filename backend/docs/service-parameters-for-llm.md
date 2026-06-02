# 後端 Service 參數清單（給 LLM 的參考）

這份文件整理了目前後端可用的 Service 與參數格式，方便你把論文中的奇怪 method 名稱轉成後端可執行的 workflow。

---

## 1. Workflow / ML 執行服務

### `POST /api/models/workflow/execute`

用途：執行資料前處理、模型訓練 / 驗證、評分。

支持的參數：

- `data_path`：已上傳 CSV 的路徑（string）
- `target_col`：目標欄位名稱（string）
- `preprocess_pipelines`：前處理 pipeline 清單（array of pipelines）
- `model_names`：要執行的模型名稱陣列（array of string）
- `score_variants`：評分指標清單（array of score variant）
- `validation_config`：驗證策略配置（object）
- `train_size`：train/test 分割比例（float，預設 0.7）
- `random_state`：隨機種子（int，預設 42）

#### `preprocess_pipelines` 範例

```json
[[{ "type": "fill_na", "strategy": "mean" }, { "type": "standardize" }]]
```

#### `score_variants` 範例

```json
[
  { "id": "score_variant_0", "metric": "accuracy" },
  { "id": "score_variant_1", "metric": "f1" }
]
```

#### `validation_config` 範例

- `test_on_test`

```json
{
  "method": "test_on_test",
  "train_size": 0.7,
  "stratified": true,
  "shuffle": true,
  "random_state": 42
}
```

- `k_fold`

```json
{
  "method": "k_fold",
  "n_splits": 5,
  "stratified": true,
  "shuffle": true,
  "random_state": 42
}
```

- `group_k_fold`

```json
{
  "method": "group_k_fold",
  "n_splits": 4,
  "group_column": "hospital_id"
}
```

- `random_sampling`

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

- `leave_one_out`

```json
{
  "method": "leave_one_out"
}
```

- `test_on_train`

```json
{
  "method": "test_on_train",
  "train_size": 0.8,
  "stratified": true,
  "shuffle": true,
  "random_state": 42
}
```

---

## 2. Preprocess / Feature Engineering 服務

### `POST /api/models/preprocess/variants`

用途：根據步驟組合產生前處理 variant 清單。

- `step_groups`: group list

範例：

```json
{
  "step_groups": [
    {
      "name": "missing",
      "options": [
        { "type": "fill_na", "strategy": "mean", "label": "mean" },
        { "type": "fill_na", "strategy": "median", "label": "median" }
      ]
    },
    {
      "name": "scale",
      "options": [
        { "type": "standardize", "label": "standard" },
        { "type": "normalize", "label": "minmax" }
      ]
    }
  ]
}
```

### `POST /api/models/score/variants`

用途：根據 score group 產生 Score Variant 清單。

- `score_groups`: group list

範例：

```json
{
  "score_groups": [
    {
      "name": "metric",
      "options": [{ "metric": "accuracy" }, { "metric": "f1" }]
    }
  ]
}
```

---

## 3. 其他支援服務

### `POST /api/models/extract-components`

用途：從模型描述 JSON 中抽取 `name` / `type` / `purpose`。

支持：

- 上傳 JSON file
- JSON body
- `model_names`: 指定要抽取的模型名稱

範例：

```json
{
  "models": [
    { "name": "Decision Tree", "type": "分類模型", "purpose": "特徵選擇" }
  ]
}
```

---

## 4. Paper / LLM 相關服務

### `POST /api/gemini/ai-analyze`

用途：用 Gemini 進行論文技術解讀與結構化抽取。

參數：

- `title`：標題
- `content`：論文文本
- `focus`：關注重點
- `language`：語言（例如 `zh-TW`）
- `mode`: `summary` / `extract`
- `save_output`: 是否儲存結果
- `output_filename`: 儲存檔名

### `POST /api/rag/upload`

用途：上傳論文到 RAG 索引。

支持：

- file 上傳（txt / md / pdf）
- JSON body：`title`, `content`, `author`, `year`

### `POST /api/rag/search`

用途：搜尋論文片段。

參數：

- `query`：查詢文字
- `top_k`：返回數量，預設 5
- `use_rerank`：是否 rerank，預設 true

### `POST /api/rag/cite`

用途：生成引用文本。

參數：

- `query`：查詢文字
- `top_k`：引用數量，預設 3
- `style`：引用格式，預設 `apa`

### `GET /api/rag/status`

用途：檢查 RAG 服務狀態。

### `POST /api/rag/clear`

用途：清空 RAG 索引。

### `DELETE /api/rag/paper/<paper_id>`

用途：刪除單篇論文索引。

---

## 5. 語音與資料訓練服務

### `POST /api/stt/transcribe`

用途：語音轉文字。

參數：

- `audio`：音檔上傳（wav / mp3 / m4a / webm / ogg / mp4 / mpeg / mpga）
- `language`：語言（可選）
- `prompt`：轉錄提示
- `temperature`：模型溫度（可選）

### `POST /api/ml/pycaret/train`

用途：PyCaret 模型訓練。

參數：

- `file`：CSV 檔案上傳
- `target_col`：目標欄位，預設 `是否跌倒`
- `output_dir`：儲存結果路徑

---

## 6. LLM 過濾建議

### 建議給 LLM 的輸入資訊

1. `service_name`：要匹配的後端服務名稱
2. `field`：原始論文中的 method 名稱與描述
3. `normalized_name`：轉成後端可用的 standard step / method
4. `parameters`：對應後端所需參數

### 例子

```json
{
  "source": "Paper says use min-max scaling",
  "normalized": "normalize",
  "service": "workflow",
  "params": {
    "type": "normalize",
    "columns": ["age", "income"]
  }
}
```

### 核心原則

- 先把論文敘述轉成後端支援的 `method`
- 再填入對應參數
- `validation_config.method` 只能選一個主流程
- `preprocess_pipelines` 與 `score_variants` 都要用結構化 JSON

---

## 7. 目前可用的 Workflow preprocessor step

- `drop_columns`
- `fill_na`
- `normalize`
- `standardize`
- `one_hot`
- `label_encode`

## 8. 目前可用的 Feature Engineering step

- `discretize_continuous`
- `continuize_discrete`
- `impute_missing`
- `select_relevant_features`
- `select_random_features`
- `normalize_features`
- `randomize_rows`
- `remove_sparse_features`
- `pca`
- `cur_decomposition`
