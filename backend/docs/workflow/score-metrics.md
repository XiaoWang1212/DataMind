# Supported Score Metrics

這份文件列出目前後端可用的評分指標（共 10 個），並說明 score variant 可用參數。

> 所有指標皆支援選填 `compute_ci: true` 開啟 Bootstrap 95% 信賴區間（論文常用）。

## 基本分類指標

### 1. accuracy

- 功能：正確率，所有預測中正確的比例。
- 適用：類別平衡時的首選指標。
- 參數：
  - `metric`: `"accuracy"`
  - `threshold` (可選): 以 y_score 做二元閾值

### 2. balanced_accuracy

- 功能：平衡正確率，各類別召回率的平均值。
- 適用：**類別不平衡時比 accuracy 更可靠**，醫學資料推薦優先使用。
- 參數：
  - `metric`: `"balanced_accuracy"`

### 3. precision

- 功能：精確率，預測為正例中真正正例的比例。
- 參數：
  - `metric`: `"precision"`
  - `threshold` (可選)
  - `pos_label` (可選)
  - `labels` (可選)

### 4. recall

- 功能：召回率（敏感度），真正正例中被正確預測的比例。
- 參數：
  - `metric`: `"recall"`
  - `threshold` (可選)
  - `pos_label` (可選)

### 5. specificity

- 功能：特異度，真正負例中被正確預測的比例（1 - FPR）。
- 適用：醫學篩檢中避免偽陽性的重要指標。
- 參數：
  - `metric`: `"specificity"`
  - `threshold` (可選)
  - `labels` (可選)

### 6. f1

- 功能：F1 分數，precision 與 recall 的調和平均。
- 參數：
  - `metric`: `"f1"`
  - `threshold` (可選)
  - `pos_label` (可選)

## 進階分類指標

### 7. mcc

- 功能：Matthews Correlation Coefficient，綜合考量 TP/TN/FP/FN 的相關係數。
- 適用：**類別嚴重不平衡時最可靠的綜合指標**，範圍 [-1, 1]，1 為完美預測。
- 參數：
  - `metric`: `"mcc"`

### 8. kappa

- 功能：Cohen's Kappa，考慮隨機一致性後的分類一致性係數。
- 適用：醫學評分者一致性研究，> 0.8 視為高度一致。
- 參數：
  - `metric`: `"kappa"`

### 9. auc

- 功能：ROC AUC，模型區分正負例的整體能力。
- 適用：類別相對平衡時的標準指標。
- 參數：
  - `metric`: `"auc"`

### 10. auprc

- 功能：Precision-Recall Curve 面積（Average Precision）。
- 適用：**類別嚴重不平衡時比 AUC-ROC 更有意義**（如罕見疾病偵測）。
- 參數：
  - `metric`: `"auprc"`

## Score Variant 範例

```json
[
  { "id": "s0", "metric": "balanced_accuracy" },
  { "id": "s1", "metric": "auc" },
  { "id": "s2", "metric": "auprc" },
  { "id": "s3", "metric": "mcc" },
  { "id": "s4", "metric": "f1", "threshold": 0.5, "pos_label": 1 }
]
```

## 信賴區間（Bootstrap CI）

在呼叫 workflow 時加入 `compute_ci: true`，回傳結果會附上每個指標的 95% CI：

```json
{
  "metric": "auc",
  "value": 0.872,
  "ci_lower": 0.841,
  "ci_upper": 0.903,
  "ci_level": 0.95
}
```

## 醫學研究建議指標組合

| 情境 | 建議指標 |
|---|---|
| 類別平衡 | accuracy, auc, f1 |
| 類別不平衡 | balanced_accuracy, mcc, auprc |
| 篩檢（避免漏診） | recall, specificity |
| 論文報告 | auc, auprc, mcc + CI |
