export type PyCaretTrainResponse = {
  success?: boolean;
  error?: string;
  result?: {
    target_col: string;
    best_model: string;
    compare_results_path: string;
    teacher_format_path: string;
    model_path: string;
    row_count: number;
    feature_count: number;
    confusion_matrix?: {
      labels: string[];
      matrix: number[][];
      prediction_column?: string;
      message?: string;
    };
    correlation_matrix?: {
      columns: string[];
      matrix: number[][];
      method: string;
      message?: string;
    };
  };
};
