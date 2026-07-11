export const mockMiningResults = {
  success: true,
  class_distribution: {
    counts: { 0: 9820, 1: 2180 },
    imbalance_ratio: 4.5046,
  },
  preprocess_variants: [
    {
      preprocess_steps: [
        { type: 'fill_na', strategy: 'mean' },
        { type: 'standardize' },
      ],
      feature_engineering_steps: [
        { type: 'select_relevant_features', k: 20 },
      ],
    },
  ],
  results: [
    {
      preprocess_pipeline_index: 0,
      model_name: 'XGBoost',
      split_name: 'split_0',
      validation_config: {
        method: 'train_test_split',
        n_splits: 1,
        stratified: true,
        train_size: 0.8,
        test_size: 0.2,
        shuffle: true,
        random_state: 42,
      },
      resampling_method: 'smote',
      best_params: {},
      metrics: [
        { id: 's0', metric: 'balanced_accuracy', value: 0.942, ci_lower: null, ci_upper: null },
        { id: 's1', metric: 'auc', value: 0.9601, ci_lower: null, ci_upper: null },
        { id: 's2', metric: 'precision', value: 0.93, ci_lower: null, ci_upper: null },
        { id: 's3', metric: 'recall', value: 0.89, ci_lower: null, ci_upper: null },
        { id: 's4', metric: 'f1', value: 0.91, ci_lower: null, ci_upper: null },
      ],
    },
  ],
}
