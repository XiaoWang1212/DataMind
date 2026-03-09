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
  };
};
