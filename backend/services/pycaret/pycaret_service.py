from pathlib import Path

import pandas as pd
from .pycaret_metrics import (
    build_confusion_matrix_payload,
    build_correlation_matrix_payload,
)


class PyCaretTrainingService:
    def train_fall_model(
        self,
        data_path: str,
        target_col: str = "是否跌倒",
        output_dir: str = "artifacts/pycaret",
    ) -> dict:
        try:
            from pycaret.classification import (
                compare_models,
                create_model,
                finalize_model,
                models,
                predict_model,
                pull,
                save_model,
                setup,
            )
            from sklearn.metrics import confusion_matrix, roc_auc_score
        except RuntimeError as exc:
            raise RuntimeError(
                "PyCaret requires Python 3.9/3.10/3.11. Please run this backend with Python 3.11."
            ) from exc

        data_file = Path(data_path)
        if not data_file.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")

        output_base = Path(output_dir)
        output_base.mkdir(parents=True, exist_ok=True)

        try:
            df = pd.read_csv(data_file, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(data_file, encoding="cp950")

        if target_col not in df.columns:
            raise ValueError(f"Target column not found: {target_col}")

        if "ID" in df.columns:
            df = df.drop(columns=["ID"])

        setup(
            data=df,
            target=target_col,
            session_id=42,
            fold=5,
            train_size=0.7,
            normalize=True,
            fix_imbalance=True,
            verbose=False,
        )

        best_model = compare_models(exclude=["lightgbm"])
        compare_results = pull()
        compare_results_path = output_base / "pycaret_compare_results.csv"
        compare_results.to_csv(compare_results_path, index=False)

        model_table = models()
        model_table = model_table[~model_table.index.isin({"lightgbm"})]

        metrics_rows = []
        for model_id, row in model_table.iterrows():
            model_name = row["Model"] if "Model" in row else row.get("Name", model_id)

            model = create_model(model_id, fold=5)
            preds = predict_model(model)

            y_true = preds[target_col]
            y_pred = preds["prediction_label"]

            labels = list(pd.unique(y_true))
            if not labels:
                continue

            pos_label = 1 if 1 in labels else ("Y" if "Y" in labels else labels[-1])
            neg_label = next(
                (label for label in labels if label != pos_label), pos_label
            )

            cm = confusion_matrix(y_true, y_pred, labels=[neg_label, pos_label])
            if cm.size == 4:
                tn, fp, fn, tp = cm.ravel()
            else:
                tn = fp = fn = tp = 0

            total = tp + tn + fp + fn
            accuracy = (tp + tn) / total if total else 0
            sensitivity = tp / (tp + fn) if (tp + fn) else 0
            specificity = tn / (tn + fp) if (tn + fp) else 0

            y_score = preds["Score"] if "Score" in preds.columns else None
            auc = (
                roc_auc_score((y_true == pos_label).astype(int), y_score)
                if y_score is not None
                else float("nan")
            )

            metrics_rows.append(
                {
                    "Classifier": model_name,
                    "Accuracy": round(accuracy, 4),
                    "Sensitivity": round(sensitivity, 4),
                    "Specificity": round(specificity, 4),
                    "AUC": round(auc, 4) if pd.notna(auc) else auc,
                }
            )

        teacher_format_path = output_base / "pycaret_teacher_format.csv"
        pd.DataFrame(metrics_rows).to_csv(teacher_format_path, index=False)

        final_model = finalize_model(best_model)
        model_path_no_suffix = output_base / "fall_model"
        save_model(final_model, str(model_path_no_suffix))

        best_model_predictions = predict_model(best_model)
        confusion_matrix_payload = build_confusion_matrix_payload(
            predictions=best_model_predictions,
            target_col=target_col,
        )
        correlation_matrix_payload = build_correlation_matrix_payload(
            source_df=df,
            target_col=target_col,
        )

        return {
            "target_col": target_col,
            "best_model": str(best_model),
            "compare_results_path": str(compare_results_path),
            "teacher_format_path": str(teacher_format_path),
            "model_path": f"{model_path_no_suffix}.pkl",
            "row_count": int(len(df)),
            "feature_count": int(len(df.columns) - 1),
            "confusion_matrix": confusion_matrix_payload,
            "correlation_matrix": correlation_matrix_payload,
        }
