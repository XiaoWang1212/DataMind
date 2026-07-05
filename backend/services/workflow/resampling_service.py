from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

RESAMPLING_METHODS = {
    "smote",
    "adasyn",
    "borderline_smote",
    "random_oversample",
    "random_undersample",
    "smoteenn",
    "smotetomek",
    "none",
}


def apply_resampling(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    method: str = "none",
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Apply resampling to training data only to handle class imbalance.

    Must be called AFTER train/test split so test data is never touched.

    Parameters
    ----------
    X_train : feature matrix (train only)
    y_train : target labels (train only)
    method  : resampling strategy name
    config  : optional kwargs forwarded to the resampler

    Returns
    -------
    Resampled (X_train_res, y_train_res) with original DataFrame column names preserved.
    """
    config = config or {}
    method = method.lower()

    if method not in RESAMPLING_METHODS:
        raise ValueError(
            f"Unknown resampling method '{method}'. "
            f"Available: {sorted(RESAMPLING_METHODS)}"
        )

    if method == "none":
        return X_train, y_train

    random_state = int(config.get("random_state", 42))
    sampling_strategy = config.get("sampling_strategy", "auto")

    resampler = _build_resampler(method, random_state, sampling_strategy, config)

    columns = X_train.columns.tolist()
    index_name = y_train.name

    X_res, y_res = resampler.fit_resample(X_train.values, y_train.values)

    X_res_df = pd.DataFrame(X_res, columns=columns)
    y_res_series = pd.Series(y_res, name=index_name)

    return X_res_df, y_res_series


def _build_resampler(
    method: str,
    random_state: int,
    sampling_strategy: Any,
    config: Dict[str, Any],
) -> Any:
    if method == "smote":
        from imblearn.over_sampling import SMOTE
        k_neighbors = int(config.get("k_neighbors", 5))
        return SMOTE(
            sampling_strategy=sampling_strategy,
            k_neighbors=k_neighbors,
            random_state=random_state,
        )

    if method == "adasyn":
        from imblearn.over_sampling import ADASYN
        n_neighbors = int(config.get("n_neighbors", 5))
        return ADASYN(
            sampling_strategy=sampling_strategy,
            n_neighbors=n_neighbors,
            random_state=random_state,
        )

    if method == "borderline_smote":
        from imblearn.over_sampling import BorderlineSMOTE
        k_neighbors = int(config.get("k_neighbors", 5))
        kind = str(config.get("kind", "borderline-1"))
        return BorderlineSMOTE(
            sampling_strategy=sampling_strategy,
            k_neighbors=k_neighbors,
            kind=kind,
            random_state=random_state,
        )

    if method == "random_oversample":
        from imblearn.over_sampling import RandomOverSampler
        return RandomOverSampler(
            sampling_strategy=sampling_strategy,
            random_state=random_state,
        )

    if method == "random_undersample":
        from imblearn.under_sampling import RandomUnderSampler
        return RandomUnderSampler(
            sampling_strategy=sampling_strategy,
            random_state=random_state,
        )

    if method == "smoteenn":
        from imblearn.combine import SMOTEENN
        return SMOTEENN(
            sampling_strategy=sampling_strategy,
            random_state=random_state,
        )

    if method == "smotetomek":
        from imblearn.combine import SMOTETomek
        return SMOTETomek(
            sampling_strategy=sampling_strategy,
            random_state=random_state,
        )

    raise ValueError(f"Unhandled method: {method}")


def describe_class_distribution(y: pd.Series) -> Dict[str, Any]:
    """Return class counts and imbalance ratio for diagnostics."""
    counts = y.value_counts().to_dict()
    if len(counts) < 2:
        return {"counts": counts, "imbalance_ratio": None}
    values = sorted(counts.values())
    ratio = round(values[-1] / values[0], 4) if values[0] > 0 else None
    return {"counts": counts, "imbalance_ratio": ratio}
