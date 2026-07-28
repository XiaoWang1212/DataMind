# Gaussian Process

這一份文件列出該模型可用的輸入參數。

## 類別: models

## 說明

高斯過程分類器，天然輸出機率且可量化預測不確定性。適合樣本數較少（< 1000 筆）的醫學資料集，如稀有疾病、小型臨床試驗。

**警告**：訓練複雜度為 O(n³)，資料量超過 1000 筆訓練會非常慢。

## 可用參數

- `n_restarts_optimizer`（核函數超參數優化的重新啟動次數，預設 0）
- `warm_start`（`True` / `False`，重用上次的解作初始值）
- `max_iter_predict`（Newton 法預測迭代上限，預設 100）
- `random_state`
- `n_jobs`
