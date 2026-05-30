# Supported Score Metrics

這份文件列出目前後端可用的評分指標，並說明 score variant 可用參數。

## 1. accuracy

- 功能：正確率。
- 參數：
  - `metric`: `"accuracy"`
  - `threshold` (可選): 若使用 `y_score` 做二元閾值則可指定
  - `pos_label` (可選)
  - `labels` (可選)

## 2. precision

- 功能：精確率。
- 參數：
  - `metric`: `"precision"`
  - `threshold` (可選)
  - `pos_label` (可選)
  - `labels` (可選)

## 3. recall

- 功能：召回率。
- 參數：
  - `metric`: `"recall"`
  - `threshold` (可選)
  - `pos_label` (可選)
  - `labels` (可選)

## 4. f1

- 功能：F1 分數。
- 參數：
  - `metric`: `"f1"`
  - `threshold` (可選)
  - `pos_label` (可選)
  - `labels` (可選)

## 5. auc

- 功能：ROC AUC 分數。
- 參數：
  - `metric`: `"auc"`
  - `threshold`: 不必要，僅需 `y_score`

## 6. specificity

- 功能：特異度。
- 參數：
  - `metric`: `"specificity"`
  - `threshold` (可選)
  - `labels` (可選)

## Score Variant 範例

```json
{
  "metric": "precision",
  "threshold": 0.5,
  "pos_label": 1
}
```

## 變成 score variant list 的格式

通常會用 `POST /api/models/score/variants` 先產生 variants，或直接手動傳：

```json
[
  { "id": "score_variant_0", "metric": "accuracy" },
  { "id": "score_variant_1", "metric": "f1" }
]
```
