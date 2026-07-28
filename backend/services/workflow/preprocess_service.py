from __future__ import annotations

from itertools import product
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer, KNNImputer
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler

PREPROCESS_STEP_TYPES = {
    "drop_columns",
    "fill_na",
    "normalize",
    "standardize",
    "one_hot",
    "label_encode",
    "knn_impute",
    "iterative_impute",
    "remove_outliers_iqr",
    "remove_outliers_zscore",
}


# ---------------------------------------------------------------------------
# Individual step helpers
# ---------------------------------------------------------------------------

def _fill_na(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns")
    strategy = step.get("strategy", "constant")
    value = step.get("value", 0)

    target_cols = [c for c in (columns or df.columns) if c in df.columns]
    result = df.copy()
    for col in target_cols:
        if strategy == "mean" and pd.api.types.is_numeric_dtype(result[col]):
            result[col] = result[col].fillna(result[col].mean())
        elif strategy == "median" and pd.api.types.is_numeric_dtype(result[col]):
            result[col] = result[col].fillna(result[col].median())
        elif strategy == "mode":
            mode = result[col].mode()
            result[col] = result[col].fillna(mode.iloc[0] if not mode.empty else value)
        else:
            result[col] = result[col].fillna(value)
    return result


def _fill_na_fit(train: pd.DataFrame, step: Dict[str, Any]) -> Dict[str, Any]:
    """Compute fill values from train set only."""
    columns = step.get("columns")
    strategy = step.get("strategy", "constant")
    value = step.get("value", 0)

    target_cols = [c for c in (columns or train.columns) if c in train.columns]
    fill_values: Dict[str, Any] = {}
    for col in target_cols:
        if strategy == "mean" and pd.api.types.is_numeric_dtype(train[col]):
            fill_values[col] = train[col].mean()
        elif strategy == "median" and pd.api.types.is_numeric_dtype(train[col]):
            fill_values[col] = train[col].median()
        elif strategy == "mode":
            mode = train[col].mode()
            fill_values[col] = mode.iloc[0] if not mode.empty else value
        else:
            fill_values[col] = value
    return {"fill_values": fill_values}


def _fill_na_transform(df: pd.DataFrame, state: Dict[str, Any]) -> pd.DataFrame:
    result = df.copy()
    for col, val in state["fill_values"].items():
        if col in result.columns:
            result[col] = result[col].fillna(val)
    return result


def _drop_columns(df: pd.DataFrame, step: Dict[str, Any]) -> pd.DataFrame:
    columns = step.get("columns", [])
    return df.drop(columns=[c for c in columns if c in df.columns], errors="ignore")


def _normalize_fit(train: pd.DataFrame, step: Dict[str, Any]) -> Dict[str, Any]:
    columns = step.get("columns")
    numeric = train.select_dtypes(include=["number"]).columns.tolist()
    target_cols = [c for c in (columns or numeric) if c in train.columns]
    scaler = MinMaxScaler()
    if target_cols:
        scaler.fit(train[target_cols])
    return {"scaler": scaler, "columns": target_cols}


def _normalize_transform(df: pd.DataFrame, state: Dict[str, Any]) -> pd.DataFrame:
    cols = [c for c in state["columns"] if c in df.columns]
    if not cols:
        return df
    result = df.copy()
    result[cols] = state["scaler"].transform(result[cols])
    return result


def _standardize_fit(train: pd.DataFrame, step: Dict[str, Any]) -> Dict[str, Any]:
    columns = step.get("columns")
    numeric = train.select_dtypes(include=["number"]).columns.tolist()
    target_cols = [c for c in (columns or numeric) if c in train.columns]
    scaler = StandardScaler()
    if target_cols:
        scaler.fit(train[target_cols])
    return {"scaler": scaler, "columns": target_cols}


def _standardize_transform(df: pd.DataFrame, state: Dict[str, Any]) -> pd.DataFrame:
    cols = [c for c in state["columns"] if c in df.columns]
    if not cols:
        return df
    result = df.copy()
    result[cols] = state["scaler"].transform(result[cols])
    return result


def _one_hot_fit(train: pd.DataFrame, step: Dict[str, Any]) -> Dict[str, Any]:
    columns = step.get("columns")
    if not columns:
        columns = train.select_dtypes(include=["object", "category"]).columns.tolist()
    columns = [c for c in columns if c in train.columns]
    dummies = pd.get_dummies(train[columns], drop_first=False) if columns else pd.DataFrame()
    return {"columns": columns, "dummy_columns": dummies.columns.tolist()}


def _one_hot_transform(df: pd.DataFrame, state: Dict[str, Any]) -> pd.DataFrame:
    cols = [c for c in state["columns"] if c in df.columns]
    if not cols:
        return df
    result = df.copy()
    dummies = pd.get_dummies(result[cols], drop_first=False)
    # Align to train columns: add missing with 0, drop extra
    for col in state["dummy_columns"]:
        if col not in dummies.columns:
            dummies[col] = 0
    dummies = dummies[state["dummy_columns"]]
    result = result.drop(columns=cols)
    return pd.concat([result, dummies], axis=1)


def _label_encode_fit(train: pd.DataFrame, step: Dict[str, Any]) -> Dict[str, Any]:
    columns = step.get("columns")
    if not columns:
        columns = train.select_dtypes(include=["object", "category"]).columns.tolist()
    encoders: Dict[str, LabelEncoder] = {}
    for col in columns:
        if col not in train.columns:
            continue
        enc = LabelEncoder()
        enc.fit(train[col].astype(str))
        encoders[col] = enc
    return {"encoders": encoders}


def _label_encode_transform(df: pd.DataFrame, state: Dict[str, Any]) -> pd.DataFrame:
    result = df.copy()
    for col, enc in state["encoders"].items():
        if col not in result.columns:
            continue
        known = set(enc.classes_)
        result[col] = result[col].astype(str).map(
            lambda v, k=known, e=enc: e.transform([v])[0] if v in k else -1
        )
    return result


def _knn_impute_fit(train: pd.DataFrame, step: Dict[str, Any]) -> Dict[str, Any]:
    n_neighbors = int(step.get("n_neighbors", 5))
    numeric = train.select_dtypes(include=["number"]).columns.tolist()
    imputer = KNNImputer(n_neighbors=n_neighbors)
    if numeric:
        imputer.fit(train[numeric])
    return {"imputer": imputer, "columns": numeric}


def _knn_impute_transform(df: pd.DataFrame, state: Dict[str, Any]) -> pd.DataFrame:
    cols = [c for c in state["columns"] if c in df.columns]
    if not cols:
        return df
    result = df.copy()
    result[cols] = state["imputer"].transform(result[cols])
    return result


def _iterative_impute_fit(train: pd.DataFrame, step: Dict[str, Any]) -> Dict[str, Any]:
    max_iter = int(step.get("max_iter", 10))
    random_state = int(step.get("random_state", 42))
    numeric = train.select_dtypes(include=["number"]).columns.tolist()
    imputer = IterativeImputer(max_iter=max_iter, random_state=random_state)
    if numeric:
        imputer.fit(train[numeric])
    return {"imputer": imputer, "columns": numeric}


def _iterative_impute_transform(df: pd.DataFrame, state: Dict[str, Any]) -> pd.DataFrame:
    cols = [c for c in state["columns"] if c in df.columns]
    if not cols:
        return df
    result = df.copy()
    result[cols] = state["imputer"].transform(result[cols])
    return result


def _remove_outliers_iqr_fit(train: pd.DataFrame, step: Dict[str, Any]) -> Dict[str, Any]:
    """Compute IQR bounds from train set; used to clip (not drop) on transform."""
    columns = step.get("columns")
    multiplier = float(step.get("multiplier", 1.5))
    numeric = train.select_dtypes(include=["number"]).columns.tolist()
    target_cols = [c for c in (columns or numeric) if c in train.columns]

    bounds: Dict[str, Tuple[float, float]] = {}
    for col in target_cols:
        q1 = float(train[col].quantile(0.25))
        q3 = float(train[col].quantile(0.75))
        iqr = q3 - q1
        bounds[col] = (q1 - multiplier * iqr, q3 + multiplier * iqr)
    return {"bounds": bounds}


def _remove_outliers_iqr_transform(df: pd.DataFrame, state: Dict[str, Any]) -> pd.DataFrame:
    result = df.copy()
    for col, (lo, hi) in state["bounds"].items():
        if col in result.columns:
            result[col] = result[col].clip(lower=lo, upper=hi)
    return result


def _remove_outliers_zscore_fit(train: pd.DataFrame, step: Dict[str, Any]) -> Dict[str, Any]:
    columns = step.get("columns")
    threshold = float(step.get("threshold", 3.0))
    numeric = train.select_dtypes(include=["number"]).columns.tolist()
    target_cols = [c for c in (columns or numeric) if c in train.columns]

    stats: Dict[str, Tuple[float, float]] = {}
    for col in target_cols:
        stats[col] = (float(train[col].mean()), float(train[col].std()))
    return {"stats": stats, "threshold": threshold}


def _remove_outliers_zscore_transform(
    df: pd.DataFrame, state: Dict[str, Any]
) -> pd.DataFrame:
    result = df.copy()
    thr = state["threshold"]
    for col, (mean, std) in state["stats"].items():
        if col not in result.columns or std == 0:
            continue
        lo = mean - thr * std
        hi = mean + thr * std
        result[col] = result[col].clip(lower=lo, upper=hi)
    return result


# ---------------------------------------------------------------------------
# Stateless apply (full dataset, no leakage for non-scaling steps)
# ---------------------------------------------------------------------------

def apply_preprocess_pipeline(
    df: pd.DataFrame,
    pipeline_steps: List[Dict[str, Any]],
) -> pd.DataFrame:
    """Apply preprocessing to a single DataFrame (fit+transform on same data).
    Use only when no train/test split is needed (e.g. exploratory analysis).
    For model training, use apply_preprocess_pipeline_for_split instead.
    """
    result = df.copy()
    for step in pipeline_steps:
        step_type = step.get("type")
        if step_type not in PREPROCESS_STEP_TYPES:
            continue
        if step_type == "drop_columns":
            result = _drop_columns(result, step)
        elif step_type == "fill_na":
            state = _fill_na_fit(result, step)
            result = _fill_na_transform(result, state)
        elif step_type == "normalize":
            state = _normalize_fit(result, step)
            result = _normalize_transform(result, state)
        elif step_type == "standardize":
            state = _standardize_fit(result, step)
            result = _standardize_transform(result, state)
        elif step_type == "one_hot":
            state = _one_hot_fit(result, step)
            result = _one_hot_transform(result, state)
        elif step_type == "label_encode":
            state = _label_encode_fit(result, step)
            result = _label_encode_transform(result, state)
        elif step_type == "knn_impute":
            state = _knn_impute_fit(result, step)
            result = _knn_impute_transform(result, state)
        elif step_type == "iterative_impute":
            state = _iterative_impute_fit(result, step)
            result = _iterative_impute_transform(result, state)
        elif step_type == "remove_outliers_iqr":
            state = _remove_outliers_iqr_fit(result, step)
            result = _remove_outliers_iqr_transform(result, state)
        elif step_type == "remove_outliers_zscore":
            state = _remove_outliers_zscore_fit(result, step)
            result = _remove_outliers_zscore_transform(result, state)
    return result


# ---------------------------------------------------------------------------
# Split-aware apply (fit on train only, transform both) — no data leakage
# ---------------------------------------------------------------------------

def apply_preprocess_pipeline_for_split(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pipeline_steps: List[Dict[str, Any]],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Apply preprocessing fit on train only, transform both train and test.
    This prevents data leakage from normalization, encoding, imputation, etc.
    """
    train_result = train_df.copy()
    test_result = test_df.copy()

    for step in pipeline_steps:
        step_type = step.get("type")
        if step_type not in PREPROCESS_STEP_TYPES:
            continue

        if step_type == "drop_columns":
            train_result = _drop_columns(train_result, step)
            test_result = _drop_columns(test_result, step)

        elif step_type == "fill_na":
            state = _fill_na_fit(train_result, step)
            train_result = _fill_na_transform(train_result, state)
            test_result = _fill_na_transform(test_result, state)

        elif step_type == "normalize":
            state = _normalize_fit(train_result, step)
            train_result = _normalize_transform(train_result, state)
            test_result = _normalize_transform(test_result, state)

        elif step_type == "standardize":
            state = _standardize_fit(train_result, step)
            train_result = _standardize_transform(train_result, state)
            test_result = _standardize_transform(test_result, state)

        elif step_type == "one_hot":
            state = _one_hot_fit(train_result, step)
            train_result = _one_hot_transform(train_result, state)
            test_result = _one_hot_transform(test_result, state)

        elif step_type == "label_encode":
            state = _label_encode_fit(train_result, step)
            train_result = _label_encode_transform(train_result, state)
            test_result = _label_encode_transform(test_result, state)

        elif step_type == "knn_impute":
            state = _knn_impute_fit(train_result, step)
            train_result = _knn_impute_transform(train_result, state)
            test_result = _knn_impute_transform(test_result, state)

        elif step_type == "iterative_impute":
            state = _iterative_impute_fit(train_result, step)
            train_result = _iterative_impute_transform(train_result, state)
            test_result = _iterative_impute_transform(test_result, state)

        elif step_type == "remove_outliers_iqr":
            state = _remove_outliers_iqr_fit(train_result, step)
            train_result = _remove_outliers_iqr_transform(train_result, state)
            test_result = _remove_outliers_iqr_transform(test_result, state)

        elif step_type == "remove_outliers_zscore":
            state = _remove_outliers_zscore_fit(train_result, step)
            train_result = _remove_outliers_zscore_transform(train_result, state)
            test_result = _remove_outliers_zscore_transform(test_result, state)

    return train_result, test_result


# ---------------------------------------------------------------------------
# Variant generator
# ---------------------------------------------------------------------------

def generate_preprocess_variants(
    step_groups: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not step_groups:
        return []

    groups = []
    for group in step_groups:
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
        steps = [step for step in combination if isinstance(step, dict)]
        label_parts = [
            f"{group['name']}={step.get('label', step.get('type', 'option'))}"
            for group, step in zip(groups, combination)
        ]
        variants.append(
            {
                "id": f"preprocess_variant_{index}",
                "label": " + ".join(label_parts),
                "steps": steps,
            }
        )

    return variants
