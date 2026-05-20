# 可用模型清單

此文件列出目前後端可用的預設模型，以及每個模型可支援的主要參數。

## 模型列表

- Logistic Regression
- K-Nearest Neighbors
- SVM
- Decision Tree
- Ridge Classifier
- Linear Discriminant Analysis
- Quadratic Discriminant Analysis
- MLP
- SGD Classifier
- Bagging
- Random Forest
- Extra Trees
- Gradient Boosting
- HistGradient Boosting
- AdaBoost
- Passive Aggressive
- Calibrated Classifier
- Gaussian NB
- Multinomial NB
- Complement NB
- Bernoulli NB
- Radius Neighbors
- XGBoost
- LightGBM
- CatBoost
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
- `intercept_scaling`
- `class_weight`
- `random_state`
- `solver`
- `max_iter`
- `verbose`
- `warm_start`
- `n_jobs`

### K-Nearest Neighbors

- `n_neighbors`
- `weights`
- `algorithm`
- `leaf_size`
- `p`
- `metric`
- `metric_params`
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
- `cache_size`
- `class_weight`
- `verbose`
- `max_iter`
- `decision_function_shape`
- `break_ties`
- `random_state`

### Decision Tree

- `criterion`
- `splitter`
- `max_depth`
- `min_samples_split`
- `min_samples_leaf`
- `min_weight_fraction_leaf`
- `max_features`
- `random_state`
- `max_leaf_nodes`
- `min_impurity_decrease`
- `class_weight`
- `ccp_alpha`
- `monotonic_cst`

### Ridge Classifier

- `alpha`
- `fit_intercept`
- `copy_X`
- `max_iter`
- `tol`
- `class_weight`
- `solver`
- `positive`
- `random_state`

### Linear Discriminant Analysis

- `solver`
- `shrinkage`
- `priors`
- `n_components`
- `store_covariance`
- `tol`
- `covariance_estimator`

### Quadratic Discriminant Analysis

- `solver`
- `shrinkage`
- `priors`
- `reg_param`
- `store_covariance`
- `tol`
- `covariance_estimator`

### MLP

- `hidden_layer_sizes`
- `activation`
- `solver`
- `alpha`
- `batch_size`
- `learning_rate`
- `learning_rate_init`
- `power_t`
- `max_iter`
- `shuffle`
- `random_state`
- `tol`
- `verbose`
- `warm_start`
- `momentum`
- `nesterovs_momentum`
- `early_stopping`
- `validation_fraction`
- `beta_1`
- `beta_2`
- `epsilon`
- `n_iter_no_change`
- `max_fun`

### SGD Classifier

- `loss`
- `penalty`
- `alpha`
- `l1_ratio`
- `fit_intercept`
- `max_iter`
- `tol`
- `shuffle`
- `verbose`
- `epsilon`
- `n_jobs`
- `random_state`
- `learning_rate`
- `eta0`
- `power_t`
- `early_stopping`
- `validation_fraction`
- `n_iter_no_change`
- `class_weight`
- `warm_start`
- `average`

### Bagging

- `estimator`
- `n_estimators`
- `max_samples`
- `max_features`
- `bootstrap`
- `bootstrap_features`
- `oob_score`
- `warm_start`
- `n_jobs`
- `random_state`
- `verbose`

### Random Forest

- `n_estimators`
- `criterion`
- `max_depth`
- `min_samples_split`
- `min_samples_leaf`
- `min_weight_fraction_leaf`
- `max_features`
- `max_leaf_nodes`
- `min_impurity_decrease`
- `bootstrap`
- `oob_score`
- `n_jobs`
- `random_state`
- `verbose`
- `warm_start`
- `class_weight`
- `ccp_alpha`
- `max_samples`
- `monotonic_cst`

### Extra Trees

- `n_estimators`
- `criterion`
- `max_depth`
- `min_samples_split`
- `min_samples_leaf`
- `min_weight_fraction_leaf`
- `max_features`
- `max_leaf_nodes`
- `min_impurity_decrease`
- `bootstrap`
- `oob_score`
- `n_jobs`
- `random_state`
- `verbose`
- `warm_start`
- `class_weight`
- `ccp_alpha`
- `max_samples`
- `monotonic_cst`

### Gradient Boosting

- `loss`
- `learning_rate`
- `n_estimators`
- `subsample`
- `criterion`
- `min_samples_split`
- `min_samples_leaf`
- `min_weight_fraction_leaf`
- `max_depth`
- `min_impurity_decrease`
- `init`
- `random_state`
- `max_features`
- `verbose`
- `max_leaf_nodes`
- `warm_start`
- `validation_fraction`
- `n_iter_no_change`
- `tol`
- `ccp_alpha`

### HistGradient Boosting

- `loss`
- `learning_rate`
- `max_iter`
- `max_leaf_nodes`
- `max_depth`
- `min_samples_leaf`
- `l2_regularization`
- `max_features`
- `max_bins`
- `categorical_features`
- `monotonic_cst`
- `interaction_cst`
- `warm_start`
- `early_stopping`
- `scoring`
- `validation_fraction`
- `n_iter_no_change`
- `tol`
- `verbose`
- `random_state`
- `class_weight`

### AdaBoost

