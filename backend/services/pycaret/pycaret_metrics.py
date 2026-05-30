from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.metrics import confusion_matrix


def _resolve_prediction_column(predictions: pd.DataFrame) -> str:
    if "prediction_label" in predictions.columns:
        return "prediction_label"
    if "Label" in predictions.columns:
        return "Label"
    raise ValueError("Prediction column not found in prediction results")


def build_confusion_matrix_payload(
    predictions: pd.DataFrame,
    target_col: str,
) -> dict[str, Any]:
    if target_col not in predictions.columns:
        return {
            "labels": [],
            "matrix": [],
            "message": f"Target column not found in predictions: {target_col}",
        }

    pred_col = _resolve_prediction_column(predictions)

    y_true = predictions[target_col].astype(str)
    y_pred = predictions[pred_col].astype(str)

    labels = sorted(set(y_true.tolist()) | set(y_pred.tolist()))
    if not labels:
        return {
            "labels": [],
            "matrix": [],
            "message": "No labels found to build confusion matrix",
        }

    cm = confusion_matrix(y_true, y_pred, labels=labels)

    return {
        "labels": labels,
        "matrix": cm.tolist(),
        "prediction_column": pred_col,
    }


def build_correlation_matrix_payload(
    source_df: pd.DataFrame,
    target_col: str,
    method: str = "pearson",
) -> dict[str, Any]:
    numeric_df = source_df.select_dtypes(include=["number"]).copy()

    if target_col in numeric_df.columns:
        numeric_df = numeric_df.drop(columns=[target_col])

    if numeric_df.shape[1] < 2:
        return {
            "columns": [],
            "matrix": [],
            "method": method,
            "message": "Numeric columns are fewer than 2, correlation matrix is unavailable",
        }

    corr = numeric_df.corr(method=method).fillna(0.0)

    return {
        "columns": corr.columns.tolist(),
        "matrix": corr.round(6).values.tolist(),
        "method": method,
    }
