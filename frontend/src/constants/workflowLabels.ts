// 前處理／特徵工程／驗證方法的中文標籤。workflow 設定面板與專案詳情頁共用，
// 兩處顯示的名稱必須一致
export const PREPROCESS_LABELS: Record<string, string> = {
  fill_na: '缺值填補',
  knn_impute: 'KNN 缺值填補',
  iterative_impute: 'MICE 多重插補',
  normalize: 'Min-Max 正規化',
  standardize: 'Z-score 標準化',
  one_hot: 'One-Hot 編碼',
  label_encode: 'Label 編碼',
  drop_columns: '移除欄位',
  remove_outliers_iqr: 'IQR 異常值處理',
  remove_outliers_zscore: 'Z-score 異常值處理',
}

export const FEATURE_LABELS: Record<string, string> = {
  select_relevant_features: '特徵選擇',
  pca: 'PCA 降維',
  discretize_continuous: '連續→離散',
  continuize_discrete: '離散→連續',
  normalize_features: '特徵正規化',
  remove_sparse_features: '移除稀疏特徵',
}

// 對應 backend/docs/workflow/resampling.md 列出的 resampling_method 值（不含 none）
export const RESAMPLING_LABELS: Record<string, string> = {
  smote: 'SMOTE 過採樣',
  adasyn: 'ADASYN 自適應過採樣',
  borderline_smote: 'Borderline-SMOTE 邊界過採樣',
  random_oversample: '隨機過採樣',
  random_undersample: '隨機欠採樣',
  smoteenn: 'SMOTE + ENN 複合採樣',
  smotetomek: 'SMOTE + Tomek 複合採樣',
}

export const VALIDATION_LABELS: Record<string, string> = {
  k_fold: 'Cross validation',
  group_k_fold: 'Cross validation by feature',
  random_sampling: 'Random sampling',
  leave_one_out: 'Leave one out',
  test_on_train: 'Test on train data',
  test_on_test: 'Test on test data',
}
