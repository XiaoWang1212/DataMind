# 可用模型清單

此文件列出目前後端可用的預設模型（共 34 個），以及每個模型可支援的主要參數。

## 模型列表

### 線性模型

- Logistic Regression
- Logistic Regression CV
- Ridge Classifier
- Ridge Classifier CV
- Linear Discriminant Analysis
- Quadratic Discriminant Analysis
- SGD Classifier
- Passive Aggressive

### 支援向量機

- SVM
- Linear SVC
- Nu-SVC

### 近鄰法

- K-Nearest Neighbors
- Radius Neighbors

### 樹與集成

- Decision Tree
- Bagging
- Random Forest
- Extra Trees
- Gradient Boosting
- HistGradient Boosting
- AdaBoost
- Voting Classifier
- Stacking Classifier

### 神經網路

- MLP

### 機率模型

- Gaussian NB
- Multinomial NB
- Complement NB
- Bernoulli NB
- Gaussian Process
- Calibrated Classifier

### 第三方 Boosting

- XGBoost
- LightGBM
- CatBoost

### 不平衡資料專用

- Balanced Random Forest
- Easy Ensemble

## 可用參數範例

### Logistic Regression

- `penalty`
- `C`
- `l1_ratio`
- `dual`
- `tol`
- `fit_intercept`
- `class_weight`
- `solver`
- `max_iter`

### Logistic Regression CV

- `Cs`（要嘗試的 C 候選數量，內部自動 CV 選最佳）
- `cv`
- `penalty`
- `solver`
- `class_weight`
- `max_iter`

### Ridge Classifier CV

- `alphas`（要嘗試的 alpha 候選值 tuple，內部自動 CV 選最佳）
- `class_weight`
- `fit_intercept`

### Linear SVC

- `estimator__C`
- `estimator__loss`（`"hinge"` / `"squared_hinge"`）
- `estimator__class_weight`

> 注意：Linear SVC 內部以 CalibratedClassifierCV 包裝，因此有 predict_proba 支援。

### Nu-SVC

- `nu`（0 < nu ≤ 1，訓練誤差上限比例）
- `kernel`（`"linear"` / `"rbf"`）
- `class_weight`

### Gaussian Process

- `n_restarts_optimizer`
- `warm_start`
- `max_iter_predict`

> 注意：適合小資料集（< 1000 筆），大資料集訓練極慢。

### Voting Classifier

- `weights`（各 estimator 的投票權重）
- `lr__C`
- `rf__n_estimators`
- `svc__C`

> 預設使用 Logistic Regression + Random Forest + SVM 的 soft voting。

### Stacking Classifier

- `passthrough`（True/False，是否將原始特徵傳給 meta-learner）
- `final_estimator__C`

> 預設使用 LR + RF + ExtraTrees 作為 base，LR 作為 meta-learner。

### K-Nearest Neighbors

- `n_neighbors`
- `weights`
- `algorithm`
- `leaf_size`
- `p`
- `metric`
- `n_jobs`

### SVM

- `C`
- `kernel`
- `degree`
- `gamma`
- `coef0`
- `shrinking`
- `probability`
- `tol`
- `class_weight`
- `max_iter`
- `random_state`

### Decision Tree

- `criterion`
- `splitter`
- `max_depth`
- `min_samples_split`
- `min_samples_leaf`
- `max_features`
- `random_state`
- `class_weight`

### Ridge Classifier

- `alpha`
- `fit_intercept`
- `max_iter`
- `tol`
- `class_weight`
- `solver`
- `random_state`

### Linear Discriminant Analysis

- `solver`
- `shrinkage`
- `n_components`
- `tol`

### Quadratic Discriminant Analysis

- `reg_param`
- `store_covariance`
- `tol`

### MLP

- `hidden_layer_sizes`
- `activation`
- `solver`
- `alpha`
- `learning_rate`
- `max_iter`
- `early_stopping`
- `random_state`

### SGD Classifier

- `loss`
- `penalty`
- `alpha`
- `l1_ratio`
- `max_iter`
- `class_weight`
- `random_state`

### Bagging

- `n_estimators`
- `max_samples`
- `max_features`
- `bootstrap`
- `random_state`

### Random Forest

- `n_estimators`
- `criterion`
- `max_depth`
- `min_samples_leaf`
- `max_features`
- `bootstrap`
- `class_weight`
- `random_state`

### Extra Trees

- `n_estimators`
- `criterion`
- `max_depth`
- `min_samples_leaf`
- `class_weight`
- `random_state`

### Gradient Boosting

- `learning_rate`
- `n_estimators`
- `subsample`
- `max_depth`
- `random_state`

### HistGradient Boosting

- `learning_rate`
- `max_iter`
- `max_leaf_nodes`
- `max_depth`
- `early_stopping`
- `random_state`

### AdaBoost

- `n_estimators`
- `learning_rate`
- `random_state`

### Passive Aggressive

- `C`
- `max_iter`
- `class_weight`
- `random_state`

### Calibrated Classifier

- `estimator`
- `method`（`"sigmoid"` / `"isotonic"`）
- `cv`

### Gaussian NB

- `var_smoothing`

### Multinomial NB

- `alpha`
- `fit_prior`

### Complement NB

- `alpha`
- `norm`

### Bernoulli NB

- `alpha`
- `binarize`
- `fit_prior`

### Radius Neighbors

- `radius`
- `weights`
- `metric`

### XGBoost

- `objective`
- `n_estimators`
- `learning_rate`
- `max_depth`
- `subsample`
- `colsample_bytree`

### LightGBM

- `num_leaves`
- `max_depth`
- `learning_rate`
- `n_estimators`
- `subsample`
- `colsample_bytree`
- `reg_alpha`
- `reg_lambda`

### CatBoost

- `iterations`
- `learning_rate`
- `depth`
- `l2_leaf_reg`
- `loss_function`

### Balanced Random Forest

- `n_estimators`
- `max_depth`
- `sampling_strategy`
- `class_weight`
- `random_state`

### Easy Ensemble

- `n_estimators`
- `sampling_strategy`
- `random_state`
