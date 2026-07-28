# Class Imbalance Resampling

這份文件說明 workflow 中可用的類別不平衡處理方法。

## 說明

Resampling 只作用在 **train set**，test set 完全不碰，確保評估的公正性。

在 `execute_workflow` 呼叫時透過 `resampling_method` 參數指定。

## 可用方法

### none（預設）

不做任何 resampling。

### smote

SMOTE（Synthetic Minority Over-sampling Technique），對少數類合成新樣本（在 K 近鄰間插值），最常用的過採樣方法。

```json
{ "resampling_method": "smote", "resampling_config": { "k_neighbors": 5 } }
```

### adasyn

ADASYN（Adaptive Synthetic Sampling），自適應 SMOTE，在決策邊界附近的少數類樣本生成更多合成樣本。

```json
{ "resampling_method": "adasyn", "resampling_config": { "n_neighbors": 5 } }
```

### borderline_smote

只對靠近決策邊界的少數類樣本做 SMOTE，比標準 SMOTE 更聚焦在困難樣本。

```json
{
  "resampling_method": "borderline_smote",
  "resampling_config": { "k_neighbors": 5, "kind": "borderline-1" }
}
```

### random_oversample

隨機重複少數類樣本（無合成），簡單但有過擬合風險。

```json
{ "resampling_method": "random_oversample" }
```

### random_undersample

隨機刪除多數類樣本，速度快但會損失資訊。

```json
{ "resampling_method": "random_undersample" }
```

### smoteenn

SMOTE + Edited Nearest Neighbours，先過採樣再清除噪音樣本，通常效果優於單純 SMOTE。

```json
{ "resampling_method": "smoteenn" }
```

### smotetomek

SMOTE + Tomek Links 清除，效果與 SMOTEENN 類似。

```json
{ "resampling_method": "smotetomek" }
```

## 共通參數（resampling_config）

- `sampling_strategy`：採樣比例目標，`"auto"` 自動平衡、或指定數值（如 `0.5` 表示少數類樣本數達多數類的 50%）
- `random_state`（預設 42）

## 醫學資料建議

| 情境 | 建議方法 |
|---|---|
| 一般不平衡（比例 1:5 ~ 1:20）| smote |
| 嚴重不平衡（比例 1:20 以上） | smoteenn 或 smotetomek |
| 資料量極少（< 100 筆） | random_oversample |
| 多數類資料充足 | random_undersample |
