from __future__ import annotations

from itertools import product
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import LabelBinarizer

SUPPORTED_METRICS = {
    "accuracy",
    "precision",
    "recall",
    "f1",
    "auc",
    "specificity",
}


def generate_score_variants(score_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not score_groups:
        return []

    groups = []
    for group in score_groups:
        name = group.get("name")
        options = group.get("options", [])
        if not name or not isinstance(options, list) or len(options) == 0:
            continue
        groups.append({"name": name, "options": options})

    if not groups:
        return []

    variants: List[Dict[str, Any]] = []
    for index, combination in enumerate(
        product(*[group["options"] for group in groups])
    ):
        variant = {group["name"]: option for group, option in zip(groups, combination)}
        variant["id"] = f"score_variant_{index}"
        variants.append(variant)

    return variants


def _safe_float_array(value: Any) -> Optional[np.ndarray]:
    if value is None:
        return None

    try:
        arr = np.asarray(value, dtype=float)
    except Exception:
        return None

    if arr.ndim == 1:
        return arr
    if arr.ndim == 2 and arr.shape[1] == 1:
        return arr.ravel()
    return None


def _specificity(
    y_true: pd.Series, y_pred: pd.Series, labels: Optional[List[Any]] = None
) -> float:
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    if matrix.size != 4:
        return 0.0
    tn, fp, fn, tp = matrix.ravel()
    return tn / (tn + fp) if (tn + fp) else 0.0


def _get_score_vector(
    y_score: Any, pos_label: Optional[Any] = None
) -> Optional[np.ndarray]:
    if y_score is None:
        return None

    if isinstance(y_score, dict):
        proba = y_score.get("proba")
        classes = y_score.get("classes")
        arr = np.asarray(proba, dtype=float)
        if arr.ndim == 1:
            return arr
        if arr.ndim == 2:
            idx = 1
            if classes is not None:
                if pos_label is not None and pos_label in classes:
                    idx = classes.index(pos_label)
                else:
                    sorted_labels = sorted(classes, key=str)
                    if len(sorted_labels) == 2 and sorted_labels[1] in classes:
                        idx = classes.index(sorted_labels[1])
            idx = min(idx, arr.shape[1] - 1)
            return arr[:, idx]

    return _safe_float_array(y_score)


def _infer_positive_label(
    y_true: pd.Series, labels: Optional[List[Any]] = None
) -> Optional[Any]:
    if labels is not None and len(labels) == 2:
        return labels[-1]

    unique_labels = pd.unique(y_true.dropna())
    if len(unique_labels) == 2:
        return sorted(unique_labels, key=str)[1]

    return None


def _threshold_predict(
    y_score: Any,
    threshold: Any,
    y_true: pd.Series,
    pos_label: Optional[Any] = None,
    labels: Optional[List[Any]] = None,
) -> pd.Series:
    score_vec = _get_score_vector(y_score, pos_label)
    if score_vec is None:
        return pd.Series([], dtype=int)

    threshold_value = float(threshold)
    if y_true.dtype.kind in "biufc" and pos_label is None and labels is None:
        return pd.Series((score_vec >= threshold_value).astype(int), index=y_true.index)

    positive_label = pos_label or _infer_positive_label(y_true, labels)
    unique_labels = pd.unique(y_true.dropna())
    negative_labels = [label for label in unique_labels if label != positive_label]
    negative_label = negative_labels[0] if negative_labels else 0

    return pd.Series(
        [
            positive_label if score >= threshold_value else negative_label
            for score in score_vec
        ],
        index=y_true.index,
    )


def _to_binary_array(y_true: pd.Series, pos_label: Optional[Any] = None) -> np.ndarray:
    if y_true.dtype.kind in "biufc":
        return y_true.astype(int).to_numpy(dtype=int)

    unique_labels = pd.unique(y_true.dropna())
    if len(unique_labels) != 2:
        raise ValueError("AUC requires exactly two class labels")

    if pos_label is None:
        pos_label = sorted(unique_labels, key=str)[1]

    label_map = {label: 1 if label == pos_label else 0 for label in unique_labels}
    if pos_label not in label_map:
        raise ValueError(f"pos_label={pos_label} is not a valid label")

    return y_true.map(label_map).astype(int).to_numpy(dtype=int)


def evaluate_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
    y_score: Any,
    score_variants: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for variant in score_variants:
        metric = str(variant.get("metric", "")).lower()
        if metric not in SUPPORTED_METRICS:
            results.append(
                {
                    "id": variant.get("id"),
                    "metric": metric,
                    "value": None,
                    "error": "Unsupported metric",
                }
            )
            continue

        threshold = variant.get("threshold")
        pos_label = variant.get("pos_label")
        labels = variant.get("labels")

        y_pred_variant = y_pred
        if threshold is not None and y_score is not None:
            y_pred_variant = _threshold_predict(
                y_score, threshold, y_true, pos_label=pos_label, labels=labels
            )

        try:
            if metric == "accuracy":
                value = accuracy_score(y_true, y_pred_variant)
            elif metric in {"precision", "recall", "f1"}:
                kwargs: Dict[str, Any] = {"zero_division": 0}
                effective_pos_label = pos_label
                if effective_pos_label is None:
                    effective_pos_label = _infer_positive_label(y_true, labels)
                if effective_pos_label is not None:
                    kwargs["pos_label"] = effective_pos_label
                if labels is not None:
                    kwargs["labels"] = labels

                if metric == "precision":
                    value = precision_score(y_true, y_pred_variant, **kwargs)
                elif metric == "recall":
                    value = recall_score(y_true, y_pred_variant, **kwargs)
                else:
                    value = f1_score(y_true, y_pred_variant, **kwargs)
            elif metric == "auc":
                if y_score is None:
                    value = None
                else:
                    score_vec = _get_score_vector(y_score, pos_label)
                    if score_vec is None:
                        value = None
                    else:
                        binary = _to_binary_array(y_true, pos_label)
                        value = roc_auc_score(binary, score_vec)
            elif metric == "specificity":
                value = _specificity(y_true, y_pred_variant, labels=labels)
            else:
                value = None
        except Exception as exc:
            results.append(
                {
                    "id": variant.get("id"),
                    "metric": metric,
                    "value": None,
                    "error": str(exc),
                }
            )
            continue

        results.append(
            {
                "id": variant.get("id"),
                "metric": metric,
                "value": float(value) if value is not None else None,
                "threshold": threshold,
                "pos_label": pos_label,
            }
        )

    return results