- `estimator`
- `n_estimators`
- `learning_rate`
- `random_state`

### Passive Aggressive

- `C`
- `fit_intercept`
- `max_iter`
- `tol`
- `early_stopping`
- `validation_fraction`
- `n_iter_no_change`
- `shuffle`
- `verbose`
- `loss`
- `n_jobs`
- `random_state`
- `warm_start`
- `class_weight`
- `average`

### Calibrated Classifier

- `estimator`
- `method`
- `cv`
- `n_jobs`
- `ensemble`

### Gaussian NB

- `priors`
- `var_smoothing`

### Multinomial NB

- `alpha`
- `force_alpha`
- `fit_prior`
- `class_prior`

### Complement NB

- `alpha`
- `force_alpha`
- `fit_prior`
- `class_prior`
- `norm`

### Bernoulli NB

- `alpha`
- `force_alpha`
- `binarize`
- `fit_prior`
- `class_prior`

### Radius Neighbors

- `radius`
- `weights`
- `algorithm`
- `leaf_size`
- `p`
- `metric`
- `outlier_label`
- `metric_params`
- `n_jobs`

### XGBoost

- `objective`

### LightGBM

- `boosting_type`
- `num_leaves`
- `max_depth`
- `learning_rate`
- `n_estimators`
- `subsample_for_bin`
- `objective`
- `class_weight`
- `min_split_gain`
- `min_child_weight`
- `min_child_samples`
- `subsample`
- `subsample_freq`
- `colsample_bytree`
- `reg_alpha`
- `reg_lambda`
- `random_state`
- `n_jobs`
- `importance_type`

### CatBoost

- `iterations`
- `learning_rate`
- `depth`
- `l2_leaf_reg`
- `model_size_reg`
- `rsm`
- `loss_function`
- `border_count`
- `feature_border_type`
- `per_float_feature_quantization`
- `input_borders`
- `output_borders`
- `fold_permutation_block`
- `od_pval`
- `od_wait`
- `od_type`
- `nan_mode`
- `counter_calc_method`
- `leaf_estimation_iterations`
- `leaf_estimation_method`
- `thread_count`
- `random_seed`
- `use_best_model`
- `best_model_min_trees`
- `verbose`
- `silent`
- `logging_level`
- `metric_period`
- `ctr_leaf_count_limit`
- `store_all_simple_ctr`
- `max_ctr_complexity`
- `has_time`
- `allow_const_label`
- `target_border`
- `classes_count`
- `class_weights`
- `auto_class_weights`
- `class_names`
- `one_hot_max_size`
- `random_strength`
- `random_score_type`
- `name`
- `ignored_features`
- `train_dir`
- `custom_loss`
- `custom_metric`
- `eval_metric`
- `bagging_temperature`
- `save_snapshot`
- `snapshot_file`
- `snapshot_interval`
- `used_ram_limit`
- `gpu_ram_part`
- `pinned_memory_size`
- `allow_writing_files`
- `final_ctr_computation_mode`
- `approx_on_full_history`
- `boosting_type`
- `simple_ctr`
- `combinations_ctr`
- `per_feature_ctr`
- `ctr_description`
- `ctr_target_border_count`
- `task_type`
- `device_config`
- `devices`
- `bootstrap_type`
- `subsample`
- `mvs_reg`
- `sampling_unit`
- `sampling_frequency`
- `dev_score_calc_obj_block_size`
- `dev_efb_max_buckets`
- `dev_efb_max_buckets`
- `max_depth`
- `n_estimators`
- `num_boost_round`
- `num_trees`
- `colsample_bylevel`
- `random_state`
- `reg_lambda`
- `objective`
- `eta`
- `max_bin`
- `scale_pos_weight`
- `gpu_cat_features_storage`
- `data_partition`
- `metadata`
- `early_stopping_rounds`
- `cat_features`
- `grow_policy`
- `min_data_in_leaf`
- `min_child_samples`
- `max_leaves`
- `num_leaves`
- `score_function`
- `leaf_estimation_backtracking`
- `ctr_history_unit`
- `monotone_constraints`
- `feature_weights`
- `penalties_coefficient`
- `first_feature_use_penalties`
- `per_object_feature_penalties`
- `model_shrink_rate`
- `model_shrink_mode`
- `langevin`
- `diffusion_temperature`
- `posterior_sampling`
- `boost_from_average`
- `text_features`
- `tokenizers`
- `dictionaries`
- `feature_calcers`
- `text_processing`
- `embedding_features`
- `callback`
- `eval_fraction`
- `fixed_binary_splits`

### Balanced Random Forest

- `n_estimators`
- `criterion`
- `max_depth`
- `min_samples_split`
- `min_samples_leaf`
- `min_weight_fraction_leaf`
- `max_features`
- `max_leaf_nodes`
- `min_impurity_decrease`
- `bootstrap`
- `oob_score`
- `sampling_strategy`
- `replacement`
- `n_jobs`
- `random_state`
- `verbose`
- `warm_start`
- `class_weight`
- `ccp_alpha`
- `max_samples`
- `monotonic_cst`

### Easy Ensemble

- `n_estimators`
- `estimator`
- `warm_start`
- `sampling_strategy`
- `replacement`
- `n_jobs`
- `random_state`
- `verbose`
