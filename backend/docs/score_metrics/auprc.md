# AUPRC（Area Under Precision-Recall Curve）

這一份文件說明可用的 score metric 及其設定。

## 類別: score_metrics

## 說明

Precision-Recall Curve 下的面積，即 Average Precision（AP）。在類別不平衡時比 AUC-ROC 更能反映模型對正例的識別能力，因為它不考慮 TN（大量負例使 AUC-ROC 虛高）。

## 適用場景

- **類別嚴重不平衡時取代 AUC 使用**（如罕見疾病偵測、異常值偵測）
- 正例樣本數極少的情境
- 論文要求報告 PR Curve 相關指標時

## 與 AUC 的差異

- AUC-ROC：計算 TPR vs FPR，負例很多時仍容易得到高分
- AUPRC：計算 Precision vs Recall，更聚焦在正例的識別品質

## 可用參數

- `metric`: `"auprc"`

## 範例

```json
{ "id": "s0", "metric": "auprc" }
```
