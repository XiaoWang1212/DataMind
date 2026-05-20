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


def evaluate_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
    y_score: Optional[np.ndarray],
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
            y_pred_variant = pd.Series(
                (y_score >= float(threshold)).astype(int), index=y_true.index
            )

        try:
            if metric == "accuracy":
                value = accuracy_score(y_true, y_pred_variant)
            elif metric == "precision":
                value = precision_score(
                    y_true,
                    y_pred_variant,
                    pos_label=pos_label,
                    zero_division=0,
                    labels=labels,
                )
            elif metric == "recall":
                value = recall_score(
                    y_true,
                    y_pred_variant,
                    pos_label=pos_label,
                    zero_division=0,
                    labels=labels,
                )
            elif metric == "f1":
                value = f1_score(
                    y_true,
                    y_pred_variant,
                    pos_label=pos_label,
                    zero_division=0,
                    labels=labels,
                )
            elif metric == "auc":
                if y_score is None:
                    value = None
                else:
                    binary = y_true.astype(int)
                    value = roc_auc_score(binary, y_score)
            elif metric == "specificity":
                value = _specificity(y_true, y_pred_variant, labels=labels)
            else:
                value = None
        except Exception as exc:
            value = None
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
