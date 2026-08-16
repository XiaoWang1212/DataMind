from __future__ import annotations

from itertools import product
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import LabelBinarizer

SUPPORTED_METRICS = {
    "accuracy",
    "balanced_accuracy",
    "precision",
    "recall",
    "f1",
    "auc",
    "auprc",
    "specificity",
    "mcc",
    "kappa",
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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
    return y_true.map(label_map).astype(int).to_numpy(dtype=int)


# ---------------------------------------------------------------------------
# Bootstrap confidence interval
# ---------------------------------------------------------------------------

def _bootstrap_ci(
    y_true: np.ndarray,
    y_score: np.ndarray,
    metric_fn: Any,
    n_bootstrap: int = 1000,
    ci: float = 0.95,
    random_state: int = 42,
) -> Tuple[float, float]:
    rng = np.random.RandomState(random_state)
    scores = []
    n = len(y_true)
    for _ in range(n_bootstrap):
        idx = rng.randint(0, n, n)
        try:
            scores.append(metric_fn(y_true[idx], y_score[idx]))
        except Exception:
            pass
    if not scores:
        return (float("nan"), float("nan"))
    alpha = (1.0 - ci) / 2.0
    lo = float(np.percentile(scores, alpha * 100))
    hi = float(np.percentile(scores, (1.0 - alpha) * 100))
    return lo, hi


# ---------------------------------------------------------------------------
# Public evaluation function
# ---------------------------------------------------------------------------

def build_roc_pr_curve(y_true: pd.Series, y_score: Any) -> Optional[Dict[str, Any]]:
    """算 ROC / PR 曲線座標點，只支援二元分類（y_score 為 None 或多分類時回傳 None）"""
    if y_score is None:
        return None
    score_vec = _get_score_vector(y_score)
    if score_vec is None:
        return None
    unique_labels = pd.unique(y_true.dropna())
    if len(unique_labels) != 2:
        return None

    try:
        pos_label = _infer_positive_label(y_true)
        binary = _to_binary_array(y_true, pos_label)
        # _to_binary_array 對數值 dtype 是原值透傳（不處理 pos_label），這裡補正成真正的 0/1
        if not np.array_equal(np.unique(binary), np.array([0, 1])):
            binary = (y_true == pos_label).to_numpy(dtype=int)

        fpr, tpr, _ = roc_curve(binary, score_vec)
        precision, recall, _ = precision_recall_curve(binary, score_vec, drop_intermediate=True)
    except Exception:
        return None

    return {
        "pos_label": str(pos_label),
        "roc": {"fpr": [round(v, 6) for v in fpr.tolist()], "tpr": [round(v, 6) for v in tpr.tolist()]},
        "pr": {"precision": [round(v, 6) for v in precision.tolist()], "recall": [round(v, 6) for v in recall.tolist()]},
    }


def evaluate_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
    y_score: Any,
    score_variants: List[Dict[str, Any]],
    compute_ci: bool = False,
    ci_n_bootstrap: int = 1000,
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
                    "error": f"Unsupported metric. Available: {sorted(SUPPORTED_METRICS)}",
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
            value, ci_lo, ci_hi = _compute_metric(
                metric=metric,
                y_true=y_true,
                y_pred=y_pred_variant,
                y_score=y_score,
                pos_label=pos_label,
                labels=labels,
                compute_ci=compute_ci,
                ci_n_bootstrap=ci_n_bootstrap,
            )
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

        entry: Dict[str, Any] = {
            "id": variant.get("id"),
            "metric": metric,
            "value": float(value) if value is not None else None,
            "threshold": threshold,
            "pos_label": pos_label,
        }
        if compute_ci and ci_lo is not None:
            entry["ci_lower"] = ci_lo
            entry["ci_upper"] = ci_hi
            entry["ci_level"] = 0.95

        results.append(entry)

    return results


def _compute_metric(
    metric: str,
    y_true: pd.Series,
    y_pred: pd.Series,
    y_score: Any,
    pos_label: Optional[Any],
    labels: Optional[List[Any]],
    compute_ci: bool,
    ci_n_bootstrap: int,
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    ci_lo: Optional[float] = None
    ci_hi: Optional[float] = None
    value: Optional[float] = None

    if metric == "accuracy":
        value = accuracy_score(y_true, y_pred)
        if compute_ci:
            ci_lo, ci_hi = _bootstrap_ci(
                y_true.to_numpy(), y_pred.to_numpy(),
                accuracy_score, ci_n_bootstrap,
            )

    elif metric == "balanced_accuracy":
        value = balanced_accuracy_score(y_true, y_pred)
        if compute_ci:
            ci_lo, ci_hi = _bootstrap_ci(
                y_true.to_numpy(), y_pred.to_numpy(),
                balanced_accuracy_score, ci_n_bootstrap,
            )

    elif metric == "mcc":
        value = matthews_corrcoef(y_true, y_pred)
        if compute_ci:
            ci_lo, ci_hi = _bootstrap_ci(
                y_true.to_numpy(), y_pred.to_numpy(),
                matthews_corrcoef, ci_n_bootstrap,
            )

    elif metric == "kappa":
        value = cohen_kappa_score(y_true, y_pred)
        if compute_ci:
            ci_lo, ci_hi = _bootstrap_ci(
                y_true.to_numpy(), y_pred.to_numpy(),
                cohen_kappa_score, ci_n_bootstrap,
            )

    elif metric in {"precision", "recall", "f1"}:
        kwargs: Dict[str, Any] = {"zero_division": 0}
        effective_pos = pos_label or _infer_positive_label(y_true, labels)
        if effective_pos is not None:
            kwargs["pos_label"] = effective_pos
        if labels is not None:
            kwargs["labels"] = labels

        fn_map = {
            "precision": precision_score,
            "recall": recall_score,
            "f1": f1_score,
        }
        fn = fn_map[metric]
        value = fn(y_true, y_pred, **kwargs)
        if compute_ci:
            ci_lo, ci_hi = _bootstrap_ci(
                y_true.to_numpy(), y_pred.to_numpy(),
                lambda yt, yp: fn(yt, yp, **kwargs),
                ci_n_bootstrap,
            )

    elif metric == "specificity":
        value = _specificity(y_true, y_pred, labels=labels)

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
                if compute_ci:
                    ci_lo, ci_hi = _bootstrap_ci(
                        binary, score_vec, roc_auc_score, ci_n_bootstrap,
                    )

    elif metric == "auprc":
        if y_score is None:
            value = None
        else:
            score_vec = _get_score_vector(y_score, pos_label)
            if score_vec is None:
                value = None
            else:
                binary = _to_binary_array(y_true, pos_label)
                value = average_precision_score(binary, score_vec)
                if compute_ci:
                    ci_lo, ci_hi = _bootstrap_ci(
                        binary, score_vec, average_precision_score, ci_n_bootstrap,
                    )

    return value, ci_lo, ci_hi
